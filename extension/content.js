console.log("Starting content")
chrome.storage.local.get({ isEnabled: true }, function (result) {
    toggleExtensionWork(result.isEnabled);
});
// Відстеження змін у storage (перемикання кнопки в popup)
chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.isEnabled) {
        toggleExtensionWork(changes.isEnabled.newValue);
    }
});

// Функція сповіщення background script про зміну стану
function toggleExtensionWork(isEnabled) {
    if (isEnabled) {
        chrome.runtime.sendMessage({ action: "STATE_CHANGED", enabled: true });
    } else {
        chrome.runtime.sendMessage({ action: "STATE_CHANGED", enabled: false });
    }
}

// Слухач повідомлень від service_worker.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "URL_BLOCKED" || message === "Url have been blocked") {
        alertWindow();
    }
});

// Вікно попередження користувача
function alertWindow() {
    const isConfirmed = confirm("Цей URL є фішинговим. GUARD його заблокував.\nЗалишити його заблокованим?");

    if (!isConfirmed) {
        chrome.runtime.sendMessage({ action: "UNBLOCK_URL" });
        alert("Розблоковую URL...");
    } else {
        alert("Ви вирішили залишити його заблокованим.");
    }
}
