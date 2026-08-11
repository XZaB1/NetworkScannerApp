import torch
import torch.nn as nn
import pandas as pd
from datetime import datetime
import re
import os
from openpyxl.utils import get_column_letter  # ← ДОБАВЛЕНО
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side  # ← ДОБАВЛЕНО
from openpyxl.formatting.rule import ColorScaleRule  # ← ДОБАВЛЕНО

class SwitchAnalyzer:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.firmware_min_versions = ["2.10", "2.11", "2.12","2.13", "2.14", "2.15","2.16", "2.17", "2.18","2.19", "2.20", "2.21"]  # Минимальная рекомендуемая версия прошивки
        self.min_uptime_hours = 8           # Минимальное время работы для стабильности
        
        self.model = self._load_model()
        self._log("Инициализирован анализатор коммутаторов TFortis")

    def _load_model(self) -> nn.Module:
        """Загружает модель для анализа стабильности коммутаторов"""
        model = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(8, 4),
            nn.ReLU(),
            nn.Linear(4, 1),
            nn.Sigmoid()
        )
        
        try:
            # Пытаемся загрузить из разных мест
            model_paths = [
                "models/switch_model.pth",
                "src/ai/models/switch_model.pth", 
                "../models/switch_model.pth"
            ]
            
            loaded = False
            for path in model_paths:
                try:
                    if os.path.exists(path):
                        model.load_state_dict(torch.load(path))
                        self._log(f"Модель загружена из {path}")
                        loaded = True
                        break
                except Exception as e:
                    self._log(f"Ошибка загрузки модели из {path}: {str(e)}", level="warning")
                    continue
            
            if not loaded:
                self._log("Модель не найдена, используется начальная модель", level="warning")
                
        except Exception as e:
            self._log(f"Критическая ошибка загрузки модели: {str(e)}", level="error")
        
        return model

    def analyze_switch_data(self, switch_data: dict) -> dict:
        """
        Анализирует данные одного коммутатора с улучшенной диагностикой
        """
        try:
            ip = switch_data.get('IP', 'unknown')
            
            # ДИАГНОСТИКА: выводим все данные коммутатора
            self._log(f"=== АНАЛИЗ КОММУТАТОРА {ip} ===")
            self._log(f"Все данные коммутатора:")
            for key, value in switch_data.items():
                self._log(f"  {key}: '{value}' (тип: {type(value)})")
            
            uptime_str = switch_data.get('Время работы', '')
            firmware = switch_data.get('Прошивка', '')
            model_type = switch_data.get('Тип устройства', 'Коммутатор')
            
            self._log(f"Uptime raw: '{uptime_str}' (тип: {type(uptime_str)})")
            self._log(f"Прошивка: '{firmware}'")
            self._log(f"Тип устройства: '{model_type}'")
            
            # Анализ времени работы
            uptime_hours = self._parse_uptime_to_hours(uptime_str)
            self._log(f"Uptime в часах: {uptime_hours} (тип: {type(uptime_hours)})")
            
            # Анализ прошивки
            firmware_risk, firmware_status = self._analyze_firmware(firmware)
            self._log(f"Статус прошивки: '{firmware_status}', риск: {firmware_risk}")
            
            # Предсказание риска с помощью модели
            self._log(f"Вызов _predict_risk с uptime_hours={uptime_hours}, firmware_status='{firmware_status}'")
            model_risk = self._predict_risk(uptime_hours, firmware_status)
            self._log(f"Результат предсказания модели: {model_risk}")
            
            # Комбинированная оценка риска
            total_risk = (model_risk * 0.7) + (firmware_risk * 0.3)
            self._log(f"Общий риск: {total_risk}")
            
            # Формирование рекомендаций
            self._log(f"Вызов _generate_recommendations с uptime_hours={uptime_hours}, firmware_status='{firmware_status}', risk_score={total_risk}")
            recommendations = self._generate_recommendations(uptime_hours, firmware_status, total_risk)
            self._log(f"Сгенерировано рекомендаций: {len(recommendations)}")
            
            result = {
                'IP Address': ip,
                'Model': model_type,
                'Uptime': uptime_str,
                'Uptime Hours': uptime_hours,
                'Firmware Version': firmware,
                'Firmware Status': firmware_status,
                'Risk Score': total_risk,
                'Recommendations': '; '.join(recommendations),
                'Analysis Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self._log(f"Анализ завершен для {ip}")
            self._log(f"Результат: {result}")
            return result
            
        except Exception as e:
            error_msg = f"КРИТИЧЕСКАЯ ОШИБКА анализа коммутатора {switch_data.get('IP', 'unknown')}: {str(e)}"
            self._log(error_msg, level="error")
            
            # Логируем полный traceback для диагностики
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}", level="error")
            
            # Логируем данные, которые вызвали ошибку
            self._log(f"Данные вызвавшие ошибку: {switch_data}", level="error")
            
            return {
                'IP Address': switch_data.get('IP', 'unknown'),
                'Error': str(e),
                'Risk Score': 0.5,
                'Recommendations': 'Критическая ошибка анализа',
                'Analysis Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def analyze_switches(self, switches_data: list) -> list:
        """
        Анализирует список коммутаторов
        """
        results = []
        
        for switch in switches_data:
            if switch.get('Тип устройства') == 'Коммутатор':
                try:
                    # ВРЕМЕННО: добавляем максимальную диагностику
                    self._log(f"=== ОБРАБОТКА КОММУТАТОРА {switch.get('IP')} ===")
                    self._log(f"Все данные: {switch}")
                    
                    # Анализируем данные
                    analysis = self.analyze_switch_data(switch)
                    results.append(analysis)
                    
                except Exception as e:
                    self._log(f"КРИТИЧЕСКАЯ ОШИБКА при анализе {switch.get('IP')}: {str(e)}", level="error")
                    import traceback
                    self._log(f"Полный traceback: {traceback.format_exc()}", level="error")
                    
                    # Сохраняем ошибку в результат
                    results.append({
                        'IP Address': switch.get('IP', 'unknown'),
                        'Error': str(e),
                        'Risk Score': 0.5,
                        'Recommendations': 'Критическая ошибка анализа'
                    })
        
        return results
    

    def _validate_switch_data(self, switch_data: dict) -> bool:
        """Проверяет корректность данных коммутатора перед анализом"""
        try:
            required_fields = ['IP', 'Время работы', 'Прошивка', 'Тип устройства']
            
            for field in required_fields:
                if field not in switch_data:
                    self._log(f"Отсутствует обязательное поле: {field}", level="warning")
                    return False
            
            # Проверяем типы данных
            uptime = switch_data.get('Время работы', '')
            if not isinstance(uptime, (str, int, float)):
                self._log(f"Некорректный тип времени работы: {type(uptime)}", level="warning")
                return False
                
            firmware = switch_data.get('Прошивка', '')
            if not isinstance(firmware, (str, type(None))):
                self._log(f"Некорректный тип прошивки: {type(firmware)}", level="warning")
                return False
                
            return True
            
        except Exception as e:
            self._log(f"Ошибка валидации данных: {e}", level="error")
            return False

    def _safe_compare(self, value1, value2, comparison_type='gt'):
        """Безопасное сравнение с преобразованием типов"""
        try:
            # Преобразуем оба значения к float
            val1 = float(value1) if value1 is not None else 0.0
            val2 = float(value2) if value2 is not None else 0.0
            
            if comparison_type == 'gt':
                return val1 > val2
            elif comparison_type == 'lt':
                return val1 < val2
            elif comparison_type == 'ge':
                return val1 >= val2
            elif comparison_type == 'le':
                return val1 <= val2
            elif comparison_type == 'eq':
                return val1 == val2
            else:
                return False
                
        except (ValueError, TypeError) as e:
            self._log(f"Ошибка сравнения {value1} и {value2}: {e}", level="error")
            return False


    def _parse_uptime_to_hours(self, uptime_str) -> float:
        """Конвертирует uptime в часы, обрабатывая разные форматы"""
        if not uptime_str:
            return 0.0
            
        try:
            # ИСПРАВЛЕНО: улучшена проверка на числа в строке
            if isinstance(uptime_str, (int, float)):
                uptime_value = float(uptime_str)
            elif isinstance(uptime_str, str) and uptime_str.strip().replace('.', '').isdigit():
                uptime_value = float(uptime_str)
            else:
                uptime_value = None
                
            if uptime_value is not None:
                # Определяем единицы измерения
                if uptime_value > 31536000000:  # миллисекунды -> часы
                    uptime_hours = uptime_value / 3600000.0
                    self._log(f"Предполагаем миллисекунды: {uptime_value} -> {uptime_hours:.2f} часов")
                elif uptime_value > 31536000:  # секунды -> часы
                    uptime_hours = uptime_value / 3600.0
                    self._log(f"Предполагаем секунды: {uptime_value} -> {uptime_hours:.2f} часов")
                else:
                    uptime_hours = uptime_value  # уже часы
                    self._log(f"Предполагаем часы: {uptime_value} часов")
                    
                return round(float(uptime_hours), 2)
                
            # Обработка строкового формата
            elif isinstance(uptime_str, str):
                hours_match = re.search(r'(\d+)\s*час', uptime_str)
                minutes_match = re.search(r'(\d+)\s*минут', uptime_str)
                seconds_match = re.search(r'(\d+)\s*секунд', uptime_str)
                
                if hours_match or minutes_match or seconds_match:
                    hours = int(hours_match.group(1)) if hours_match else 0
                    minutes = int(minutes_match.group(1)) if minutes_match else 0
                    seconds = int(seconds_match.group(1)) if seconds_match else 0
                    
                    total_hours = hours + (minutes / 60.0) + (seconds / 3600.0)
                    self._log(f"Строковый формат: {uptime_str} -> {total_hours:.2f} часов")
                    return round(total_hours, 2)
                else:
                    # Пытаемся извлечь число
                    numbers = re.findall(r'\d+', uptime_str)
                    if numbers:
                        uptime_value = float(numbers[0])
                        uptime_hours = uptime_value / 3600.0  # предполагаем секунды
                        self._log(f"Число из строки: {uptime_str} -> {uptime_hours:.2f} часов")
                        return round(uptime_hours, 2)
                    else:
                        self._log(f"Неизвестный формат uptime: '{uptime_str}'", level="warning")
                        return 0.0
            else:
                self._log(f"Неизвестный тип uptime: {type(uptime_str)}", level="warning")
                return 0.0
                
        except Exception as e:
            self._log(f"Ошибка парсинга uptime '{uptime_str}': {str(e)}", level="warning")
            return 0.0

    def _analyze_firmware(self, firmware_version: str) -> tuple:
        """Анализирует версию прошивки с правильным распознаванием 00.02.xx"""
        if not firmware_version:
            return 0.9, "unknown"
        
        try:
            self._log(f"Анализ прошивки: '{firmware_version}'")
            
            # Улучшенный парсинг для формата 00.02.11
            version_match = re.search(r'(\d{2})\.(\d{2})\.(\d{2})', firmware_version)
            if version_match:
                first = int(version_match.group(1))
                second = int(version_match.group(2))
                third = int(version_match.group(3))
                
                # Для формата 00.02.11 считаем как версию 2.11
                if first == 0 and second == 2:
                    effective_version = f"2.{third}"
                    self._log(f"Преобразованная версия: {effective_version}")
                    
                    # Сравниваем с минимальной версией 2.10
                    if third >= 10:  # 2.11 >= 2.10
                        return 0.1, "current"
                    else:
                        return 0.7, "outdated"
            
            # Стандартный парсинг для других форматов
            version_match = re.search(r'(\d+\.\d+)', firmware_version)
            if not version_match:
                return 0.5, "invalid"
                
            version = version_match.group(1)
            version_parts = version.split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
            
            min_parts = self.firmware_min_version.split('.')
            min_major = int(min_parts[0])
            min_minor = int(min_parts[1])
            
            if major > min_major or (major == min_major and minor >= min_minor):
                return 0.1, "current"
            else:
                return 0.7, "outdated"
                
        except (ValueError, IndexError) as e:
            self._log(f"Ошибка анализа прошивки '{firmware_version}': {str(e)}", level="warning")
            return 0.5, "invalid"

    def _compare_versions(self, v1, v2):
        """Сравнение версий типа X.Y"""
        try:
            v1_parts = list(map(int, v1.split('.')))
            v2_parts = list(map(int, v2.split('.')))
            
            # Дополняем до одинаковой длины
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            return 0
        except Exception as e:
            self._log(f"Ошибка сравнения версий {v1} и {v2}: {e}", level="warning")
            return -1     

    def _predict_risk(self, uptime_hours, firmware_status: str) -> float:
        """Предсказывает риск с помощью модели с полной диагностикой"""
        self.debug_predict_risk(uptime_hours, firmware_status)
        try:
            # ДЕТАЛЬНАЯ ДИАГНОСТИКА ВХОДНЫХ ДАННЫХ
            self._log(f"=== ДИАГНОСТИКА _predict_risk ===")
            self._log(f"uptime_hours: {uptime_hours} (тип: {type(uptime_hours)})")
            self._log(f"firmware_status: '{firmware_status}' (тип: {type(firmware_status)})")
            
            # Гарантируем числовые типы
            original_uptime = uptime_hours
            if not isinstance(uptime_hours, (int, float)):
                self._log(f"Преобразуем uptime_hours из {type(uptime_hours)} в float")
                try:
                    uptime_hours = float(uptime_hours) if uptime_hours is not None else 0.0
                    self._log(f"Преобразовано: {original_uptime} -> {uptime_hours}")
                except (ValueError, TypeError) as e:
                    self._log(f"Ошибка преобразования uptime_hours: {e}", level="warning")
                    uptime_hours = 0.0
            
            # Преобразуем firmware_status в числовой формат
            status_mapping = {"outdated": 0, "current": 1, "unknown": 2, "invalid": 2}
            firmware_numeric = status_mapping.get(firmware_status, 2)
            self._log(f"firmware_numeric: {firmware_numeric} (тип: {type(firmware_numeric)})")
            
            # Детальная диагностика перед созданием тензора
            self._log(f"Создаем тензор с данными:")
            self._log(f"  uptime_hours: {uptime_hours} (float: {float(uptime_hours)})")
            self._log(f"  firmware_numeric: {firmware_numeric} (float: {float(firmware_numeric)})")
            
            # Явное преобразование всех значений в float
            features = torch.FloatTensor([
                [float(uptime_hours), float(firmware_numeric), 0.0, 0.0]
            ])
            
            self._log(f"Тензор создан: {features}")
            
            with torch.no_grad():
                risk = self.model(features).item()
                self._log(f"Модель вернула риск: {risk}")
                
            return float(risk)
        
            
        except Exception as e:
            self._log(f"Ошибка предсказания: {str(e)}", level="error")
            # Добавляем информацию о типах данных для отладки
            self._log(f"Типы данных при ошибке: uptime_hours={type(uptime_hours)}, firmware_status={type(firmware_status)}")
            
            # Логируем traceback для точного определения места ошибки
            import traceback
            tb = traceback.format_exc()
            self._log(f"Traceback: {tb}", level="error")
            
            return self._calculate_heuristic_risk(uptime_hours, firmware_status)
        
        
    def debug_predict_risk(self, uptime_hours, firmware_status: str):
        """Временный метод для отладки проблемы сравнения"""
        self._log("=== ПРИНУДИТЕЛЬНАЯ ДИАГНОСТИКА СРАВНЕНИЯ ===")
        
        # Проверяем ВСЕ возможные сравнения в коде
        comparisons_to_test = [
            ("uptime_hours > 0", uptime_hours > 0 if isinstance(uptime_hours, (int, float)) else "ERROR"),
            ("uptime_hours < min_uptime", uptime_hours < self.min_uptime_hours if isinstance(uptime_hours, (int, float)) else "ERROR"),
            ("uptime_hours < 24", uptime_hours < 24 if isinstance(uptime_hours, (int, float)) else "ERROR"),
            ("uptime_hours < 168", uptime_hours < 168 if isinstance(uptime_hours, (int, float)) else "ERROR"),
        ]
        
        for test_name, result in comparisons_to_test:
            self._log(f"Тест {test_name}: {result}")
        
        # Проверяем, что приходит в эвристическую функцию
        heuristic_risk = self._calculate_heuristic_risk(uptime_hours, firmware_status)
        self._log(f"Эвристическая оценка риска: {heuristic_risk}")

    def predict_single(self, switch_data):
        """Анализ одного коммутатора в реальном времени"""
        try:
            # Подготовка данных для модели
            X = self._prepare_features([switch_data])
            
            # Предсказание
            with torch.no_grad():
                prediction = self.model(X)
                risk_score = prediction.item()
            
            # Генерация рекомендаций
            recommendations = self._generate_recommendations_advanced(risk_score, switch_data)
            
            return {
                'risk_score': risk_score,
                'recommendations': recommendations
            }
            
        except Exception as e:
            self._log(f"Ошибка предсказания: {str(e)}", level="error")
            return {
                'risk_score': 0.5,
                'recommendations': ["Ошибка анализа"]
            }

    def _prepare_features(self, switches_data):
        """Подготовка признаков для модели"""
        features = []
        for data in switches_data:
            # Извлекаем и нормализуем признаки
            uptime_hours = data.get('Uptime Hours', 0)
            firmware_status = data.get('Firmware Status', 2)
            error_count = data.get('Error Count', 0)
            occupied_ports = data.get('Occupied Ports', 0)
            total_ports = data.get('Total Ports', 0)
            
            # Нормализация (можно добавить более сложную логику)
            port_occupancy = occupied_ports / max(total_ports, 1)  # избегаем деления на 0
            
            features.append([uptime_hours, firmware_status, error_count, port_occupancy])
        
        return torch.FloatTensor(features)

    def _generate_recommendations_advanced(self, risk_score, switch_data):
        """Генерация рекомендаций на основе оценки риска с безопасными сравнениями"""
        recommendations = []
        
        # Безопасное сравнение для risk_score
        try:
            risk_score = float(risk_score) if risk_score is not None else 0.0
        except (ValueError, TypeError):
            risk_score = 0.0
        
        # Рекомендации на основе уровня риска (безопасное сравнение)
        if risk_score > 0.7:
            recommendations.append("Высокий риск! Требуется немедленная проверка")
        elif risk_score > 0.4:
            recommendations.append("Средний риск. Рекомендуется плановая проверка")
        else:
            recommendations.append("Низкий риск. Стабильная работа")
        
        # Рекомендации на основе времени работы
        uptime_hours = switch_data.get('Uptime Hours', 0)
        
        # Гарантируем, что uptime_hours - число
        try:
            if not isinstance(uptime_hours, (int, float)):
                uptime_hours = float(uptime_hours)
        except (ValueError, TypeError):
            uptime_hours = 0
        
        # Преобразуем в дни для удобства
        uptime_days = uptime_hours / 24.0
        
        # Безопасные сравнения для времени работы
        if self._safe_compare(uptime_hours, 0, 'eq'):
            recommendations.append("Коммутатор не работает - проверьте питание и подключение")
        elif self._safe_compare(uptime_hours, self.min_uptime_hours, 'lt'):
            recommendations.append("Нестабильная работа - возможны постоянные перезагрузки")
        elif self._safe_compare(uptime_days, 365, 'gt'):
            recommendations.append(f"Время работы более {uptime_days:.0f} дней - рекомендуется плановая перезагрузка")
        elif self._safe_compare(uptime_days, 180, 'gt'):
            recommendations.append(f"Время работы {uptime_days:.0f} дней - рекомендуется проверить логи и производительность")
        elif self._safe_compare(uptime_days, 90, 'gt'):
            recommendations.append(f"Время работы {uptime_days:.0f} дней - стабильная работа")
        
        # Рекомендации на основе прошивки
        firmware_status = switch_data.get('Firmware Status', 'unknown')
        
        # Обрабатываем разные форматы статуса прошивки
        if isinstance(firmware_status, int):
            # Числовой формат
            if firmware_status == 0:
                recommendations.append("Обновите прошивку до актуальной версии")
            elif firmware_status == 2:
                recommendations.append("Статус прошивки неизвестен, требуется проверка")
        elif isinstance(firmware_status, str):
            # Строковый формат
            if firmware_status == "outdated":
                recommendations.append("Обновите прошивку до актуальной версии")
            elif firmware_status == "unknown":
                recommendations.append("Статус прошивки неизвестен, требуется проверка")
            elif firmware_status == "invalid":
                recommendations.append("Некорректная версия прошивки, требуется проверка")
        
        # Рекомендации на основе ошибок
        error_count = switch_data.get('Error Count', 0)
        
        # Гарантируем, что error_count - число
        try:
            if not isinstance(error_count, (int, float)):
                error_count = int(error_count)
        except (ValueError, TypeError):
            error_count = 0
        
        # Безопасные сравнения для ошибок
        if self._safe_compare(error_count, 10, 'gt'):
            recommendations.append(f"Критический уровень ошибок ({error_count}) - требуется немедленная диагностика")
        elif self._safe_compare(error_count, 5, 'gt'):
            recommendations.append(f"Обнаружено {error_count} ошибок - требуется диагностика")
        elif self._safe_compare(error_count, 0, 'gt'):
            recommendations.append(f"Обнаружено {error_count} ошибок - рекомендуется мониторинг")
        
        # Рекомендации на основе загрузки портов
        occupied_ports = switch_data.get('Occupied Ports', 0)
        total_ports = switch_data.get('Total Ports', 1)
        
        # Гарантируем числовые значения
        try:
            if not isinstance(occupied_ports, (int, float)):
                occupied_ports = int(occupied_ports)
            if not isinstance(total_ports, (int, float)):
                total_ports = int(total_ports)
        except (ValueError, TypeError):
            occupied_ports = 0
            total_ports = 1
        
        # Избегаем деления на ноль
        if total_ports <= 0:
            total_ports = 1
        
        port_occupancy = occupied_ports / total_ports
        
        # Безопасные сравнения для загрузки портов
        if self._safe_compare(port_occupancy, 0.9, 'gt'):
            recommendations.append(f"Высокая загрузка портов ({occupied_ports}/{total_ports}) -考慮 расширение")
        elif self._safe_compare(port_occupancy, 0.7, 'gt'):
            recommendations.append(f"Высокая загрузка портов ({occupied_ports}/{total_ports}) - мониторинг производительности")
        elif self._safe_compare(port_occupancy, 0.1, 'lt'):
            recommendations.append(f"Низкая загрузка портов ({occupied_ports}/{total_ports}) - возможна избыточность")
        elif self._safe_compare(port_occupancy, 0.3, 'lt'):
            recommendations.append(f"Низкая загрузка портов ({occupied_ports}/{total_ports}) - оптимальная работа")
        
        # Дополнительные рекомендации на основе других параметров
        cpu_usage = switch_data.get('CPU Usage', 0)
        memory_usage = switch_data.get('Memory Usage', 0)
        
        # Безопасные сравнения для CPU и памяти
        if self._safe_compare(cpu_usage, 80, 'gt'):
            recommendations.append(f"Высокая загрузка CPU ({cpu_usage}%) - требуется оптимизация")
        if self._safe_compare(memory_usage, 85, 'gt'):
            recommendations.append(f"Высокая загрузка памяти ({memory_usage}%) - требуется мониторинг")
        
        # Если рекомендаций нет, добавляем общую
        if not recommendations:
            recommendations.append("Система стабильна, рекомендаций не требуется")
        
        return recommendations

    def _extract_uptime_hours(self, uptime_str):
        """Извлекает количество часов из времени работы, обрабатывая разные форматы"""
        if not uptime_str:
            return 0
        
        try:
            # Если это число (вероятно секунды или миллисекунды)
            if isinstance(uptime_str, (int, float)) or (isinstance(uptime_str, str) and uptime_str.strip().isdigit()):
                uptime_value = float(uptime_str)
                
                # Определяем единицы измерения по величине значения
                if uptime_value > 31536000000:  # Если больше года в миллисекундах
                    # Скорее всего это миллисекунды
                    uptime_hours = uptime_value / 3600000.0
                    self._log(f"Предполагаем миллисекунды: {uptime_value} -> {uptime_hours:.2f} часов")
                elif uptime_value > 31536000:  # Если больше года в секундах
                    # Возможно это сотые доли секунды или другой формат
                    uptime_hours = uptime_value / 3600.0
                    self._log(f"Предполагаем секунды (большое значение): {uptime_value} -> {uptime_hours:.2f} часов")
                else:
                    # Скорее всего секунды
                    uptime_hours = uptime_value / 3600.0
                    self._log(f"Предполагаем секунды: {uptime_value} -> {uptime_hours:.2f} часов")
                    
                return int(uptime_hours)  # Возвращаем целое число часов
            
            # Если это строка с форматом времени
            elif isinstance(uptime_str, str):
                # Проверяем разные паттерны
                hours_match = re.search(r'(\d+)\s*час', uptime_str)
                minutes_match = re.search(r'(\d+)\s*минут', uptime_str)
                seconds_match = re.search(r'(\d+)\s*секунд', uptime_str)
                
                days_match = re.search(r'(\d+)\s*дн', uptime_str)  # дни
                weeks_match = re.search(r'(\d+)\s*нед', uptime_str)  # недели
                
                if hours_match or minutes_match or seconds_match or days_match or weeks_match:
                    # Извлекаем все компоненты времени
                    days = int(days_match.group(1)) if days_match else 0
                    weeks = int(weeks_match.group(1)) if weeks_match else 0
                    hours = int(hours_match.group(1)) if hours_match else 0
                    minutes = int(minutes_match.group(1)) if minutes_match else 0
                    seconds = int(seconds_match.group(1)) if seconds_match else 0
                    
                    total_hours = (weeks * 7 * 24) + (days * 24) + hours + (minutes / 60.0) + (seconds / 3600.0)
                    self._log(f"Строковый формат: {uptime_str} -> {total_hours:.2f} часов")
                    return int(total_hours)
                
                else:
                    # Пытаемся извлечь число из строки
                    numbers = re.findall(r'\d+', uptime_str)
                    if numbers:
                        # Берем первое найденное число
                        uptime_value = float(numbers[0])
                        # Предполагаем часы (так как метод называется _extract_uptime_hours)
                        self._log(f"Число в строке: {uptime_str} -> {uptime_value} часов")
                        return int(uptime_value)
                    else:
                        self._log(f"Неизвестный строковый формат uptime: '{uptime_str}'", level="warning")
                        return 0
            else:
                self._log(f"Неизвестный тип uptime: {type(uptime_str)}", level="warning")
                return 0
                
        except Exception as e:
            self._log(f"Ошибка извлечения часов из uptime '{uptime_str}': {str(e)}", level="warning")
            return 0

    def _get_firmware_status(self, firmware_str):
        """Определяет статус прошивки"""
        if not firmware_str:
            return 2  # Неизвестно
            
        firmware_lower = firmware_str.lower()
        if 'старая' in firmware_lower or 'old' in firmware_lower:
            return 0  # Устаревшая
        elif 'актуаль' in firmware_lower or 'current' in firmware_lower:
            return 1  # Актуальная
        else:
            return 2  # Неизвестно

    def _count_errors(self, switch_data):
        """Подсчет ошибок в данных коммутатора"""
        error_count = 0
        for key in switch_data:
            if key.startswith('Порт ') and switch_data[key] and 'error' in str(switch_data[key]).lower():
                error_count += 1
        return error_count

    def _calculate_heuristic_risk(self, uptime_hours, firmware_status: str) -> float:
        """Эвристическая оценка риска с диагностикой"""
        self._log("=== ДИАГНОСТИКА _calculate_heuristic_risk ===")
        self._log(f"Вход: uptime_hours={uptime_hours} (тип: {type(uptime_hours)}), firmware_status='{firmware_status}'")
        
        try:
            # Гарантируем, что uptime_hours - число
            original_value = uptime_hours
            if not isinstance(uptime_hours, (int, float)):
                uptime_hours = float(uptime_hours) if uptime_hours is not None else 0.0
                self._log(f"Преобразовано uptime_hours: {original_value} -> {uptime_hours}")
        except (ValueError, TypeError) as e:
            self._log(f"Ошибка преобразования uptime_hours: {e}", level="warning")
            uptime_hours = 0.0
        
        base_risk = 0.0
        
        # Диагностика каждого сравнения
        comparisons = [
            ("uptime_hours == 0.0", uptime_hours == 0.0, 0.9),
            ("uptime_hours < min_uptime", uptime_hours < float(self.min_uptime_hours), 0.7),
            ("uptime_hours < 24.0", uptime_hours < 24.0, 0.3),
            ("uptime_hours < 168.0", uptime_hours < 168.0, 0.1),
        ]
        
        for condition, result, risk_value in comparisons:
            self._log(f"Проверка {condition}: {result}")
            if result:
                base_risk += risk_value
                self._log(f"Добавлен риск {risk_value}, общий: {base_risk}")
        
        # Риск по прошивке
        firmware_risks = {
            "outdated": 0.6,
            "unknown": 0.4, 
            "invalid": 0.3
        }
        
        if firmware_status in firmware_risks:
            base_risk += firmware_risks[firmware_status]
            self._log(f"Добавлен риск прошивки {firmware_status}: {firmware_risks[firmware_status]}")
        
        final_risk = min(1.0, base_risk)
        self._log(f"Финальный риск: {final_risk}")
        
        return final_risk

    def _generate_recommendations(self, uptime_hours, firmware_status: str, risk_score: float) -> list:
        """Генерирует рекомендации на основе анализа с защитой от типов"""
        try:
            # Гарантируем, что uptime_hours - число
            if not isinstance(uptime_hours, (int, float)):
                uptime_hours = float(uptime_hours) if uptime_hours else 0.0
        except (ValueError, TypeError):
            uptime_hours = 0.0
        
        recommendations = []
        
        # Рекомендации по времени работы (используем безопасное сравнение)
        if self._safe_compare(uptime_hours, 0.0, 'eq'):
            recommendations.append("Коммутатор не работает - необходимо физически проверить питание и подключение")
        elif self._safe_compare(uptime_hours, float(self.min_uptime_hours), 'lt'):
            recommendations.append("Необходимо физически проверить коммутатор, так как происходит постоянная перезагрузка")
        elif self._safe_compare(uptime_hours, 24.0, 'lt'):
            recommendations.append("Коммутатор недавно перезагружался - рекомендуется проверить логи")
        
        # Рекомендации по прошивке (строковое сравнение - безопасно)
        if firmware_status == "outdated":
            recommendations.append("Необходимо обновить прошивку до версии 2.10 или выше")
        elif firmware_status == "unknown":
            recommendations.append("Не удалось определить версию прошивки - рекомендуется проверить вручную")
        elif firmware_status == "invalid":
            recommendations.append("Обнаружена некорректная версия прошивки - требуется проверка")
        
        # Общие рекомендации по уровню риска (безопасное сравнение)
        if self._safe_compare(risk_score, 0.7, 'gt'):
            recommendations.append("ВЫСОКИЙ РИСК! Требуется немедленное вмешательство")
        elif self._safe_compare(risk_score, 0.4, 'gt'):
            recommendations.append("Средний уровень риска - рекомендуется плановое обслуживание")
        
        if not recommendations:
            recommendations.append("Система стабильна, рекомендаций не требуется")
        
        return recommendations

    def save_ai_analysis_to_excel(self, analysis_results: list, filename: str):
        """Сохраняет результаты AI анализа в Excel файл с авто-форматированием"""
        try:
            df = pd.DataFrame(analysis_results)
            
            # Упорядочиваем колонки
            columns_order = [
                'IP Address', 'Model', 'Uptime', 'Uptime Hours', 
                'Firmware Version', 'Firmware Status', 'Risk Score', 
                'Recommendations', 'Analysis Timestamp'
            ]
            
            existing_columns = [col for col in columns_order if col in df.columns]
            df = df[existing_columns]
            
            # ════════════════════════════════════════════════════════════════════
            # СНАЧАЛА форматируем значения, ПОТОМ переименовываем колонки
            # ════════════════════════════════════════════════════════════════════
            
            # Форматирование значений (на английских названиях)
            if 'Risk Score' in df.columns:
                df['Risk Score'] = df['Risk Score'].apply(
                    lambda x: f"{float(x)*100:.1f}%".replace('.', ',')
                )
            
            if 'Uptime Hours' in df.columns:
                df['Uptime Hours'] = df['Uptime Hours'].apply(
                    lambda x: f"{float(x):.2f}".replace('.', ',') if x else "0,00"
                )
            
            # ════════════════════════════════════════════════════════════════════
            # ПОТОМ переименовываем колонки на русский
            # ════════════════════════════════════════════════════════════════════
            column_names_mapping = {
                'IP Address': 'IP адрес',
                'Model': 'Модель',
                'Uptime': 'Время работы',
                'Uptime Hours': 'Время работы (часы)',
                'Firmware Version': 'Версия прошивки',
                'Firmware Status': 'Статус прошивки',
                'Risk Score': 'Уровень риска',
                'Recommendations': 'Рекомендации',
                'Analysis Timestamp': 'Время анализа'
            }
            
            # Переименовываем только те колонки, которые есть в DataFrame
            df = df.rename(columns={col: column_names_mapping[col] 
                                for col in df.columns 
                                if col in column_names_mapping})
            
            # Создаем Excel файл с авто-форматированием
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Анализ рисков')
                
                workbook = writer.book
                worksheet = writer.sheets['Анализ рисков']
                
                # Авто-подбор ширины колонок
                self._auto_adjust_columns(worksheet, df)
                
                # Добавляем форматирование
                self._apply_excel_formatting(worksheet, df)
                
                # Добавляем фильтры
                worksheet.auto_filter.ref = worksheet.dimensions
                
            self._log(f"Результаты AI анализа сохранены в {filename} с авто-форматированием")
            
        except Exception as e:
            self._log(f"Ошибка сохранения AI анализа в Excel: {str(e)}", level="error")
            raise

    def _auto_adjust_columns(self, worksheet, df):
        """Автоматически подбирает ширину колонок"""
        try:
            from openpyxl.utils import get_column_letter
            
            for idx, column in enumerate(df.columns, 1):
                column_letter = get_column_letter(idx)
                
                # Определяем максимальную длину в колонке
                max_length = 0
                column_name = str(column)
                
                # Учитываем заголовок
                max_length = max(max_length, len(column_name))
                
                # Учитываем данные в ячейках
                for cell in worksheet[column_letter]:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        max_length = max(max_length, cell_length)
                
                # Добавляем небольшой запас
                adjusted_width = min(max_length + 2, 50)  # Максимальная ширина 50
                
                worksheet.column_dimensions[column_letter].width = adjusted_width
                
        except Exception as e:
            self._log(f"Ошибка авто-подбора колонок: {e}", level="warning")

    def _apply_excel_formatting(self, worksheet, df):
        """Применяет дополнительное форматирование к таблице"""
        try:
            # Стили
            header_font = Font(bold=True, color="FFFFFF", size=12)
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            centered = Alignment(horizontal="center", vertical="center")
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Форматируем заголовки
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = centered
                cell.border = border
            
            # Форматируем данные
            for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
                for cell in row:
                    cell.border = border
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
            
            # Особое форматирование для колонки Уровень риска (бывший Risk Score)
            for idx, column in enumerate(df.columns, 1):
                if column == 'Уровень риска':  # ← ИЗМЕНИЛ НА РУССКОЕ НАЗВАНИЕ
                    column_letter = get_column_letter(idx)
                    for row in range(2, worksheet.max_row + 1):
                        cell = worksheet[f"{column_letter}{row}"]
                        cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Замораживаем заголовки
            worksheet.freeze_panes = "A2"
            
        except Exception as e:
            self._log(f"Ошибка применения форматирования: {e}", level="warning")


    def debug_analyze_switch_data(self, switch_data: dict) -> dict:
        """Версия для отладки с подробным логированием"""
        try:
            ip = switch_data.get('IP', 'unknown')
            self._log(f"=== ДЕБАГ Анализ коммутатора {ip} ===")
            
            uptime_str = switch_data.get('Время работы', '')
            self._log(f"Uptime строка: '{uptime_str}' (тип: {type(uptime_str)})")
            
            uptime_hours = self._parse_uptime_to_hours(uptime_str)
            self._log(f"Uptime часов: {uptime_hours} (тип: {type(uptime_hours)})")
            
            firmware = switch_data.get('Прошивка', '')
            self._log(f"Прошивка: '{firmware}'")
            
            firmware_risk, firmware_status = self._analyze_firmware(firmware)
            self._log(f"Статус прошивки: {firmware_status}, риск: {firmware_risk}")
            
            # Возвращаем результат для отладки
            return {
                'IP Address': ip,
                'Uptime': uptime_str,
                'Uptime Hours': uptime_hours,
                'Firmware Version': firmware,
                'Firmware Status': firmware_status,
                'Firmware Risk': firmware_risk
            }
            
        except Exception as e:
            self._log(f"Ошибка отладки: {str(e)}", level="error")
            return {'Error': str(e)}

    def _log(self, message: str, level: str = "info"):
        """Логирование"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] [SwitchAI] {message}"
            
            if self.log_callback and callable(self.log_callback):
                self.log_callback(formatted_message, level)
            else:
                print(formatted_message)
        except Exception as e:
            print(f"[SwitchAI] Ошибка логирования: {e}")
            
# Пример использования
if __name__ == "__main__":
    # Тестовые данные с разными форматами uptime
    test_data = [
        {
            'IP': '192.168.1.10',
            'Тип устройства': 'Коммутатор',
            'Время работы': '1486865',  # число (секунды)
            'Прошивка': '2.7'
        },
        {
            'IP': '192.168.1.11',
            'Тип устройства': 'Коммутатор',
            'Время работы': '2 часов 15 минут 30 секунд',
            'Прошивка': '2.12'
        }
    ]
    
    analyzer = SwitchAnalyzer()
    results = analyzer.analyze_switches(test_data)
    
    for result in results:
        print(f"IP: {result['IP Address']}")
        print(f"Risk: {result['Risk Score']:.3f}")
        print(f"Uptime Hours: {result['Uptime Hours']}")
        print(f"Recommendations: {result['Recommendations']}")
        print()