console.log("Service Worker успешно запущен!");
    // Функція відправки посилання на webserver
async function sendUrlToBackend(url) {
    // Ігнорування службових сторінок браузера
    if (!url || url.startsWith('chrome://') || url.startsWith('edge://') || url.startsWith('about:')) {
        return null;
    }

    try {
        const response = await fetch('http://guardai/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });
        const data = await response.json();
        console.log(`Проскановано URL ${url}`, data);
        return data;
    } catch (error) {
        console.error(`Помилка відправки на webserver`, error);
        return null;
    }
}

function parse(string) {
    if (!string) return 0;
    const pattern = /\d+(?:\.\d+)?(?=%)/;
    const match = String(string).match(pattern);
    return match ? parseFloat(match[0]) : 0;
}

// Відстеження зміни URL у всіх вкладках браузера
chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
    if (message.action === "STATE Changed" && message.enabled) {
        const url = sender.tab?.url;
        const tabId = sender.tab?.id;
        if (url) {
            const data = await sendUrlToBackend(url);
            if (data && data.probability) {
                const probability = parse(data.probability);
                const isPhishingInt = Math.trunc(probability);

                await blockUrl(1, url, isPhishingInt);

                if (tabId) {
                    try {
                        await chrome.tabs.sendMessage(tabId, { action: "URL_BLOCKED", message: "Url have been blocked" });
                    } catch (e) {
                        console.log("Не зміг відправити повідомлення на вкладку", e);
                    }
                }
            } else {
                console.log("APP повернув пусті данні або помилку!");
            }
        }
    }
});

/**
 * @param {number} ruleId
 * @param {string} exactUrl
 * @param {number} probabilityIsPhishing
 */

async function blockUrl(ruleId, exactUrl, probabilityIsPhishing) {
    const strictFilter = `|${exactUrl}|`;
    const rule = {
        id: ruleId,
        priority: 1,
        action: {
            type: "block"
        },
        condition: {
            urlFilter: strictFilter,
            resourceTypes: ["main_frame", "sub_frame", "script", "xmlhttprequest", "image"]
        }
    };

    if (probabilityIsPhishing > 50) {
        await chrome.declarativeNetRequest.updateDynamicRules({
            removeRuleIds: [ruleId],
            addRules: [rule]
        });
    }
}
