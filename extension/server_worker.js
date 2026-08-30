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
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            if (changeInfo.url) {
                data = sendUrlToBackend(changeInfo.url);
                if (data){
                    try {
                        await chrome.tabs.sendMessage(tabId){
                            message: data;
                        });
                    catch (error){
                        console.log("Не зміг відправити данні на content ");

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
