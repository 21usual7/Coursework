// керує інтерфейсом вспливаючого вікна (кнопка вкл/вкл, збереження налаштувань).
document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("button");
    const btnText = button.querySelector(".btn-text");

    chrome.storage.local.get({isEnabled : true}, (result) => {
        updateUI(isEnabled);
    });

    button.addEventListener("click", () => {
        chrome.storage.local.get({isEnabled : true}, (result) => {
            const newState = !currentState;

            chrome.storage.local.set({isEnabled: newState}, () => {
                updateUI(newState);
            });
        });
    });

    // оновлення зовнішнього виду кнопки
    function updateUI(isEnabled) {
        if (isEnabled) {
            button.classList.remove("off");
            button.classList.add("active");
            btnText.textContent = "Увімкнено";
        } else {
            button.classList.remove("active")
            button.classList.add("off");
            btnText.textContent = "Вимкнено";
        }
    }
});
