import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import random
from collections import defaultdict

# Предполагается, что эти функции определены в отдельных файлах
from mac_model import MacClassifier, save_model
from mac_utils import extract_mac_features

def generate_training_data(samples_per_vendor=1000):
    """Улучшенная генерация синтетических данных"""
    vendors = {
        'axis': {'oui': ['b8:a4:4f'], 'ip_range': (196, 217)},
        'hikvision': {'oui': ['c4:2f:90', '18:68:cb'], 'ip_range': (195, 204)},
        'dahua': {'oui': ['b4:4c:3b', 'c0:39:5a'], 'ip_range': (217, 217)}
    }
    
    data = []
    mac_ip_map = defaultdict(list)
    
    for vendor, params in vendors.items():
        for _ in range(samples_per_vendor):
            oui = random.choice(params['oui'])
            mac = f"{oui}:{random.randint(0x00, 0xFF):02x}:{random.randint(0x00, 0xFF):02x}:{random.randint(0x00, 0xFF):02x}"
            ip = f"10.{random.randint(119, 120)}.{random.randint(*params['ip_range'])}.{random.randint(1, 254)}"
            
            data.append({
                'mac': mac,
                'vendor': vendor,
                'ip': ip,
                'is_duplicate': 0
            })
            mac_ip_map[mac].append(ip)
            
            # Генерация дубликатов
            if random.random() < 0.15 and len(mac_ip_map[mac]) == 1:
                duplicate_ip = f"10.{random.randint(119, 120)}.{random.randint(*params['ip_range'])}.{random.randint(1, 254)}"
                data.append({
                    'mac': mac,
                    'vendor': vendor,
                    'ip': duplicate_ip,
                    'is_duplicate': 1
                })
    
    return pd.DataFrame(data)

def train_model():
    # Подготовка данных
    df = generate_training_data(1500)  # 1500 примеров на производителя
    mac_groups = df.groupby('mac')
    
    features = []
    labels = []
    
    for mac, group in mac_groups:
        ip_list = group['ip'].tolist()
        vendor = group['vendor'].iloc[0]
        is_duplicate = group['is_duplicate'].max()
        
        features.append(extract_mac_features(mac, vendor, ip_list))
        labels.append(is_duplicate)
    
    # Балансировка классов
    features, labels = balance_classes(features, labels)
    
    # Преобразование в тензоры
    X = torch.FloatTensor(features)
    y = torch.FloatTensor(labels).unsqueeze(1)
    
    # Разделение данных
    dataset = TensorDataset(X, y)
    train_size = int(0.8 * len(dataset))
    test_size = len(dataset) - train_size
    train_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, test_size])
    
    # Модель и обучение
    model = MacClassifier(input_size=3)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    
    # Обучение с ранней остановкой
    best_acc = 0
    for epoch in range(100):
        model.train()
        for batch_x, batch_y in DataLoader(train_dataset, batch_size=64, shuffle=True):
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
        
        # Валидация
        model.eval()
        with torch.no_grad():
            correct = 0
            total = 0
            for batch_x, batch_y in DataLoader(test_dataset, batch_size=64):
                outputs = model(batch_x)
                predicted = (outputs > 0.5).float()
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
            
            acc = 100 * correct / total
            if acc > best_acc:
                best_acc = acc
                save_model(model)
                print(f'Epoch {epoch}: New best accuracy {acc:.2f}%')
    
    print(f"Final Accuracy: {best_acc:.2f}%")

def balance_classes(features, labels):
    """Балансировка классов для борьбы с дисбалансом"""
    from collections import Counter
    import numpy as np
    
    label_counts = Counter(labels)
    if len(label_counts) < 2:
        return features, labels
    
    minority_class = min(label_counts, key=label_counts.get)
    indices = [i for i, label in enumerate(labels) if label == minority_class]
    
    # Увеличиваем количество примеров меньшинства
    features += [features[i] for i in indices * (label_counts[1-minority_class] // label_counts[minority_class] - 1)]
    labels += [minority_class] * (label_counts[1-minority_class] // label_counts[minority_class] - 1) * len(indices)
    
    return features, labels

if __name__ == "__main__":
    train_model()
    
    # Тестирование на реальных примерах
    model = MacClassifier(input_size=3)
    model.load_state_dict(torch.load("models/mac_model.pth"))
    model.eval()

    test_cases = [
        {
            "mac": "b8:a4:4f:14:be:3a",
            "vendor": "axis",
            "ip_list": ["10.119.196.97"],
            "comment": "Нормальная камера Axis"
        },
        {
            "mac": "b8:a4:4f:14:5d:7e",
            "vendor": "axis",
            "ip_list": ["10.119.217.145", "10.119.217.146"],
            "comment": "Дубликат MAC (аномалия!)"
        },
        {
            "mac": "c4:2f:90:d5:5d:18",
            "vendor": "hikvision",
            "ip_list": ["10.119.195.19"],
            "comment": "Нормальная камера Hikvision"
        }
    ]

    print("\n🔍 Тестирование на реальных сценариях:")
    for case in test_cases:
        features = extract_mac_features(case["mac"], case["vendor"], case["ip_list"])
        with torch.no_grad():
            prob = model(torch.FloatTensor(features).unsqueeze(0)).item()
        
        status = "АНОМАЛИЯ" if prob > 0.5 else "Норма"
        print(f"\nMAC: {case['mac']} ({case['vendor'].upper()})")
        print(f"IP: {', '.join(case['ip_list'])}")
        print(f"Вероятность аномалии: {prob*100:.1f}% → {status}")
        print(f"Пояснение: {case['comment']}")
        print("-"*60)