import { test } from "node:test";
import assert from "node:assert/strict";
import { createChrome, createDocument, el, flush, loadScript } from "./harness.mjs";

function setup(chromeOpts) {
  const nodes = { "#binding": el(), "#status": el(), "#bind": el(), "#unbind": el() };
  const dom = createDocument(nodes);
  const c = createChrome(chromeOpts);
  loadScript("popup.js", { document: dom.document, chrome: c.chrome });
  return { ...c, nodes };
}

const chatTab = { id: 7, url: "https://chatgpt.com/g/g-p-abc123/project" };

test("未绑定时显示“未绑定项目”和空状态", async () => {
  const { nodes } = setup();
  await flush();
  assert.equal(nodes["#binding"].textContent, "未绑定项目");
  assert.equal(nodes["#status"].textContent, "{}");
});

test("已绑定时显示项目名，没有名称时退回指纹", async () => {
  let s = setup({ storage: { boundProjectName: "My Project", boundProjectFingerprint: "g-p-abc123" } });
  await flush();
  assert.equal(s.nodes["#binding"].textContent, "已绑定：My Project");
  s = setup({ storage: { boundProjectFingerprint: "g-p-abc123" } });
  await flush();
  assert.equal(s.nodes["#binding"].textContent, "已绑定：g-p-abc123");
});

test("点击绑定：从当前 ChatGPT 标签读取项目并保存", async () => {
  const { nodes, data, calls } = setup({
    tabs: [chatTab],
    tabMessageReply: { projectName: "My Project", projectFingerprint: "g-p-abc123" },
  });
  await nodes["#bind"].click();
  await flush();
  assert.deepEqual(calls.tabsQuery, [{ active: true, currentWindow: true }]);
  assert.deepEqual(calls.tabsSendMessage, [{ id: 7, msg: { type: "inspect-project" } }]);
  assert.equal(data.boundProjectName, "My Project");
  assert.equal(data.boundProjectFingerprint, "g-p-abc123");
  assert.deepEqual(data.lastStatus, { ok: true, message: "Project bound; no local task executed." });
  assert.equal(nodes["#binding"].textContent, "已绑定：My Project");
});

test("当前标签不是 ChatGPT 时不绑定并记录错误", async () => {
  const { nodes, data, calls } = setup({ tabs: [{ id: 3, url: "https://example.com/" }] });
  await nodes["#bind"].click();
  await flush();
  assert.equal(calls.tabsSendMessage.length, 0);
  assert.equal(data.boundProjectFingerprint, undefined);
  assert.deepEqual(data.lastStatus, { ok: false, error: "Error: 当前标签不是 ChatGPT" });
});

test("无法确认项目名或指纹时不绑定", async () => {
  for (const reply of [{ projectFingerprint: "g-p-abc123", projectName: null }, { projectName: "X", projectFingerprint: null }, undefined]) {
    const { nodes, data } = setup({ tabs: [chatTab], tabMessageReply: reply });
    await nodes["#bind"].click();
    await flush();
    assert.equal(data.boundProjectFingerprint, undefined);
    assert.deepEqual(data.lastStatus, { ok: false, error: "Error: 无法确认当前项目归属" });
  }
});

test("点击解除绑定：删除绑定并更新状态", async () => {
  const { nodes, data } = setup({ storage: { boundProjectName: "P", boundProjectFingerprint: "g-p-abc123" } });
  await nodes["#unbind"].click();
  await flush();
  assert.equal(data.boundProjectName, undefined);
  assert.equal(data.boundProjectFingerprint, undefined);
  assert.deepEqual(data.lastStatus, { ok: true, message: "Project unbound." });
  assert.equal(nodes["#binding"].textContent, "未绑定项目");
});
