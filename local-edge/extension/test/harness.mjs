// 轻量测试夹具：用 node:vm 加载扩展脚本，模拟 chrome.* API 和所需的最小 DOM。无第三方依赖。
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

// vm 上下文中的对象原型属于另一个 realm；记录前转成本 realm 的普通 JSON 值，便于 deepStrictEqual 比较
const plain = (v) => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));

const EXT_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");

export function createChrome({ storage = {}, tabs = [], nativeReply, nativeError, tabMessageReply } = {}) {
  const data = { ...storage };
  const listeners = [];
  const calls = { sendMessage: [], sendNativeMessage: [], tabsSendMessage: [], tabsQuery: [] };
  const chrome = {
    runtime: {
      lastError: undefined,
      onMessage: { addListener: (fn) => listeners.push(fn) },
      sendMessage: (msg) => { calls.sendMessage.push(plain(msg)); },
      sendNativeMessage: (host, msg, cb) => {
        calls.sendNativeMessage.push({ host, msg: plain(msg) });
        setImmediate(() => {
          chrome.runtime.lastError = nativeError ? { message: nativeError } : undefined;
          cb(nativeError ? undefined : nativeReply);
          chrome.runtime.lastError = undefined;
        });
      },
    },
    storage: {
      local: {
        get: async (keys) => Object.fromEntries(keys.filter((k) => k in data).map((k) => [k, structuredClone(data[k])])),
        set: async (obj) => { Object.assign(data, plain(obj)); },
        remove: async (keys) => { for (const k of keys) delete data[k]; },
      },
    },
    tabs: {
      query: async (q) => { calls.tabsQuery.push(plain(q)); return tabs; },
      sendMessage: async (id, msg) => { calls.tabsSendMessage.push({ id, msg: plain(msg) }); return tabMessageReply; },
    },
  };
  return { chrome, data, listeners, calls };
}

/** 依次调用已注册的 onMessage 监听器，返回 {returned, responses} */
export function dispatch(listeners, message) {
  const responses = [];
  const returned = listeners.map((fn) => fn(message, {}, (r) => responses.push(plain(r))));
  return { returned, responses };
}

export async function flush(times = 10) {
  for (let i = 0; i < times; i++) await new Promise((r) => setImmediate(r));
}

class FakeElement {
  constructor({ textContent = "", href } = {}) {
    this.textContent = textContent;
    this.href = href;
    this.handlers = {};
  }
  addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }
  async click() { for (const fn of this.handlers.click || []) await fn(); }
}

export function el(opts) { return new FakeElement(opts); }

/**
 * 创建最小 document：selectors 是 { 选择器: 元素或元素数组 }，
 * querySelector / querySelectorAll 只按完全相同的选择器字符串查找。
 */
export function createDocument(selectors = {}) {
  const observers = [];
  const document = {
    documentElement: {},
    querySelector: (sel) => { const v = selectors[sel]; return Array.isArray(v) ? v[0] ?? null : v ?? null; },
    querySelectorAll: (sel) => { const v = selectors[sel]; return v === undefined ? [] : Array.isArray(v) ? v : [v]; },
  };
  class MutationObserver {
    constructor(cb) { this.cb = cb; observers.push(this); }
    observe(target, options) { this.target = target; this.options = options; }
    trigger() { this.cb([], this); }
  }
  return { document, selectors, observers, MutationObserver };
}

export function loadScript(file, globals) {
  const code = readFileSync(join(EXT_DIR, file), "utf8");
  const context = vm.createContext({ ...globals, setImmediate, structuredClone, console });
  vm.runInContext(code, context, { filename: file });
  return context;
}
