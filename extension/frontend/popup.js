// керує інтерфейсом спливаючого вікна (кнопка увімк/вимк, збереження налаштувань)
document.addEventListener("DOMContentLoaded", async () => {
    const button = document.getElementById("button");
    const btnText = button.querySelector(".btn-text");

    const result = await chrome.storage.local.get({ isEnabled: true });
    updateUI(result.isEnabled);
    // обробка кліку
    button.addEventListener("click", async () => {
        // отримуємо поточний стан
        const data = await chrome.storage.local.get({ isEnabled: true });
        const newState = !data.isEnabled;

        // зберігаємо новий стан та оновлюємо UI
        await chrome.storage.local.set({ isEnabled: newState });
        updateUI(newState);
    });

    // оновлення зовнішнього вигляду кнопки
    function updateUI(isEnabled) {
        if (isEnabled) {
            button.classList.remove("off");
            button.classList.add("active");
            btnText.textContent = "увімкнено";
        } else {
            button.classList.remove("active");
            button.classList.add("off");
            btnText.textContent = "вимкнено";
        }
    }
});
