'''Графіки для звіту за результатами навчання моделі (training_metrics.txt) -> ml/charts/

Використання (з папки backend, потрібен matplotlib: pip install matplotlib):
    python ml/train_GUARD.py      # якщо модель перенавчена - оновити метрики
    python ml/draw_charts.py
'''
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ml_dir = Path(__file__).resolve().parent
METRICS = ml_dir.parent / "training_metrics.txt"
CHARTS = ml_dir / "charts"
THRESHOLD = 0.6

# підбір гіперпараметрів (п. 4.2 звіту): дерева, min_samples_leaf, файл МБ, RAM моделі МБ, recall@0.6,
# чи поміщається сервер у 512 МБ Render
HYPERPARAMS = [
    (50, 1, 99, 573, 0.725, False),
    (50, 3, 48, 213, 0.653, False),
    (30, 3, 29, 128, 0.655, True),
    (40, 5, 28, 110, 0.623, True),
    (60, 10, 28, 97, 0.587, True),
    (100, 20, 30, 92, 0.549, True),
]

BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def read_metrics():
    text = METRICS.read_text(encoding="utf-8")
    thresholds = [tuple(map(float, m)) for m in re.findall(
        r"поріг ([\d.]+): precision=([\d.]+) recall=([\d.]+) f1=([\d.]+) FPR=([\d.]+)", text)]
    classes = re.search(r"confusion matrix \((\[.*?\])\)", text).group(1)
    classes = re.findall(r"'(\w+)'", classes)
    matrix = re.search(r"confusion matrix .*?:\n(\[\[.*?\]\])", text, re.S).group(1)
    matrix = np.array([list(map(int, row.split())) for row in re.findall(r"\[([\d\s]+)\]", matrix)])
    top = re.search(r"топ-15 важливих ознак:\n((?:  .*\n)+)", text).group(1)
    importances = [(name, float(v)) for name, v in (line.split() for line in top.strip().splitlines())]
    return thresholds, classes, matrix, importances


def style(ax, grid="y"):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0)
    ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def title(ax, text):
    ax.set_title(text, loc="left", fontsize=12, color=INK, pad=10)


def draw_thresholds(thresholds):
    t, precision, recall, f1, fpr = (np.array(c) for c in zip(*thresholds))
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [3, 2]})
    for ax in (a, b):
        ax.axvline(THRESHOLD, color=INK_2, linewidth=1, linestyle="--")
        ax.text(THRESHOLD, 0.02, f" обрано {THRESHOLD}", transform=ax.get_xaxis_transform(),
                fontsize=9, color=INK_2, va="bottom")
        ax.set_xticks(t)
        ax.set_xlabel("поріг блокування", color=INK_2)
        style(ax)
    for values, label, color in ((precision, "precision", BLUE), (recall, "recall", ORANGE), (f1, "F1", AQUA)):
        a.plot(t, values * 100, color=color, linewidth=2, marker="o", markersize=7,
               markeredgecolor=SURFACE, markeredgewidth=2, label=label)
        a.annotate(f"{values[-1] * 100:.0f}%", (t[-1], values[-1] * 100), textcoords="offset points",
                   xytext=(8, -3), fontsize=9, color=INK)
    i = list(t).index(THRESHOLD)
    for values in (precision, recall):
        a.annotate(f"{values[i] * 100:.1f}%", (t[i], values[i] * 100), textcoords="offset points",
                   xytext=(6, 6), fontsize=9, color=INK)
    a.set_ylim(40, 100)
    a.set_ylabel("%", color=INK_2)
    a.legend(frameon=False, fontsize=10, loc="lower left")
    title(a, "Якість на тестовій вибірці (небезпечний / ні)")

    b.plot(t, fpr * 100, color=VIOLET, linewidth=2, marker="o", markersize=7,
           markeredgecolor=SURFACE, markeredgewidth=2)
    for x, v in zip(t, fpr):
        b.annotate(f"{v * 100:.1f}%", (x, v * 100), textcoords="offset points", xytext=(7, 7),
                   fontsize=9, color=INK)
    b.set_ylim(0, max(fpr) * 100 * 1.25)
    b.set_ylabel("% безпечних URL, заблокованих помилково", color=INK_2)
    title(b, "Хибні спрацювання (FPR)")
    fig.tight_layout()
    fig.savefig(CHARTS / "1_thresholds.png", dpi=150)
    plt.close(fig)


def draw_confusion(classes, matrix):
    share = matrix / matrix.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(7, 5.6))
    ax.imshow(share, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("blue", ["#f4f8fd", "#0d366b"]),
              vmin=0, vmax=1)
    for i in range(len(classes)):
        for j in range(len(classes)):
            color = "white" if share[i, j] > 0.55 else INK
            ax.text(j, i, f"{share[i, j] * 100:.1f}%\n{matrix[i, j]:,}".replace(",", " "),
                    ha="center", va="center", fontsize=10, color=color)
    ax.set_xticks(range(len(classes)), classes, color=INK)
    ax.set_yticks(range(len(classes)), classes, color=INK)
    ax.set_xlabel("передбачений клас", color=INK_2)
    ax.set_ylabel("справжній клас", color=INK_2)
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_xticks(np.arange(len(classes) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(classes) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    title(ax, "Матриця помилок (частка від справжнього класу)")
    fig.tight_layout()
    fig.savefig(CHARTS / "2_confusion_matrix.png", dpi=150)
    plt.close(fig)


def draw_importances(importances):
    names, values = zip(*importances)
    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.barh(names, values, height=0.65, color=BLUE)
    for i, v in enumerate(values):
        ax.text(v + 0.001, i, f"{v:.3f}", va="center", fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.tick_params(axis="y", colors=INK)
    ax.set_xlabel("важливість ознаки (feature_importances_)", color=INK_2)
    style(ax, grid="x")
    title(ax, "Топ-15 ознак RandomForest")
    fig.tight_layout()
    fig.savefig(CHARTS / "3_feature_importances.png", dpi=150)
    plt.close(fig)


def draw_hyperparams():
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for trees, leaf, size, ram, recall, fits in HYPERPARAMS:
        chosen = (trees, leaf) == (30, 3)
        color = BLUE if fits else "#b9b8b3"
        ax.scatter(ram, recall * 100, s=110 if chosen else 70, color=color,
                   edgecolors=INK if chosen else SURFACE, linewidths=2 if chosen else 1.5, zorder=3)
        label = f"{trees} дерев, leaf={leaf}\nфайл {size} МБ" + ("  <- обрано" if chosen else "")
        ax.annotate(label, (ram, recall * 100), textcoords="offset points", xytext=(0, 14) if chosen else (9, -4),
                    ha="center" if chosen else "left", va="bottom" if chosen else "center_baseline", fontsize=8.5, color=INK if fits else INK_2, fontweight="bold" if chosen else "normal")
    ax.scatter([], [], color=BLUE, label="сервер поміщається в 512 МБ Render")
    ax.scatter([], [], color="#b9b8b3", label="не поміщається")
    ax.set_xlabel("пам'ять, яку займає модель, МБ", color=INK_2)
    ax.set_ylabel("recall при порозі 0.6, %", color=INK_2)
    ax.set_xlim(60, 700)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    title(ax, "Підбір гіперпараметрів: якість проти пам'яті")
    fig.tight_layout()
    fig.savefig(CHARTS / "4_hyperparameters.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    CHARTS.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": SURFACE})
    thresholds, classes, matrix, importances = read_metrics()
    draw_thresholds(thresholds)
    draw_confusion(classes, matrix)
    draw_importances(importances)
    draw_hyperparams()
    print(f"графіки збережено в {CHARTS}")
