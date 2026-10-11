import { test } from "node:test";
import assert from "node:assert/strict";
import { createChrome, dispatch, flush, loadScript } from "./harness.mjs";

const BOUND = { boundProjectName: "P", boundProjectFingerprint: "g-p-abc123" };
const candidate = (fingerprint) => ({
  type: "handoff-candidate",
  packet: { protocol: "rwrouter/1.1", task_id: "t-1" },
  project: { projectFingerprint: fingerprint },
});

function setup(opts) {
  const c = createChrome(opts);
  loadScript("service_worker.js", { chrome: c.chrome });
  return c;
}

test("非 handoff-candidate 消息直接忽略（不返回 true、不响应）", async () => {
  const { listeners, calls } = setup({ storage: BOUND });
  const { returned, responses } = dispatch(listeners, { type: "inspect-project" });
  await flush();
  assert.deepEqual(returned, [undefined]);
  assert.deepEqual(responses, []);
  assert.equal(calls.sendNativeMessage.length, 0);
});

test("项目指纹与绑定不一致时拒绝，不调用本地宿主", async () => {
  const { listeners, calls, data } = setup({ storage: BOUND });
  const { returned, responses } = dispatch(listeners, candidate("g-p-other"));
  assert.deepEqual(returned, [true], "异步响应需要返回 true");
  await flush();
  const expected = { ok: false, error: "Rejected: handoff is outside the bound ChatGPT Project" };
  assert.deepEqual(responses, [expected]);
  assert.deepEqual(data.lastStatus, expected);
  assert.equal(calls.sendNativeMessage.length, 0);
});

test("未绑定或缺少指纹时拒绝", async () => {
  for (const [storage, fp] of [[{}, "g-p-abc123"], [BOUND, undefined], [{}, undefined]]) {
    const { listeners, calls } = setup({ storage });
    const { responses } = dispatch(listeners, candidate(fp));
    await flush();
    assert.equal(responses[0].ok, false);
    assert.equal(calls.sendNativeMessage.length, 0);
  }
});

test("指纹一致时转发给本地宿主并保存回复", async () => {
  const reply = { ok: true, accepted: "t-1" };
  const { listeners, calls, data } = setup({ storage: BOUND, nativeReply: reply });
  const { responses } = dispatch(listeners, candidate("g-p-abc123"));
  await flush();
  assert.equal(calls.sendNativeMessage.length, 1);
  assert.equal(calls.sendNativeMessage[0].host, "com.roy.reverse_web_router");
  assert.deepEqual(calls.sendNativeMessage[0].msg, {
    project_fingerprint: "g-p-abc123",
    packet: { protocol: "rwrouter/1.1", task_id: "t-1" },
  });
  assert.deepEqual(responses, [reply]);
  assert.deepEqual(data.lastStatus, reply);
});

test("本地宿主报错（lastError）时返回并保存错误", async () => {
  const { listeners, data } = setup({ storage: BOUND, nativeError: "Specified native messaging host not found." });
  const { responses } = dispatch(listeners, candidate("g-p-abc123"));
  await flush();
  const expected = { ok: false, error: "Specified native messaging host not found." };
  assert.deepEqual(responses, [expected]);
  assert.deepEqual(data.lastStatus, expected);
});
