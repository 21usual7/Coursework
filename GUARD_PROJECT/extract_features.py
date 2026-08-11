import time
import re
import math
import socket
import requests
import tldextract
from urllib.parse import urlparse
import ssl


def extract_features(url: str) -> list:
    '''Функція яка достає головні ознаки фішонгової URL та стандартизує їх'''
    features = []
    
    assert type(url) is str, "URL is not string type"
    
    #Перевірка на https
    features.append(len(url))
    features.append(1) if "https:" in url else features.append(0)
    features.append(is_ip(url))
    cerificate_val = check_for_certificate(url)
    
    features.append(cerificate_val) if cerificate_val is not None else f"Certificate is None {exit(-1)}"
    
    return features
    
    
def is_ip(url):
    '''Функція яка перевіряє чи є в URL IP адреса'''
    pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    match = re.findall(pattern, url)
    return 1 if match else 0     


def check_for_certificate(url):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    parsed_url = parsed_url(url)
    host = parsed_url.hostname
    port = parsed_url.port or 443
    context = ssl.create_default_context()
    
    try:
        with socket.create_connection((host, port), timeout=5) as s: 
            with context.wrap_socket(s, server_hostname=host) as ssock:
                certificate = ssock.getpeercert()
                
                return 1 

    except ssl.SSLError as e:
        return 0
    
    except Exception as e:
        print(f"Помилка підключення {e}")
        return None
    