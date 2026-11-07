document.addEventListener("DOMContentLoaded", async () => {
  const button = document.getElementById("button");
  const btnText = button.querySelector(".btn-text");
  const statusHint = document.getElementById("statusHint");
  const historyList = document.getElementById("historyList");
  const clearBtn = document.getElementById("clearHistory");
  const historyPanel = document.getElementById("historyPanel");
  const historyCount = document.getElementById("historyCount");

  // ----- Панель заблокованих (виїжджає справа) -----
  document.getElementById("historyToggle").addEventListener("click", async () => {
    await loadHistory();
    document.body.classList.add("panel-open");
    historyPanel.classList.add("open");
  });

  document.getElementById("historyClose").addEventListener("click", () => {
    historyPanel.classList.remove("open");
    document.body.classList.remove("panel-open");
  });

  // ----- toggle -----
  const result = await chrome.storage.local.get({ isEnabled: true });
  updateUI(result.isEnabled);

  button.addEventListener("click", async () => {
    const data = await chrome.storage.local.get({ isEnabled: true });
    const newState = !data.isEnabled;
    await chrome.storage.local.set({ isEnabled: newState });
    updateUI(newState);
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

  // ----- Історія блокувань -----
  async function loadHistory() {
    if (!historyList) return;

    let history = [];
    try {
      const res = await chrome.runtime.sendMessage({ action: "get_blocked_history" }); // Виправлено
      history = res?.history || [];
    } catch (e) {
      console.warn("Не вдалося отримати історію", e);
    }

    historyList.innerHTML = "";
    historyCount.textContent = history.length;

    if (!history.length) {
      historyList.innerHTML = '<li class="empty">Поки нічого не заблоковано</li>';
      return;
    }

    for (const [i, item] of history.entries()) {
      const li = document.createElement("li");
      li.className = "history-item";
      // картки з'являються по черзі
      li.style.animationDelay = `${i * 60}ms`;

      const info = document.createElement("div");
      info.className = "history-info";

      const prob =
        item.probability != null
          ? `${Math.round(Number(item.probability) * 100)}%`
          : "—";

      info.innerHTML = `
        <a class="history-url" href="${escapeHtml(item.url)}" target="_blank" title="${escapeHtml(item.url)}">
          ${escapeHtml(truncate(item.url, 42))}
        </a>
        <span class="history-meta">${formatTime(item.time)} <b class="history-prob">${prob}</b></span>
      `;

      const unblockBtn = document.createElement("button");
      unblockBtn.type = "button";
      unblockBtn.className = "btn-unblock";
      unblockBtn.textContent = "Розблокувати";

      unblockBtn.addEventListener("click", async () => {
        unblockBtn.disabled = true;
        li.classList.add("removing");
        try {
          await chrome.runtime.sendMessage({
            action: "unblock_url", // Виправлено на нижній регістр
            url: item.url
          });
        } catch (e) {
          console.warn("Unblock failed", e);
        }
        setTimeout(() => loadHistory(), 200);
      });

      li.appendChild(info);
      li.appendChild(unblockBtn);
      historyList.appendChild(li);
    }
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      try {
        await chrome.runtime.sendMessage({ action: "clear_blocked_history" }); 
      } catch (_) {}
      await loadHistory();
    });
  }

  function truncate(str, n) {
    if (!str) return "";
    return str.length > n ? str.slice(0, n) + "…" : str;
  }

  function formatTime(ts) {
    try {
      return new Date(ts).toLocaleString("uk-UA", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch {
      return "";
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  await loadHistory();
});
