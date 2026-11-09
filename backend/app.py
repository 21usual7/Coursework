from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from check_isPhishing import check_url
import os

'''Сервер, що приймає й оброблює запити від server_worker, дістає з них URL-посилання, викликає функцію, що запускає модель та повертає відповідь'''

app = Flask(__name__)
# запит - лише {"url": ...}: велике тіло відхиляємо одразу (413), щоб не вичерпати 512 МБ пам'яті
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

# На Render запити йдуть через проксі: справжня IP-адреса клієнта - у X-Forwarded-For
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# API публічне і без авторизації: обмежуємо кількість запитів з однієї IP,
# щоб ніхто не перевантажив сервер і не вичерпав ліміт Google Safe Browsing (10 000/добу)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({"status": "error", "message": "Too many requests, try again later"}), 429


@app.route("/", methods=["GET"])
def index():
    return "Welcome, to the backend server of GUARDI! Please, authorize!", 200


@app.route("/guardai/api/scan", methods=["POST"])
@limiter.limit("60 per minute;1000 per day")
def api_scan():
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not isinstance(data.get("url"), str) or not 0 < len(data["url"]) <= 2048:
        return jsonify({"status": "error", "message": "Missing or invalid 'url' in request body"}), 400

    url = data["url"]

    try:
        result = check_url(url)

        # Безпечно отримуємо значення незалежно від того, як названо ключ в результаті
        is_phishing = result.get("is_phishing", result.get("is_phisging", False))
        probability = result.get("probability", 0.0)
        threat_type = result.get("threat_type", "unknown")
        reasons = result.get("reasons", [])

        return jsonify({
            "status": "success",
            "url": url,
            "is_phishing": is_phishing,
            "probability": probability,
            "threat_type": threat_type,
            "reasons": reasons
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()  
        # подробиці - лише в лог сервера, не клієнту
        return jsonify({"status": "error", "message": "Internal error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
