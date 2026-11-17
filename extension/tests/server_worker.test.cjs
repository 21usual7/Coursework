const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "../server_worker.js"), "utf8");

function worker(initial = {}, fetchImpl) {
  const local = structuredClone(initial);
  const session = {};
  const calls = { fetch: [], rules: [], tabs: [] };
  let navigate;
  let onMessage;
  const storage = (state) => ({
    async get(defaults) { return structuredClone({ ...defaults, ...state }); },
    async set(values) { Object.assign(state, structuredClone(values)); }
  });
  const context = vm.createContext({
    URL, AbortSignal,
    console: { log() {}, error() {} },
    chrome: {
      storage: { local: storage(local), session: storage(session) },
      declarativeNetRequest: {
        async updateDynamicRules(rules) { calls.rules.push(rules); }
      },
      tabs: { async update(id, options) { calls.tabs.push({ id, ...options }); } },
      webNavigation: { onBeforeNavigate: { addListener(fn) { navigate = fn; } } },
      runtime: {
        getURL: (path) => `chrome-extension://guard/${path}`,
        onMessage: { addListener(fn) { onMessage = fn; } }
      }
    },
    async fetch(endpoint, options) {
      calls.fetch.push({ endpoint, ...options });
      if (fetchImpl) return fetchImpl(endpoint, options);
      return { json: async () => ({ status: "success", is_phishing: false, probability: 0.1 }) };
    }
  });
  vm.runInContext(source, context);
  return {
    local, calls, context,
    navigate: (url, extra = {}) => navigate({ url, tabId: 1, frameId: 0, ...extra }),
    message: (message) => new Promise((resolve) => onMessage(message, {}, resolve))
  };
}

test("disabled protection and subframes do not scan", async () => {
  const disabled = worker({ isEnabled: false });
  await disabled.navigate("https://example.com/");
  assert.equal(disabled.calls.fetch.length, 0);
  const enabled = worker();
  await enabled.navigate("https://example.com/", { frameId: 1 });
  assert.equal(enabled.calls.fetch.length, 0);
});

test("trusted subdomains skip scanning, lookalike domains do not", async () => {
  const w = worker();
  await w.navigate("https://accounts.google.com/");
  assert.equal(w.calls.fetch.length, 0);
  await w.navigate("https://google.com.evil.example/");
  assert.equal(w.calls.fetch.length, 1);
});

test("browser internal pages skip scanning", async () => {
  const w = worker();
  for (const url of ["about:blank", "chrome://settings", "moz-extension://guard/page", "chrome-extension://guard/page"]) {
    await w.navigate(url);
  }
  assert.equal(w.calls.fetch.length, 0);
});

test("cache ignores fragments and distinguishes query parameters", async () => {
  const w = worker();
  await w.navigate("https://example.com/?id=1#first");
  await w.navigate("https://example.com/?id=1#second");
  await w.navigate("https://example.com/?id=2");
  assert.equal(w.calls.fetch.length, 2);
  assert.equal(JSON.parse(w.calls.fetch[0].body).url, "https://example.com/?id=1");
});

test("expired cache entries are scanned again", async () => {
  const w = worker();
  await w.navigate("https://example.com/");
  vm.runInContext("Date.now = () => 4102444800000", w.context);
  await w.navigate("https://example.com/");
  assert.equal(w.calls.fetch.length, 2);
});

test("phishing creates a block rule, history entry and warning page", async () => {
  const w = worker({}, async () => ({
    json: async () => ({ status: "success", is_phishing: true, probability: 0.9 })
  }));
  const url = "https://paypal-login.example/signin";
  await w.navigate(url);
  assert.equal(w.calls.rules[0].addRules[0].action.type, "block");
  assert.equal(w.local.blockedHistory[0].url, url);
  assert.equal(new URL(w.calls.tabs[0].url).searchParams.get("url"), url);
  const response = await w.message({ action: "unblock_url", url });
  assert.equal(response.ok, true);
  assert.equal(w.calls.rules[1].removeRuleIds[0], w.calls.rules[0].addRules[0].id);
  assert.equal(w.local.blockedHistory.length, 0);
  await w.navigate(url);
  assert.equal(w.calls.fetch.length, 1);
  assert.equal(w.calls.tabs.length, 1);
});

test("network failures and API errors are not cached", async () => {
  for (const fetchImpl of [
    async () => { throw new Error("offline"); },
    async () => ({ json: async () => ({ status: "error", message: "Too many requests" }) })
  ]) {
    const w = worker({}, fetchImpl);
    await w.navigate("https://example.com/");
    await w.navigate("https://example.com/");
    assert.equal(w.calls.fetch.length, 2);
    assert.equal(w.calls.tabs.length, 0);
  }
});

test("clearing history keeps whitelist entries", async () => {
  const w = worker({ whitelist: ["https://example.com/"], blockedHistory: [{ url: "https://evil.example/" }] });
  await w.message({ action: "clear_blocked_history" });
  assert.equal(w.local.blockedHistory.length, 0);
  assert.deepEqual(w.local.whitelist, ["https://example.com/"]);
});
