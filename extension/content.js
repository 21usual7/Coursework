chrome.storage.local.get({ isEnabled: true }, function (result) {
  toggleExtensionWork(result.isEnabled);
});


chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.isEnabled) {
    toggleExtensionWork(changes.isEnabled.newValue);
  }
});


function toggleExtensionWork(isEnabled) {
  chrome.runtime.sendMessage({
    action: "state_changed",
    enabled: !!isEnabled
  }).catch(() => {});
}


// Повідомлення від service worker
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.action === "url_blocked") {
    alertWindow(message.url || window.location.href);
  }
  return false;
});


function alertWindow(url) {
  const isConfirmed = confirm(
    "Цей URL є фішинговим. GUARD його заблокував.\n\n" +
    "URL: " + url + "\n\n" +
    "Залишити його заблокованим?"
  );

  if (!isConfirmed) {
    chrome.runtime.sendMessage({
      action: "unblock_url",
      url: url
    }).catch(() => {});
    alert("Розблоковую URL... Оновіть сторінку.");
  } else {
    alert("Ви вирішили залишити його заблокованим.");
  }
}
