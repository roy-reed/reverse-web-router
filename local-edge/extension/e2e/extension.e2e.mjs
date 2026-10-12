// 真实 Chromium 加载未打包扩展的端到端测试。
// chrome.* API 全部是浏览器的真实实现。只有两处替身：
//  1) https://chatgpt.com/* 由 context.route 返回本地 fixture，不访问外网；
//  2) popup 的 chrome.tabs.query({active, currentWindow}) 被替换成按 URL 找真实 ChatGPT 标签，
//     原因是测试里 popup 以普通标签打开，它自己就是当前活动标签。
// native messaging host 没有安装，因此绑定后的转发会走真实的 lastError 分支。
import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FP = 'g-p-abc123-demo';
const CHAT_URL = `https://chatgpt.com/g/${FP}/c/thread-1`;
const HEADLESS = process.env.E2E_HEADED !== '1';

const packet = (taskId, protocol = 'rwrouter/1.1') =>
  JSON.stringify({ protocol, task_id: taskId, goal: 'demo' });

function chatPage({ fingerprint = FP, blocks = [] } = {}) {
  const codes = blocks.map((b) => `<pre><code>${b.replace(/</g, '&lt;')}</code></pre>`).join('\n');
  return `<!doctype html><html><body>
    <nav><a href="/g/${fingerprint}/project">Demo Project</a></nav>
    <main id="thread">${codes}</main></body></html>`;
}

let context, userDataDir, sw, extId;
let pageHtml = chatPage();

