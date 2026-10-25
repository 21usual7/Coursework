import ssl
import socket
from urllib.parse import urlparse
from datetime import datetime
import requests

def check_ssl(url: str) -> dict:
    '''Функція, що перевіряє наявність та валідність SSL-сертифіката та його вік'''

    status = {"has_ssl": False, 
              "ssl_valid": 0, 
              "ssl_age": 0,
              "error": None}

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    parsed_url = urlparse(url)
    if parsed_url.scheme != "https":
        status["error"] = "not https"
        return status

    hostname = (parsed_url.netloc or parsed_url.path.split("/")[0]).split(":")[0]
    if not hostname:
        status["error"] = "invalid hostname"
        return status

    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=1.5) as s:
            with context.wrap_socket(s, server_hostname = hostname) as ss:
                certificate = ss.getpeercert()
                status["has_ssl"] = True
                status["ssl_valid"] = 1

                not_before_str = certificate.get("notBefore")
                if not not_before_str:
                    date = datetime.strptime(not_before_str, "%b %d %H:%M:%S %Y %Z")
                    age_days = (datetime.utcnow() - date).days
                    status["ssl_age"] = max(0, age_days)

                return status
    except Exception as e:
        status["error"] = str(e)
        return status


def check_redirects():
    '''Перевіряє кількість перенаправлень'''

    status = {"redirect_count": 0, "has_nultiple_redirects": 0}

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=1.5,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        count = len(response.history)
        status["redirect_count"] = count

        status["has_nultiple_redirects"] = 1 if count > 3 else 0
    except Exception:
        pass

    return status