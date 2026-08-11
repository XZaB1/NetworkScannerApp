import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
from mac_model import MacClassifier, save_model
from mac_utils import extract_mac_features
import random

def generate_training_data():
    """Генерирует синтетические данные для обучения"""
    data = []
    for _ in range(1000):
        # Генерация нормальных MAC (без дубликатов)
        mac = f"{random.randint(0x00, 0xFF):02X}:{random.randint(0x00, 0xFF):02X}:...".lower()
        vendor = "hikvision"
        ip = f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        data.append({
            'mac': mac,
            'vendor': vendor,
            'ip': ip,
            'is_duplicate': 0
        })
        
        # Генерация дубликатов (10% от данных)
        if random.random() < 0.1:
            duplicate_ip = f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            data.append({
                'mac': mac,
                'vendor': vendor,
                'ip': duplicate_ip,
                'is_duplicate': 1
            })
    
    return pd.DataFrame(data)

def train_model():
    # Подготовка данных
    df = generate_training_data()
    mac_groups = df.groupby('mac')
    
    features = []
    labels = []
    
    for mac, group in mac_groups:
        ip_list = group['ip'].tolist()
        vendor = group['vendor'].iloc[0]
        is_duplicate = group['is_duplicate'].max()
        
        features.append(extract_mac_features(mac, vendor, ip_list))
        labels.append(is_duplicate)
    
    # Преобразование в тензоры PyTorch
    X = torch.FloatTensor(features)
    y = torch.FloatTensor(labels).unsqueeze(1)
    
    # Разделение на тренировочные и тестовые данные
    dataset = TensorDataset(X, y)
    train_size = int(0.8 * len(dataset))
    test_size = len(dataset) - train_size
    train_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, test_size])
    
    # Создание модели
    model = MacClassifier(input_size=3)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Обучение
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    for epoch in range(50):
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
    
    # Сохранение модели
    save_model(model)
    
    # Оценка точности
    test_loader = DataLoader(test_dataset, batch_size=32)
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            outputs = model(batch_x)
            predicted = (outputs > 0.7).float()
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
    
    print(f"Accuracy: {100 * correct / total:.2f}%")

if __name__ == "__main__":
    train_model()

        # ===== ДОБАВЛЯЕМ ТЕСТОВЫЙ КОД НИЖЕ =====
    # Загружаем модель для тестов
    model = MacClassifier(input_size=3)
    model.load_state_dict(torch.load("models/mac_model.pth"))
    model.eval()

    # Примеры для проверки (как в реальной сети)
    test_devices = [
        # Пример 1: Обычное устройство (1 MAC - 1 IP)
        {
            "mac": "00:1A:2B:11:22:33",  # Realtek
            "vendor": "dlink",
            "ip_list": ["192.168.1.10"],
            "comment": "Ноутбук в сети (норма)"
        },
        
        # Пример 2: Дубликат (1 MAC - 2 IP в разных подсетях)
        {
            "mac": "AA:BB:CC:44:55:66",  # Фейковый MAC
            "vendor": "unknown",
            "ip_list": ["10.1.1.15", "192.168.2.20"],
            "comment": "Хакер подменил MAC!"
        },
        
        # Пример 3: Роутер (может иметь несколько IP)
        {
            "mac": "C8:3A:35:77:88:99",  # TP-Link
            "vendor": "tplink",
            "ip_list": ["192.168.1.1", "10.0.0.1"],
            "comment": "Роутер (норма)"
        }
    ]

    # Проверяем каждый случай
    print("\n🔍 Проверка модели на тестовых данных:")
    for device in test_devices:
        features = extract_mac_features(device["mac"], device["vendor"], device["ip_list"])
        input_tensor = torch.FloatTensor(features).unsqueeze(0)
        
        with torch.no_grad():
            prob = model(input_tensor).item()
        
        # Простое объяснение
        verdict = "ДУБЛИКАТ (COPY)" if prob > 0.5 else "Норма (YES)"
        print(f"\nMAC: {device['mac']}")
        print(f"IP: {', '.join(device['ip_list'])}")
        print(f"Вендор: {device['vendor'].upper()}")
        print(f"Вероятность дубликата: {prob*100:.1f}% → {verdict}")
        print(f"Пояснение: {device['comment']}")
        print("-" * 50)