before(async () => {
  userDataDir = await mkdtemp(path.join(tmpdir(), 'rwr-e2e-'));
  context = await chromium.launchPersistentContext(userDataDir, {
    channel: 'chromium', // 新版 headless 才支持扩展；headless shell 不支持
    headless: HEADLESS,
    args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`],
  });
  await context.route('https://chatgpt.com/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: pageHtml }),
  );
  sw = context.serviceWorkers()[0] ?? (await context.waitForEvent('serviceworker', { timeout: 15000 }));
  extId = new URL(sw.url()).host;
});

after(async () => {
  await context?.close();
  if (userDataDir) await rm(userDataDir, { recursive: true, force: true });
});

beforeEach(async () => {
  for (const p of context.pages()) await p.close();
  await sw.evaluate(async () => {
    await chrome.storage.local.clear();
    self.__candidates = [];
    if (!self.__probe) {
      self.__probe = true;
      chrome.runtime.onMessage.addListener((m) => {
        if (m?.type === 'handoff-candidate') self.__candidates.push(m);
      });
    }
  });
});

const storage = () => sw.evaluate(() => chrome.storage.local.get(null));
const candidates = () => sw.evaluate(() => self.__candidates);

async function waitFor(fn, label, timeout = 10000) {
  const end = Date.now() + timeout;
  let last;
  while (Date.now() < end) {
    last = await fn();
    if (last) return last;
    await new Promise((r) => setTimeout(r, 100));
  }
  assert.fail(`timeout waiting for ${label}; last=${JSON.stringify(last)}`);
}

async function openChat(blocks, fingerprint = FP) {
  pageHtml = chatPage({ fingerprint, blocks });
  const page = await context.newPage();
  await page.goto(fingerprint === FP ? CHAT_URL : `https://chatgpt.com/g/${fingerprint}/c/thread-1`);
  return page;
}

async function openPopup(tabUrlPattern = 'https://chatgpt.com/*') {
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${extId}/popup.html`);
  await popup.evaluate((pattern) => {
    const realQuery = chrome.tabs.query.bind(chrome.tabs);
    chrome.tabs.query = async () => {
      if (pattern) return realQuery({ url: pattern });
      // 扩展对非 chatgpt.com 页面没有 host 权限，不能按 URL 过滤：返回除 popup 自身以外的标签
      const self = await chrome.tabs.getCurrent();
      return (await realQuery({})).filter((t) => t.id !== self.id);
    };
  }, tabUrlPattern);
  return popup;
}

test('扩展在真实 Chromium 中加载：MV3 service worker 运行，popup 显示未绑定', async () => {
  assert.match(extId, /^[a-p]{32}$/);
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${extId}/popup.html`);
  assert.equal(await popup.textContent('#binding'), '未绑定项目');
  assert.equal(await popup.textContent('#status'), '{}');
});

test('未绑定时，页面里的 rwrouter/1.1 握手包被 content script 发现并被 service worker 拒绝', async () => {
  await openChat([packet('task-1'), packet('other', 'rwrouter/1.0'), '{"protocol": broken', 'plain text']);
  const s = await waitFor(async () => (await storage()).lastStatus, 'lastStatus');
  assert.deepEqual(s, { ok: false, error: 'Rejected: handoff is outside the bound ChatGPT Project' });
  const c = await candidates();
  assert.equal(c.length, 1, '只应上报协议版本正确且可解析的包');
  assert.equal(c[0].packet.task_id, 'task-1');
  assert.equal(c[0].project.projectFingerprint, FP);
  assert.equal(c[0].project.projectName, 'Demo Project');
});

test('popup 绑定当前项目 → 后续握手包被转发到 native host（未安装时记录真实错误）', async () => {
  const chat = await openChat([]);
  const popup = await openPopup();
  await popup.click('#bind');
  await popup.waitForFunction(() => document.querySelector('#binding').textContent.startsWith('已绑定'));
  assert.equal(await popup.textContent('#binding'), '已绑定：Demo Project');
  let st = await storage();
  assert.equal(st.boundProjectFingerprint, FP);
  assert.equal(st.boundProjectName, 'Demo Project');

  await chat.evaluate((json) => {
    const pre = document.createElement('pre');
    pre.innerHTML = '<code></code>';
    pre.firstChild.textContent = json;
    document.querySelector('#thread').append(pre);
  }, packet('task-bound'));
  st = await waitFor(async () => {
    const v = await storage();
    return v.lastStatus && v.lastStatus.ok === false && v.lastStatus.error !== undefined && v;
  }, 'native status');
  assert.match(st.lastStatus.error, /native messaging host/i);
  assert.notEqual(st.lastStatus.error, 'Rejected: handoff is outside the bound ChatGPT Project');
  assert.deepEqual((await candidates()).map((c) => c.packet.task_id), ['task-bound']);
});

test('同一 task_id 在页面变化后只上报一次，新 task_id 继续上报', async () => {
  const chat = await openChat([packet('dup')]);
  await waitFor(async () => (await candidates()).length === 1, 'first candidate');
  const add = (json) =>
    chat.evaluate((j) => {
      const pre = document.createElement('pre');
      pre.innerHTML = '<code></code>';
      pre.firstChild.textContent = j;
      document.querySelector('#thread').append(pre);
    }, json);
  await add(packet('dup'));
  await add(packet('fresh'));
  await waitFor(async () => (await candidates()).length >= 2, 'second candidate');
  await new Promise((r) => setTimeout(r, 300));
  assert.deepEqual((await candidates()).map((c) => c.packet.task_id), ['dup', 'fresh']);
});

test('绑定 A 项目后，来自 B 项目页面的握手包仍被拒绝', async () => {
  await sw.evaluate(() =>
    chrome.storage.local.set({ boundProjectName: 'Demo Project', boundProjectFingerprint: 'g-p-abc123-demo' }),
  );
  await openChat([packet('task-b')], 'g-p-other-proj');
  const s = await waitFor(async () => (await storage()).lastStatus, 'lastStatus');
  assert.equal(s.error, 'Rejected: handoff is outside the bound ChatGPT Project');
});

test('popup 解除绑定后清除绑定信息', async () => {
  await sw.evaluate(() =>
    chrome.storage.local.set({ boundProjectName: 'Demo Project', boundProjectFingerprint: 'g-p-abc123-demo' }),
  );
  const popup = await openPopup();
  assert.equal(await popup.textContent('#binding'), '已绑定：Demo Project');
  await popup.click('#unbind');
  await popup.waitForFunction(() => document.querySelector('#binding').textContent === '未绑定项目');
  const st = await storage();
  assert.equal(st.boundProjectFingerprint, undefined);
  assert.deepEqual(st.lastStatus, { ok: true, message: 'Project unbound.' });
});

test('当前没有 ChatGPT 标签时，popup 绑定失败并显示错误', async () => {
  const popup = await openPopup();
  await popup.click('#bind');
  await popup.waitForFunction(() => document.querySelector('#status').textContent.includes('ChatGPT'));
  const st = await storage();
  assert.equal(st.boundProjectFingerprint, undefined);
  assert.equal(st.lastStatus.ok, false);
  assert.match(st.lastStatus.error, /当前标签不是 ChatGPT/);
});

test('活动标签不是 chatgpt.com 时，popup 拒绝绑定，即使该页面结构相同', async () => {
  await context.route('https://example.com/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: chatPage() }),
  );
  const other = await context.newPage();
  await other.goto(`https://example.com/g/${FP}/c/thread-1`);
  const popup = await openPopup(null);
  await popup.click('#bind');
  await popup.waitForFunction(() => document.querySelector('#status').textContent.includes('"ok": false'));
  const st = await storage();
  assert.equal(st.boundProjectFingerprint, undefined);
  assert.equal(st.lastStatus.error, 'Error: 当前标签不是 ChatGPT');
});
