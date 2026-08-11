import os
import sys
from pathlib import Path
import json
from typing import Optional

class PathManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self.init_paths()
    
    def init_paths(self):
        """Инициализация всех путей"""
        self._determine_base_path()
        self._setup_working_dirs()
    
    def _determine_base_path(self):
        """Определяет базовый путь в зависимости от режима запуска"""
        if getattr(sys, 'frozen', False):
            # Режим EXE
            self.base_path = Path(sys.executable).parent
        else:
            # Режим разработки
            self.base_path = Path(__file__).parent.parent
    
    def _setup_working_dirs(self):
        """Создает все необходимые рабочие директории"""
        # Основные директории
        self.config_dir = self.base_path / "config"
        self.data_dir = self.base_path / "data"
        self.logs_dir = self.data_dir / "logs"
        self.results_dir = self.data_dir / "scan_results"
        
        # Создаем директории если их нет
        self.config_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
    
    def get_config_path(self, filename: str) -> Path:
        """Возвращает путь к файлу конфигурации"""
        return self.config_dir / filename
    
    def get_range_file(self, device_type: str) -> Path:
        """Возвращает путь к файлу диапазонов для типа устройства"""
        return self.get_config_path(f"ranges_{device_type.lower()}.json")
    
    def get_log_path(self, log_name: str) -> Path:
        """Возвращает путь к файлу лога"""
        return self.logs_dir / log_name
    
    def get_result_file(self, filename: str) -> Path:
        """Возвращает путь к файлу результатов"""
        return self.results_dir / filename
    
    def load_json(self, filepath: Path) -> Optional[dict]:
        """Загружает данные из JSON файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def save_json(self, filepath: Path, data: dict) -> bool:
        """Сохраняет данные в JSON файл"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except (IOError, TypeError):
            return False


# Пример использования:
if __name__ == "__main__":
    pm = PathManager()
    print("Base path:", pm.base_path)
    print("Config dir:", pm.config_dir)
    print("Data dir:", pm.data_dir)