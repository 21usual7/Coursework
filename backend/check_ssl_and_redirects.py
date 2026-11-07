import ssl
import socket
import ipaddress
from urllib.parse import urlparse, urljoin
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
                if not_before_str:
                    date = datetime.strptime(not_before_str, "%b %d %H:%M:%S %Y %Z")
                    age_days = (datetime.utcnow() - date).days
                    status["ssl_age"] = max(0, age_days)

                return status
    except Exception as e:
        status["error"] = str(e)
        return status


MAX_REDIRECTS = 5


def _is_public_host(url: str) -> bool:
    '''Чи веде URL на публічну адресу. Захист від SSRF: без цього через наш публічний API
    можна змусити сервер звертатися до localhost чи внутрішніх адрес (169.254.169.254 тощо)'''

    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
        return False

    try:
        addresses = socket.getaddrinfo(parsed_url.hostname, None)
    except socket.gaierror:
        return False

    return all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)


def check_redirects(url: str) -> dict:
    '''Йде по перенаправленнях і повертає кінцеву адресу.
    Корисна саме кінцева адреса (bit.ly/xxx -> paypal-login.xyz), а не кількість
    перенаправлень: звичайні сайти теж перенаправляють по 3-5 разів'''

    status = {"redirect_count": 0, "final_url": url, "error": None}

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    current = url
    try:
        # по кроках, а не allow_redirects=True - щоб перевіряти кожну адресу на SSRF
        for _ in range(MAX_REDIRECTS):
            if not _is_public_host(current):
                status["error"] = "not public host"
                break

            response = requests.get(
                current,
                allow_redirects=False,
                timeout=2,
                stream=True,  # тіло сторінки не завантажуємо
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response.close()

            location = response.headers.get("Location")
            if response.status_code not in (301, 302, 303, 307, 308) or not location:
                break

            current = urljoin(current, location)
            status["redirect_count"] += 1
    except Exception as e:
        status["error"] = str(e)

    status["final_url"] = current
    return status
