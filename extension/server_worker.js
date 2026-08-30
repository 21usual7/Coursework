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
                    await chrome.tabs.sendMessage(tabId){
                        message: url;
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
