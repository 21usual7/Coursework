# GUARD AI

Розширення для Chrome, яке захищає від фішингу. Кожен URL перед завантаженням сторінки
перевіряється сервером: модель машинного навчання (RandomForest) + правила для очевидних
ознак фішингу. Якщо сайт небезпечний, замість нього відкривається сторінка-попередження.

## Як це працює

```
Chrome ──(onBeforeNavigate)──> server_worker.js ──POST /guardai/api/scan──> Flask (Render)
                                     │                                         │
                          небезпечно │                       модель RandomForest (47 ознак URL)
                                     ▼                     + правила (бренд на чужому домені, '@',
                              blocked.html                   IP замість домену, ...)
                                                           + перевірка перенаправлень
                                                             (для коротких посилань і "сірої зони")
                                                           + Google Safe Browsing (база відомих загроз)
```

Підсумкова оцінка = максимум з оцінок моделі, правил і (за потреби) кінцевої адреси
після перенаправлень. Якщо URL є в базі Google Safe Browsing — 1.0. Сайт блокується
при оцінці ≥ 0.6.

## Структура

```
backend/
  app.py                      Flask-сервер, API /guardai/api/scan
  check_isPhishing.py         модель + правила + перевірка перенаправлень
  check_rules.py              правила поверх моделі
  check_ssl_and_redirects.py  перехід по перенаправленнях (із захистом від SSRF)
  safebrowsing.py             перевірка в базі Google Safe Browsing
  tests/test_guard.py         тести (pytest)
  training_metrics.txt        метрики останнього навчання
  ml/
    extract_features.py       нормалізація URL і 47 ознак
    train_GUARD.py            навчання моделі
    augment_benign.py         генерація benign-URL зі списку популярних сайтів Tranco
    draw_charts.py            графіки за training_metrics.txt -> ml/charts/
    coursework.pkl            навчена модель
    malicious_phish_cleaned.csv   датасет (642 861 URL, 4 класи)
    tranco_benign.csv         47 880 benign-URL популярних сайтів
extension/
  manifest.json
  server_worker.js            перевірка URL, блокування, кеш, білий список
  frontend/
    popup.html / .js / .css   попап: увімкнення, панель заблокованих сайтів
    blocked.html / .js        сторінка-попередження
```

## Запуск сервера локально

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                   # http://localhost:5000
```

Ключ Google Safe Browsing (необов'язково — без нього ця перевірка просто пропускається):
створити ключ у Google Cloud Console (APIs & Services → Credentials, обмежити до
«Safe Browsing API») і покласти в `backend/.env`:

```
GSB_API_KEY=ваш_ключ
```

`.env` є в `.gitignore` і в репозиторій не потрапляє. На Render ключ задається в
Environment → `GSB_API_KEY`.

Перевірка:

```bash
curl -X POST http://localhost:5000/guardai/api/scan \
  -H "Content-Type: application/json" \
  -d '{"url": "http://paypal-login-verify.xyz/signin"}'
```

Відповідь:

```json
{
  "status": "success",
  "url": "http://paypal-login-verify.xyz/signin",
  "is_phishing": true,
  "probability": 0.9,
  "threat_type": "phishing",
  "reasons": ["назва бренду 'paypal' на чужому домені paypal-login-verify.xyz", "..."]
}
```

Версії бібліотек у `requirements.txt` зафіксовані: `coursework.pkl` завантажується лише
тією версією scikit-learn, якою модель навчена (1.9.0).

## Тести

```bash
cd backend
pip install pytest
python -m pytest tests -q
```

36 тестів: ознаки, правила, захист від SSRF, підсумкова перевірка, API (зокрема
обмеження частоти запитів). Мережеві перевірки підмінено заглушками — тести не
звертаються до Google і працюють без інтернету.

## Встановлення розширення

1. Відкрити `chrome://extensions`
2. Увімкнути «Режим розробника»
3. «Завантажити розпаковане» → вибрати папку `extension/`

Розширення звертається до сервера на Render (`server_worker.js`, адреса
`coursework-ysbi.onrender.com`). Для локального сервера змінити адресу на
`http://localhost:5000/guardai/api/scan`.

## Повторне навчання моделі

```bash
cd backend
# 1. Список популярних сайтів: https://tranco-list.eu/top-1m.csv.zip -> розпакувати top-1m.csv
python ml/augment_benign.py шлях/до/top-1m.csv   # -> ml/tranco_benign.csv
# 2. Навчання (~2 хв)
python ml/train_GUARD.py                          # -> ml/coursework.pkl, training_metrics.txt
# 3. Графіки (потрібен matplotlib, лише локально)
python ml/draw_charts.py                          # -> ml/charts/*.png
```

## Результати

| Метрика | Значення |
|---|---|
| ROC-AUC (безпечний / небезпечний) | 0.955 |
| Precision / recall при порозі 0.6 | 0.944 / 0.655 |
| Хибні тривоги на незнайомих популярних сайтах | 1.5% |
| Розмір моделі / пам'ять сервера | 29 МБ / ~440 МБ |

Повні метрики — у `backend/training_metrics.txt`.

## Обмеження

- API обмежено до 60 запитів на хвилину і 1000 на добу з однієї IP-адреси (далі — відповідь 429).
  URL довший за 2048 символів не приймається (400), тіло запиту більше 16 КБ — (413).
  Лічильники зберігаються в пам'яті сервера і скидаються при його перезапуску чи засинанні.
- Аналізується лише рядок URL, не вміст сторінки.
- Безкоштовний Render засинає після 15 хв простою і прокидається 30–60 с; у цей час
  перевірка не встигає (таймаут 5 с) і сторінки відкриваються без неї.
- Усі відвідувані URL (крім білого списку) надсилаються на сервер.
