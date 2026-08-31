// Функція відправки посилання на webserver
async function sendUrlToBackend(url) {
    // Ігнорування службових сторінок браузера
    if (!url || url.startsWith('chrome://') || url.startsWith('edge://') || url.startsWith('about:')) {
        return;
    }

    try {
        const response = await fetch('http://guardai/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({url: url})
        });
        const data = await response.json();
        console.log(`Проскановано URL ${url}`, data);
        return data;
        }
    } catch (error){
        console.error(`Помилка відправки на webserver`, error);
    }
}

// Відстеження зміни URL у всіх вкладках браузера
chrome.runtime.onMessage((message, sender, sendResponse){
    if (message.action == "STATE Changed" && message.enabled){
        if (message) {
        const url = sender.tab?.url;
        const tabID = sender.tab?.id;
            if (url){
                try {
                    const data = JSON.parse(sendUrlToBackend(url))
                catch (error){
                    console.log("Не зміг відправити данні на content ");

                }

                const isPhishingInt = Math.Trunc(parse());
                blockUrl(1, url, isPhishingInt);
                try{
                    chrome.tabs.sendMessage(tabId, {"Url have been blocked"});
                }
                catch(e){
                    console.log("Не зміг відправити повідомлення");
                }
                else {
                    console.log("APP повернув пусті данні!");
                }
            }

        }
    }
    });
}
});


@param {number} ruleId;
@param {string} exactUrl
async function blockUrl(ruleId, exactUrl, probabilityIsPhising){
    const strictFilter = `|${exactUrl}|`;
    const rule = {
        id: ruleId,
        priority: 1,
        action: {
        type: "block"
        },
        condition: {
        urlFilter: staticFilter,
        resourceTypes: ["main_frame", "sub_frame", "script", "xmlhttprequest", "image"]
        }
    };
    if (probabilityIsPhising > 50){
        await chrome.declarativeNetRequest.updateDynamicRules({
            removeRuleIds: [ruleId],
            addRules: [rule]
    }
  });
}

function parse(string){
    const pattern = \d+(?:\.\d+)?(?=%);
    return string.match(pattern);
}

