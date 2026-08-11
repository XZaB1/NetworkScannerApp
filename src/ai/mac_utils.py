import re

def normalize_mac(mac: str) -> str:
    """Приводит MAC-адрес к стандартному формату (AA:BB:CC:DD:EE:FF)"""
    mac = mac.upper().replace("-", ":").strip()
    if not re.match(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$", mac):
        raise ValueError(f"Invalid MAC address format: {mac}")
    return mac

def extract_mac_features(mac: str, vendor: str, ip_list: list) -> list:
    """Извлекает признаки для нейросети"""
    first_byte = int(mac.split(':')[0], 16)
    subnets = len({ip.split('.')[2] for ip in ip_list})
    vendor_code = 1 if vendor.lower() == "hikvision" else 0
    return [first_byte, subnets, vendor_code]