console.log("Service Worker успешно запущен!");

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
    return u.origin + u.pathname; // без ?query и #hash
  } catch {
    return url;
  }
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
    if (!url || url.startsWith('chrome://') || url.startsWith('edge://') || url.startsWith('about:')) {
        return null;
    }
    if (isSafeDomain(url)){
        return;
    }
    const cleanUrl = normalizeUrl(url);
    try {
        const response = await fetch('http://localhost:1337/guardai/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: cleanUrl })
        });
        const data = await response.json();
        console.log(`Проскановано URL ${url} -> ${cleanUrl}`, data);
        return data;
    } catch (error) {
        console.error(`Помилка відправки на webserver`, error);
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

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "STATE_CHANGED" && message.enabled) {
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

                if (tabId) {
                    try {
                        await chrome.tabs.sendMessage(tabId, {
                            action: "URL_BLOCKED",
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

    if (message.action === "UNBLOCK_URL" && message.url) {
        const ruleId = hashCode(message.url);
        chrome.declarativeNetRequest.updateDynamicRules({
            removeRuleIds: [ruleId]
        }).then(() => {
            console.log("Unblocked:", message.url);
        });
        return;
    }

    return true;
});


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
