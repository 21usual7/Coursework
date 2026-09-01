// Керує інтерфейсом спливаючого вікна (кнопка увімк/вимк, збереження налаштувань)
console.log("HELLO WORLD!")
document.addEventListener("DOMContentLoaded", async () => {
    const button = document.getElementById("button");
    const btnText = button.querySelector(".btn-text");

    // Початкове завантаження стану
    const result = await chrome.storage.local.get({ isEnabled: true });
    updateUI(result.isEnabled);

    // Обробка кліку
    button.addEventListener("click", async () => {
        // Отримуємо поточний стан
        const data = await chrome.storage.local.get({ isEnabled: true });
        const newState = !data.isEnabled;

        // Зберігаємо новий стан та оновлюємо UI
        await chrome.storage.local.set({ isEnabled: newState });
        updateUI(newState);
    });

    // Оновлення зовнішнього вигляду кнопки
    function updateUI(isEnabled) {
        if (isEnabled) {
            button.classList.remove("off");
            button.classList.add("active");
            btnText.textContent = "Увімкнено";
        } else {
            button.classList.remove("active");
            button.classList.add("off");
            btnText.textContent = "Вимкнено";
        }
    }
});
