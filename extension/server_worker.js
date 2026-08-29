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
    } catch (error){
        console.error(`Помилка відправки на webserver`, error);
    }
}

// Відстеження зміни URL у всіх вкладках браузера
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.url) {
        sendUrlToBackend(changeInfo.url);
    }
});
