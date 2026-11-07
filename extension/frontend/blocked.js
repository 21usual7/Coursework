document.addEventListener("DOMContentLoaded", () => {
  const url = new URLSearchParams(location.search).get("url") || "";
  document.getElementById("blockedUrl").textContent = url;

  document.getElementById("closeTab").addEventListener("click", async () => {
    const tab = await chrome.tabs.getCurrent();
    chrome.tabs.remove(tab.id);
  });

  // Розблоковує URL (додає до whitelist) і відкриває його
  document.getElementById("proceed").addEventListener("click", async () => {
    try {
      await chrome.runtime.sendMessage({ action: "unblock_url", url: url });
    } catch (e) {
      console.warn("Unblock failed", e);
    }
    location.href = url;
  });
});
