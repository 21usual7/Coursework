console.log("Service Worker успішно запущено!");

const SAFE_DOMAINS = [
  "google.com", "www.google.com",
  "youtube.com", "www.youtube.com",
  "google.com.ua", "google.ru",
  "github.com", "wikipedia.org",
  "reddit.com", "stackoverflow.com",
  "microsoft.com", "apple.com"
];


function normalizeUrl(url) {
  try {
    const u = new URL(url);
    return u.origin + u.pathname;
  } catch {
    return url;
  }
}


async function isWhitelisted(url) {
  const { whitelist = [] } = await chrome.storage.local.get({ whitelist: [] });
  return whitelist.includes(normalizeUrl(url));
}


function isSafeDomain(url) {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return SAFE_DOMAINS.some(d => host === d || host.endsWith("." + d));
  } catch {
    return false;
  }
}


async function sendUrlToBackend(url) {
  if (!url || url.startsWith("chrome://") || url.startsWith("edge://") || url.startsWith("about:")) {
    return null;
  }
  if (isSafeDomain(url)) {
    return null;
  }

  if (await isWhitelisted(url)) {
    console.log(`Whitelist skip: ${url}`);
    return null;
  }

  const cleanUrl = normalizeUrl(url);

  try {
    const response = await fetch("https://coursework-ysbi.onrender.com/guardai/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: cleanUrl })
    });
    const data = await response.json();
    console.log(`Проскановано URL ${url} -> ${cleanUrl}`, data);
    return data;
  } catch (error) {
    console.error("Помилка відправки на webserver", error);
    return null;
  }
}


function hashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) % 2147483647 || 1;
}


async function addToBlockedHistory(url, probability) {
  const { blockedHistory = [] } = await chrome.storage.local.get({ blockedHistory: [] });

  if (blockedHistory[0]?.url === url) return;

  blockedHistory.unshift({
    url,
    probability: probability ?? null,
    time: Date.now()
  });

  if (blockedHistory.length > 50) blockedHistory.length = 50;
  await chrome.storage.local.set({ blockedHistory });
}


async function removeFromBlockedHistory(url) {
  const { blockedHistory = [] } = await chrome.storage.local.get({ blockedHistory: [] });
  const next = blockedHistory.filter((item) => item.url !== url);
  await chrome.storage.local.set({ blockedHistory: next });
}


async function unblockUrl(exactUrl) {
  const ruleId = hashCode(exactUrl);
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: [ruleId]
  });
  
  const { whitelist = [] } = await chrome.storage.local.get({ whitelist: [] });
  const cleanUrl = normalizeUrl(exactUrl);
  if (!whitelist.includes(cleanUrl)) {
    whitelist.push(cleanUrl);
    await chrome.storage.local.set({ whitelist });
  }

  await removeFromBlockedHistory(exactUrl);
  console.log("Unblocked & Whitelisted:", exactUrl);
}


async function blockUrl(ruleId, exactUrl) {
  const rule = {
    id: ruleId,
    priority: 1,
    action: { type: "block" },
    condition: {
      urlFilter: exactUrl,
      resourceTypes: ["main_frame", "sub_frame"]
    }
  };
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: [ruleId],
    addRules: [rule]
  });
}


chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.action) return;

  const action = message.action.toLowerCase();

  if (action === "state_changed" && message.enabled) {
    (async () => {
      const url = sender.tab?.url;
      const tabId = sender.tab?.id;
      if (!url) return;

      const data = await sendUrlToBackend(url);
      if (!data) return;

      const probability = typeof data.probability === "number"
        ? data.probability
        : parseFloat(data.probability) || 0;

      const isPhishing = data.is_phishing === true || probability > 0.9;

      if (isPhishing) {
        const ruleId = hashCode(url);
        await blockUrl(ruleId, url);
        await addToBlockedHistory(url, probability);

        if (tabId) {
          try {
            await chrome.tabs.sendMessage(tabId, {
              action: "url_blocked", 
              url: url
            });
          } catch (e) {
            console.log("Не зміг відправити повідомлення на вкладку", e);
          }
        }
      } else {
        console.log(`Safe: ${url} (prob=${probability})`);
      }
    })();
    return true;
  }

  // 2) разблокировка из popup / content 
  if (action === "unblock_url" && message.url) {
    unblockUrl(message.url).then(() => sendResponse({ ok: true }));
    return true;
  }

  // 3) отдать историю в popup
  if (action === "get_blocked_history") {
    chrome.storage.local.get({ blockedHistory: [] }).then((data) => {
      sendResponse({ history: data.blockedHistory || [] });
    });
    return true;
  }

  // 4) очистить только список
  if (action === "clear_blocked_history") {
    chrome.storage.local.set({ blockedHistory: [] }).then(() => {
      sendResponse({ ok: true });
    });
    return true;
  }

  return true;
});
