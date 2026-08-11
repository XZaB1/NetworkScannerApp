import torch
import torch.nn as nn
from switch_analyzer import SwitchAnalyzer

def test_model():
    """Тестирование обученной модели"""
    print("Тестирование модели анализа коммутаторов...")
    
    # Создаем анализатор
    analyzer = SwitchAnalyzer()
    
    # Тестовые данные
    test_cases = [
        {
            'IP': '192.168.1.10',
            'Тип устройства': 'Коммутатор',
            'Время работы': '2 часов 15 минут 30 секунд',  # Менее 8 часов
            'Прошивка': '2.7'  # Устаревшая версия
        },
        {
            'IP': '192.168.1.11',
            'Тип устройства': 'Коммутатор', 
            'Время работы': '15 часов 45 минут 12 секунд',  # Более 8 часов
            'Прошивка': '2.12'  # Актуальная версия
        },
        {
            'IP': '192.168.1.12',
            'Тип устройства': 'Коммутатор',
            'Время работы': '120 часов 0 минут 0 секунд',  # Долгая работа
            'Прошивка': '2.15'  # Актуальная версия
        }
    ]
    
    print("\nРезультаты анализа тестовых данных:")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        result = analyzer.analyze_switch_data(test_case)
        
        print(f"\nТест {i}: {result['IP Address']}")
        print(f"  Время работы: {result['Uptime']} ({result['Uptime Hours']} часов)")
        print(f"  Прошивка: {result['Firmware Version']} ({result['Firmware Status']})")
        print(f"  Уровень риска: {result['Risk Score']:.3f}")
        print(f"  Рекомендации: {result['Recommendations']}")
        print("-" * 80)

if __name__ == "__main__":
    test_model()