import ssl
import socket
import ipaddress
from urllib.parse import urlparse, urljoin
from datetime import datetime
import time
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool, Timeout
from urllib3.util import parse_url


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


def _is_public_ip(address: str) -> bool:
    '''Чи є IP-адреса публічною. IPv6 з вкладеною IPv4 (::127.0.0.1, NAT64 64:ff9b::/96)
    is_global вважає публічними, тому перевіряємо саму вкладену IPv4'''

    ip = ipaddress.ip_address(address.split("%")[0])
    if ip.version == 6 and (int(ip) >> 32 == 0 or ip in ipaddress.ip_network("64:ff9b::/96")):
        ip = ipaddress.ip_address(int(ip) & 0xFFFFFFFF)
    return ip.is_global


def _is_public_host(url: str):
    '''Чи веде URL на публічну адресу. Захист від SSRF: без цього через наш публічний API
    можна змусити сервер звертатися до localhost чи внутрішніх адрес (169.254.169.254 тощо).
    Повертає перевірену IP-адресу або None'''

    # хост беремо тим самим розбором, що й urllib3: urlparse читає "http://127.0.0.1\@bit.ly"
    # як bit.ly, а urllib3 підключається до 127.0.0.1
    try:
        parsed_url = parse_url(url)
    except ValueError:
        return None
    if parsed_url.scheme not in ("http", "https") or not parsed_url.host:
        return None

    # лише стандартні порти: інакше через сервер можна сканувати порти чужих хостів
    if parsed_url.port not in (None, 80, 443):
        return None

    try:
        addresses = socket.getaddrinfo(parsed_url.host.strip("[]"), None)
    except socket.gaierror:
        return None

    if not all(_is_public_ip(a[4][0]) for a in addresses):
        return None
    return addresses[0][4][0]


def check_redirects(url: str) -> dict:
    '''Йде по перенаправленнях і повертає кінцеву адресу.
    Корисна саме кінцева адреса (bit.ly/xxx -> paypal-login.xyz), а не кількість
    перенаправлень: звичайні сайти теж перенаправляють по 3-5 разів'''

    status = {"redirect_count": 0, "final_url": url, "error": None}

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    current = url
    start = time.monotonic()
    try:
        # по кроках, а не allow_redirects=True - щоб перевіряти кожну адресу на SSRF
        for _ in range(MAX_REDIRECTS):
            # розширення чекає відповідь лише 5 с: на весь ланцюжок - не більше 4 с
            left = 4 - (time.monotonic() - start)
            if left <= 0:
                status["error"] = "timeout"
                break

            ip = _is_public_host(current)
            if not ip:
                status["error"] = "not public host"
                break

            # підключаємось саме до перевіреної IP, а не резолвимо домен вдруге:
            # інакше DNS може віддати іншу (внутрішню) адресу (DNS rebinding)
            parsed_url = parse_url(current)
            if parsed_url.scheme == "https":
                pool = HTTPSConnectionPool(ip, parsed_url.port or 443, server_hostname=parsed_url.host,
                                           assert_hostname=parsed_url.host)
            else:
                pool = HTTPConnectionPool(ip, parsed_url.port or 80)
            response = pool.urlopen(
                "GET",
                parsed_url.request_uri,
                headers={"User-Agent": "Mozilla/5.0", "Host": parsed_url.netloc},
                redirect=False,
                retries=False,
                timeout=Timeout(total=min(left, 2)),
                preload_content=False  # тіло сторінки не завантажуємо
            )
            response.release_conn()
            pool.close()

            location = response.headers.get("Location")
            if response.status not in (301, 302, 303, 307, 308) or not location:
                break

            current = urljoin(current, location)
            status["redirect_count"] += 1
    except Exception as e:
        status["error"] = str(e)

    status["final_url"] = current
    return status
