import torch
import torch.nn as nn
import os

class MacClassifier(nn.Module):
    """Нейросеть для классификации MAC-адресов"""
    def __init__(self, input_size=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        return self.net(x)

def save_model(model, path="models/mac_model.pth"):
    """Сохраняет модель и создает папку при необходимости"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(model.state_dict(), path)