document.addEventListener("DOMContentLoaded", async () => {
  const button = document.getElementById("button");
  const btnText = button.querySelector(".btn-text");
  const statusHint = document.getElementById("statusHint");

  // Load saved state
  const result = await chrome.storage.local.get({ isEnabled: true });
  updateUI(result.isEnabled);

  // Toggle on click
  button.addEventListener("click", async () => {
    const data = await chrome.storage.local.get({ isEnabled: true });
    const newState = !data.isEnabled;

    await chrome.storage.local.set({ isEnabled: newState });
    updateUI(newState);

    // Notify service worker
    try {
      await chrome.runtime.sendMessage({
        action: "STATE_CHANGED",
        enabled: newState
      });
    } catch (e) {
      console.warn("Could not notify service worker", e);
    }
  });

  function updateUI(isEnabled) {
    if (isEnabled) {
      button.classList.remove("off");
      button.classList.add("active");
      btnText.textContent = "Увімкнено";
      statusHint.textContent = "Захист активний";
    } else {
      button.classList.remove("active");
      button.classList.add("off");
      btnText.textContent = "Вимкнено";
      statusHint.textContent = "Захист вимкнено";
    }
  }
});
