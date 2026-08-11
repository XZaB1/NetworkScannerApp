import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import os

class SwitchTrainer:
    def __init__(self):
        self.model = self._create_model()
        self.scaler = StandardScaler()
        
    def _create_model(self) -> nn.Module:
        """Создает нейронную сеть"""
        return nn.Sequential(
            nn.Linear(4, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def generate_data(self, num_samples=3000):
        """Генерирует данные для обучения"""
        np.random.seed(42)
        
        data = []
        for _ in range(num_samples):
            uptime_hours = np.random.exponential(200)
            firmware_status = np.random.choice([0, 1, 2])
            error_count = np.random.poisson(2)
            temperature = np.random.normal(40, 10)
            temperature = max(10, min(80, temperature))
            
            risk = 0.1
            risk += min(0.4, (uptime_hours / 1000) ** 0.7)
            
            if firmware_status == 0:
                risk += 0.25
            elif firmware_status == 2:
                risk += 0.15
            
            risk += min(0.2, error_count * 0.08)
            
            if temperature > 60:
                risk += 0.15
            elif temperature > 50:
                risk += 0.08
            elif temperature < 20:
                risk += 0.1
            
            risk = min(0.95, max(0.05, risk))
            risk += np.random.normal(0, 0.02)
            
            data.append([uptime_hours, firmware_status, error_count, temperature, risk])
        
        df = pd.DataFrame(data, columns=['uptime_hours', 'firmware_status', 'error_count', 'temperature', 'risk'])
        df['risk'] = df['risk'].clip(0.05, 0.95)
        return df
    
    def prepare_data(self, df):
        """Подготавливает данные для обучения"""
        X = df[['uptime_hours', 'firmware_status', 'error_count', 'temperature']].values
        y = df['risk'].values
        
        X = self.scaler.fit_transform(X)
        
        return torch.FloatTensor(X), torch.FloatTensor(y)
    
    def calculate_accuracy(self, predictions, targets, threshold=0.5):
        """Вычисляет accuracy для бинарной классификации"""
        binary_pred = (predictions > threshold).float()
        binary_true = (targets > threshold).float()
        accuracy = (binary_pred == binary_true).float().mean()
        return accuracy.item()
    
    def train(self, X, y, epochs=50, learning_rate=0.01, validation_split=0.2):
        """Обучение с сбором accuracy и loss"""
        torch.manual_seed(42)
        np.random.seed(42)
        
        indices = np.random.permutation(len(X))
        split_idx = int(len(X) * (1 - validation_split))
        
        X_train, y_train = X[:split_idx], y[:split_idx]
        X_val, y_val = X[split_idx:], y[split_idx:]
        
        print(f"Размеры: Train {len(X_train)}, Val {len(X_val)}")
        
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        train_losses = []
        val_losses = []
        train_accuracies = []
        val_accuracies = []
        
        print("\nНачало обучения (50 эпох)...")
        
        for epoch in range(epochs):
            # Тренировка
            self.model.train()
            optimizer.zero_grad()
            
            outputs = self.model(X_train)
            loss = criterion(outputs.squeeze(), y_train)
            
            loss.backward()
            optimizer.step()
            
            train_losses.append(loss.item())
            train_acc = self.calculate_accuracy(outputs.squeeze(), y_train)
            train_accuracies.append(train_acc)
            
            # Валидация
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val)
                val_loss = criterion(val_outputs.squeeze(), y_val)
                val_losses.append(val_loss.item())
                
                val_acc = self.calculate_accuracy(val_outputs.squeeze(), y_val)
                val_accuracies.append(val_acc)
            
            if (epoch + 1) % 10 == 0:
                print(f'Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}, Acc: {train_acc:.4f}, Val Loss: {val_loss.item():.4f}, Val Acc: {val_acc:.4f}')
        
        return {
            'train_losses': train_losses,
            'val_losses': val_losses,
            'train_accuracies': train_accuracies,
            'val_accuracies': val_accuracies
        }
    
    def plot_simple_dual_graphs(self, history):
        """ПРОСТОЙ и надежный вариант двух графиков"""
        try:
            train_losses = history['train_losses']
            val_losses = history['val_losses']
            train_accuracies = history['train_accuracies']
            val_accuracies = history['val_accuracies']
            
            # Создаем фигуру
            plt.figure(figsize=(14, 6))
            
            # График 1: Accuracy
            plt.subplot(1, 2, 1)
            epochs = range(1, 51)
            
            plt.plot(epochs, train_accuracies, 'g-', linewidth=2, label='Training Accuracy')
            plt.plot(epochs, val_accuracies, 'orange', linewidth=2, label='Validation Accuracy')
            plt.title('Training and Validation Accuracy', fontsize=14, fontweight='bold')
            plt.xlabel('Epoch')
            plt.ylabel('Accuracy')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xlim(1, 50)
            plt.ylim(0.5, 1.0)
            
            # Простые аннотации для Accuracy
            acc_improvement = train_accuracies[-1] - train_accuracies[0]
            plt.text(25, 0.55, f'Accuracy improvement: {acc_improvement:.3f}', 
                    ha='center', fontsize=10, bbox=dict(facecolor='lightgreen', alpha=0.7))
            
            # График 2: Loss
            plt.subplot(1, 2, 2)
            plt.plot(epochs, train_losses, 'b-', linewidth=2, label='Training Loss')
            plt.plot(epochs, val_losses, 'r-', linewidth=2, label='Validation Loss')
            plt.title('Training and Validation Loss', fontsize=14, fontweight='bold')
            plt.xlabel('Epoch')
            plt.ylabel('Loss (MSE)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xlim(1, 50)
            
            # Простые аннотации для Loss
            loss_improvement = train_losses[0] - train_losses[-1]
            loss_reduction = (1 - train_losses[-1] / train_losses[0]) * 100
            plt.text(25, train_losses[0] * 0.8, f'Loss reduction: {loss_reduction:.1f}%', 
                    ha='center', fontsize=10, bbox=dict(facecolor='lightblue', alpha=0.7))
            
            plt.tight_layout()
            plt.savefig('SIMPLE_DUAL_GRAPH.png', dpi=300, bbox_inches='tight')
            plt.show()
            
            # Статистика в консоли
            self._print_stats(history)
            
        except Exception as e:
            print(f"Ошибка: {e}")
            # Резервный вариант - отдельные графики
            self._plot_backup(history)
    
    def _plot_backup(self, history):
        """Резервный вариант если основной не работает"""
        train_losses = history['train_losses']
        val_losses = history['val_losses']
        train_accuracies = history['train_accuracies']
        val_accuracies = history['val_accuracies']
        
        # Два отдельных графика
        plt.figure(figsize=(12, 5))
        
        plt.subplot(1, 2, 1)
        epochs = range(1, 51)
        plt.plot(epochs, train_accuracies, 'g-', label='Train Acc')
        plt.plot(epochs, val_accuracies, 'orange', label='Val Acc')
        plt.title('Accuracy')
        plt.legend()
        plt.grid(True)
        
        plt.subplot(1, 2, 2)
        plt.plot(epochs, train_losses, 'b-', label='Train Loss')
        plt.plot(epochs, val_losses, 'r-', label='Val Loss')
        plt.title('Loss')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('BACKUP_GRAPH.png', dpi=300)
        plt.show()
    
    def _print_stats(self, history):
        """Статистика в консоли"""
        train_losses = history['train_losses']
        val_losses = history['val_losses']
        train_accuracies = history['train_accuracies']
        val_accuracies = history['val_accuracies']
        
        print("\n" + "="*50)
        print("СТАТИСТИКА ОБУЧЕНИЯ")
        print("="*50)
        print(f"Начальная Accuracy: {train_accuracies[0]:.4f}")
        print(f"Финальная Accuracy: {train_accuracies[-1]:.4f}")
        print(f"Улучшение Accuracy: {train_accuracies[-1] - train_accuracies[0]:.4f}")
        print(f"Начальный Loss: {train_losses[0]:.6f}")
        print(f"Финальный Loss: {train_losses[-1]:.6f}")
        print(f"Улучшение Loss: {train_losses[0] - train_losses[-1]:.6f}")

def main():
    """Упрощенная основная функция"""
    print("ПРОСТОЙ ВАРИАНТ ДВУХ ГРАФИКОВ")
    print("="*50)
    
    trainer = SwitchTrainer()
    
    print("Генерация данных...")
    data = trainer.generate_data(2000)
    
    # Подготовка данных
    X, y = trainer.prepare_data(data)
    
    # Обучение
    history = trainer.train(X, y, epochs=50, learning_rate=0.01)
    
    # Графики
    print("\nПостроение простых графиков...")
    trainer.plot_simple_dual_graphs(history)
    
    print("\nГотово! Файл: SIMPLE_DUAL_GRAPH.png")

if __name__ == "__main__":
    main()