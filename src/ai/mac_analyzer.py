import torch
from collections import defaultdict
from ai.mac_model import MacClassifier
from ai.mac_utils import normalize_mac, extract_mac_features
import os
from typing import Dict, List
import sys

class MacAnalyzer:

    VENDOR_OUI = {
    "Hikvision": ["00:04:8F", "C4:2F:90", "B4:A3:82"],
    "Dahua": ["B8:44:D9", "28:B2:BD", "34:23:BA", "B4:4C:3B", "C0:39:5A", "6C:1C:71"],
    "Axis": ["B8:A4:4F", "AC:CC:8E"],
}
    
    def __init__(self, log_callback=None):
        """
        Инициализация анализатора MAC-адресов
        
        Args:
            log_callback: Функция для вывода логов (принимает message: str)
        """
        self.mac_db = defaultdict(list)
        self.log_callback = log_callback
        self.model = self._load_model()

    def detect_vendor(self, mac: str) -> str:
        """Определяет производителя по MAC-адресу"""
        mac_prefix = mac[:8].upper()  # Первые 6 символов (OUI)
        for vendor, prefixes in self.VENDOR_OUI.items():
            if any(mac_prefix.startswith(oui) for oui in prefixes):
                return vendor
        return "Unknown"
    
    def _load_model(self) -> MacClassifier:
        """Загружает обученную модель PyTorch"""
        try:
            model = MacClassifier()
            
            # Пробуем несколько возможных путей
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "models/mac_model.pth"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "models/mac_model.pth"),
                os.path.join(sys._MEIPASS, "ai/models/mac_model.pth"),  # Для PyInstaller
                os.path.join(sys._MEIPASS, "models/mac_model.pth"),     # Альтернативный путь
                "models/mac_model.pth",  # Относительный путь
            ]
            
            model_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    break
                    
            if not model_path:
                available_files = []
                for root, dirs, files in os.walk(os.path.dirname(__file__)):
                    available_files.extend(files)
                raise FileNotFoundError(
                    f"Файл модели не найден. Проверенные пути: {possible_paths}\n"
                    f"Доступные файлы: {available_files}"
                )
                
            self._log(f"Загружаем модель из: {model_path}")
            model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            model.eval()
            return model
            
        except Exception as e:
            self._log(f"Ошибка загрузки модели: {str(e)}")
            # Возвращаем заглушку или пробрасываем исключение дальше
            raise
    
    def analyze(self, ip: str, mac: str, vendor: str) -> Dict:
        """
        Анализирует MAC-адрес на предмет дублирования
        
        Args:
            ip: IP-адрес устройства
            mac: MAC-адрес устройства
            vendor: Производитель устройства
            
        Returns:
            Словарь с результатами анализа
        """
        try:
            mac = normalize_mac(mac)
            self.mac_db[mac].append(ip)
            
            # Нормализация вендора (используем ключи из VENDOR_OUI)
            vendor = vendor if vendor in self.VENDOR_OUI else "Unknown"
            
            result = {
                'is_duplicate': False,
                'risk_score': 0.0,
                'conflict_ips': []
            }
            
            if len(self.mac_db[mac]) > 1:
                try:
                    features = self.extract_mac_features(mac, vendor, self.mac_db[mac])
                    risk_score = self._predict_risk(features)
                    
                    result.update({
                        'is_duplicate': True,
                        'risk_score': float(risk_score),
                        'conflict_ips': self.mac_db[mac].copy()
                    })
                    
                    self._log(
                        f"Обнаружен дубликат MAC!\n"
                        f"MAC: {mac}\n"
                        f"Vendor: {vendor}\n"
                        f"Конфликты: {', '.join(self.mac_db[mac])}\n"
                        f"Риск: {risk_score:.2f}"
                    )
                except Exception as e:
                    self._log(f"Ошибка анализа дубликата: {str(e)}")
                    result['error'] = str(e)
            
            return result
            
        except Exception as e:
            self._log(f"Ошибка анализа: {str(e)}")
            return {
                'is_duplicate': False,
                'risk_score': 0.0,
                'conflict_ips': [],
                'error': str(e)
            }
    
    def _predict_risk(self, features: List) -> float:
        """Предсказывает риск дубликата (гарантированно возвращает float между 0 и 1)"""
        try:
            if not features:
                return 0.0
                
            tensor = torch.FloatTensor(features).unsqueeze(0)
            prediction = self.model(tensor).item()
            return max(0.0, min(1.0, prediction))  # Ограничение значения 0-1
            
        except Exception as e:
            self._log(f"Ошибка предсказания: {str(e)}")
            return 0.0  # Значение по умолчанию при ошибке
    
    def _log(self, message: str) -> None:
        """Отправляет сообщение в callback"""
        if self.log_callback is None:
            print(f"LOG (no callback): {message}")  # Fallback вывод
            return
            
        try:
            self.log_callback(message)
        except Exception as e:
            print(f"Ошибка в callback: {str(e)}")

    def clear_db(self) -> None:
        """Очищает базу известных MAC-адресов"""
        self.mac_db.clear()
        self._log("База MAC-адресов очищена")


if __name__ == "__main__":
    # Тестовый пример
    def simple_logger(message: str):
        print(f"[LOG] {message}")

    print("Тестирование MacAnalyzer...")
    analyzer = MacAnalyzer(log_callback=simple_logger)
    
    test_data = [
        ("10.1.1.10", "00:1A:2B:11:22:33", "Hikvision"),
        ("10.1.1.11", "00:1A:2B:11:22:33", "Hikvision"),
        ("192.168.1.100", "AA:BB:CC:DD:EE:FF", "Dahua")
    ]
    
    for ip, mac, vendor in test_data:
        result = analyzer.analyze(ip, mac, vendor)
        print(f"Результат для {ip}: {result}")