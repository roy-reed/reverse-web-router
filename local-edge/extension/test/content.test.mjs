import { test } from "node:test";
import assert from "node:assert/strict";
import { createChrome, createDocument, dispatch, el, loadScript } from "./harness.mjs";

const PROJECT_LINK = 'a[href*="/g/g-p-"][href$="/project"]';
const location = { pathname: "/g/g-p-abc123/c/xyz", href: "https://chatgpt.com/g/g-p-abc123/c/xyz" };

function packet(extra = {}) {
  return JSON.stringify({ protocol: "rwrouter/1.1", task_id: "t-1", ...extra });
}

function setup(codeBlocks, { pathname } = {}) {
  const dom = createDocument({
    [PROJECT_LINK]: el({ textContent: "  My Project  " }),
    "pre code": codeBlocks.map((t) => el({ textContent: t })),
  });
  const c = createChrome();
  const loc = pathname ? { pathname, href: `https://chatgpt.com${pathname}` } : location;
  loadScript("content.js", { document: dom.document, location: loc, MutationObserver: dom.MutationObserver, chrome: c.chrome });
  return { ...c, dom };
}

test("加载时检测 rwrouter/1.1 交接包并附带项目信息", () => {
  const { calls } = setup([packet()]);
  assert.equal(calls.sendMessage.length, 1);
  const msg = calls.sendMessage[0];
  assert.equal(msg.type, "handoff-candidate");
  assert.deepEqual(msg.packet, { protocol: "rwrouter/1.1", task_id: "t-1" });
  assert.deepEqual(msg.project, { projectName: "My Project", projectFingerprint: "g-p-abc123", url: location.href });
});

test("忽略其他协议、非法 JSON、非对象文本和缺少 task_id 的包", () => {
  const { calls } = setup([
    JSON.stringify({ protocol: "rwrouter/1.0", task_id: "old" }),
    '{"protocol": broken',
    'console.log("protocol")',
    JSON.stringify({ protocol: "rwrouter/1.1" }),
  ]);
  assert.equal(calls.sendMessage.length, 0);
});

test("同一 task_id 只上报一次，DOM 变化后新任务仍会上报", () => {
  const { calls, dom } = setup([packet()]);
  assert.equal(calls.sendMessage.length, 1);
  dom.observers[0].trigger();
  assert.equal(calls.sendMessage.length, 1, "重复的 task_id 不应再次发送");
  dom.selectors["pre code"].push(el({ textContent: packet({ task_id: "t-2" }) }));
  dom.observers[0].trigger();
  assert.equal(calls.sendMessage.length, 2);
  assert.equal(calls.sendMessage[1].packet.task_id, "t-2");
});

test("MutationObserver 监听整个文档子树", () => {
  const { dom } = setup([]);
  assert.equal(dom.observers.length, 1);
  assert.equal(dom.observers[0].target, dom.document.documentElement);
  assert.deepEqual({ ...dom.observers[0].options }, { childList: true, subtree: true });
});

test("响应 inspect-project 消息，其他消息不响应", () => {
  const { listeners } = setup([]);
  const r1 = dispatch(listeners, { type: "inspect-project" });
  assert.deepEqual(r1.responses, [{ projectName: "My Project", projectFingerprint: "g-p-abc123", url: location.href }]);
  const r2 = dispatch(listeners, { type: "something-else" });
  assert.deepEqual(r2.responses, []);
});

test("不在项目路径下时指纹为 null", () => {
  const { calls } = setup([packet()], { pathname: "/c/plain-chat" });
  assert.equal(calls.sendMessage[0].project.projectFingerprint, null);
});
