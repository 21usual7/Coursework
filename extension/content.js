console.log("Starting content")
chrome.storage.local.get({ isEnabled: true }, function (result) {
    console.log(1)
    toggleExtensionWork(result.isEnabled);
});
// Відстеження змін у storage (перемикання кнопки в popup)
chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.isEnabled) {
        console.log(2)
        toggleExtensionWork(changes.isEnabled.newValue);
    }
});

// Функція сповіщення background script про зміну стану
function toggleExtensionWork(isEnabled) {
    if (isEnabled) {
        console.log(3)
        chrome.runtime.sendMessage({ action: "STATE_CHANGED", enabled: true });
    } else {
        console.log(4)
        chrome.runtime.sendMessage({ action: "STATE_CHANGED", enabled: false });
    }
}

// Слухач повідомлень від service_worker.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
if (message && message.action === "URL_BLOCKED") {
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
