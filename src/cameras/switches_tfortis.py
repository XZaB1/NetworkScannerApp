import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import json
import os
from ipaddress import IPv4Address, summarize_address_range
import pandas as pd
import requests
import re
import time
from utils.path_manager import PathManager
from requests.auth import HTTPDigestAuth
from datetime import datetime
from ai.switch_analyzer import SwitchAnalyzer
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import subprocess




_original_subprocess_run = subprocess.run

def _silent_subprocess_run(*args, **kwargs):
    """Автоматически скрывает CMD окна для всех subprocess вызовов"""
    kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
    kwargs.setdefault('stdout', subprocess.PIPE)
    kwargs.setdefault('stderr', subprocess.PIPE)
    return _original_subprocess_run(*args, **kwargs)

# Заменяем стандартный subprocess.run
subprocess.run = _silent_subprocess_run

# Также перехватываем Popen если используется
_original_subprocess_popen = subprocess.Popen

def _silent_subprocess_popen(*args, **kwargs):
    kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
    kwargs.setdefault('stdout', subprocess.PIPE)
    kwargs.setdefault('stderr', subprocess.PIPE)
    return _original_subprocess_popen(*args, **kwargs)

subprocess.Popen = _silent_subprocess_popen

class TFortisWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Сканирование коммутаторов T-Fortis")
        self.master.geometry("1000x800")
        
        # Инициализация переменных
        self.ip_ranges = []
        self.selected_ranges = []
        self.range_vars = []
        self.data = []
        self.stop_scan = False
        self.scan_thread = None
        self.running = False
        
        # Сначала создаем окно для лога ИИ
        self.create_ai_log_window()
        
        # Затем инициализируем AI анализатор
        self.switch_analyzer = SwitchAnalyzer(log_callback=self.add_to_ai_log)
        self.ai_results = []  # Для хранения результатов AI анализа
        
        # Защита от закрытия окна во время сканирования
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Загрузка диапазонов и создание интерфейса
        self.load_ranges()
        self.create_widgets()
    
    def _auto_adjust_columns_excel(self, worksheet, df):
        """Автоматически подбирает ширину колонок, исключая MAC-table"""
        try:
            for idx, column in enumerate(df.columns, 1):
                column_letter = get_column_letter(idx)
                
                # ИСКЛЮЧАЕМ MAC-table из авто-подбора ширины
                if column == 'MAC-table':
                    worksheet.column_dimensions[column_letter].width = 30  # Фиксированная ширина
                    continue
                
                # Определяем максимальную длину в колонке для остальных колонок
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
            print(f"Ошибка авто-подбора колонок: {e}")

    def _apply_excel_formatting_main(self, worksheet, df):
        """Применяет форматирование к таблице"""
        try:
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            
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
                    # ОТКЛЮЧАЕМ ПЕРЕНОС ТЕКСТА ДЛЯ MAC-table
                    if cell.column_letter == get_column_letter(list(df.columns).index('MAC-table') + 1):
                        cell.alignment = Alignment(vertical="center", wrap_text=False)  # ← выключено
                    else:
                        cell.alignment = Alignment(vertical="center", wrap_text=True)   # ← для остальных включено
            
            # Центрируем числовые колонки
            numeric_columns = ['Портов', 'Занятые порты']
            for idx, column in enumerate(df.columns, 1):
                if column in numeric_columns:
                    column_letter = get_column_letter(idx)
                    for row in range(2, worksheet.max_row + 1):
                        cell = worksheet[f"{column_letter}{row}"]
                        cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Замораживаем заголовки
            worksheet.freeze_panes = "A2"
            
        except Exception as e:
            print(f"Ошибка применения форматирования: {e}")

    def create_ai_log_window(self):
        """Создает отдельное окно для лога ИИ анализа коммутаторов"""
        self.ai_log_window = tk.Toplevel(self.master)
        self.ai_log_window.title("Лог анализа коммутаторов (ИИ)")
        self.ai_log_window.geometry("800x400")
        self.ai_log_window.protocol("WM_DELETE_WINDOW", self.hide_ai_log_window)  # Скрывать вместо закрытия
        self.ai_log_window.resizable(True, True)
        
        # Скрываем окно при создании
        self.ai_log_window.withdraw()
        
        self.ai_log = scrolledtext.ScrolledText(self.ai_log_window, wrap=tk.WORD, height=20)
        self.ai_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        button_frame = ttk.Frame(self.ai_log_window)
        button_frame.pack(pady=5)
        
        ttk.Button(
            button_frame, 
            text="Очистить лог",
            command=lambda: self.ai_log.delete(1.0, tk.END)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Скрыть",
            command=self.hide_ai_log_window
        ).pack(side=tk.LEFT, padx=5)
    
    def hide_ai_log_window(self):
        """Скрывает окно лога ИИ вместо закрытия"""
        self.ai_log_window.withdraw()
    
    def show_ai_log_window(self):
        """Показывает окно лога ИИ"""
        self.ai_log_window.deiconify()
        self.ai_log_window.lift()
    
    def add_to_ai_log(self, message, level="info"):
        """Вывод в лог ИИ"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_message = f"[{timestamp}] {message}\n"
            
            # Проверяем, существует ли ai_log
            if hasattr(self, 'ai_log') and self.ai_log.winfo_exists():
                self.ai_log.insert(tk.END, formatted_message)
                self.ai_log.see(tk.END)
                self.ai_log.update_idletasks()
            else:
                # Если окно лога не создано, выводим в консоль
                print(f"[AI_LOG] {formatted_message}")
                
        except Exception as e:
            print(f"Ошибка добавления в лог ИИ: {e}")
    



    def on_close(self):
        """Обработчик закрытия окна"""
        if self.running:
            if messagebox.askokcancel("Выход", "Сканирование еще выполняется. Прервать и выйти?"):
                self.stop_scan_process()
                self.master.destroy()
        else:
            self.master.destroy()
    
    def create_widgets(self):
            """Создание интерфейса"""
            # Основные фреймы
            control_frame = ttk.Frame(self.master)
            control_frame.pack(pady=10, padx=10, fill=tk.X)
            
            range_frame = ttk.LabelFrame(self.master, text="Управление диапазонами IP")
            range_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
            
            # Элементы управления
            self.start_btn = ttk.Button(control_frame, text="Начать сканирование", command=self.start_scan_thread)
            self.start_btn.pack(side=tk.LEFT, padx=5)
            
            self.stop_btn = ttk.Button(control_frame, text="Остановить", command=self.stop_scan_process, state=tk.DISABLED)
            self.stop_btn.pack(side=tk.LEFT, padx=5)
            

            
            # ДОБАВИТЬ ЭТУ КНОПКУ ДЛЯ ОТКРЫТИЯ ЛОГА ИИ
            ttk.Button(control_frame, text="Логи анализа ИИ", command=self.show_ai_log_window).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(control_frame, text="Добавить диапазон", command=self.add_range_dialog).pack(side=tk.RIGHT, padx=5)
            ttk.Button(control_frame, text="Удалить выбранное", command=self.remove_selected_ranges).pack(side=tk.RIGHT, padx=5)
            
            # Прокручиваемый фрейм для диапазонов
            self.canvas = tk.Canvas(range_frame)
            scrollbar = ttk.Scrollbar(range_frame, orient="vertical", command=self.canvas.yview)
            self.scrollable_frame = ttk.Frame(self.canvas)
            
            self.scrollable_frame.bind(
                "<Configure>",
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.configure(yscrollcommand=scrollbar.set)
            
            self.canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Прогресс-бар
            self.progress = ttk.Progressbar(self.master, orient="horizontal", mode="determinate")
            self.progress.pack(fill=tk.X, padx=10, pady=5)
            
            # Лог и результаты
            notebook = ttk.Notebook(self.master)
            
            # Вкладка лога
            log_frame = ttk.Frame(notebook)
            self.log = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
            self.log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            notebook.add(log_frame, text="Лог выполнения")
            
            # Вкладка результатов
            result_frame = ttk.Frame(notebook)
            self.result_text = scrolledtext.ScrolledText(result_frame, height=15, wrap=tk.WORD)
            self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            notebook.add(result_frame, text="Результаты")
            
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Фрейм для кнопок сохранения
            save_frame = ttk.Frame(self.master)
            save_frame.pack(pady=10)
            
            # Кнопка сохранения обычных результатов
            ttk.Button(save_frame, text="Сохранить результаты в Excel", command=self.save_to_excel).pack(side=tk.LEFT, padx=5)
            
            # ДОБАВИТЬ ЭТУ КНОПКУ ДЛЯ СОХРАНЕНИЯ РЕЗУЛЬТАТОВ ИИ
            ttk.Button(save_frame, text="Сохранить результаты AI", command=self.save_ai_to_excel).pack(side=tk.LEFT, padx=5)
            
            # Инициализация чекбоксов
            self.update_range_checkboxes()
    
    def update_range_checkboxes(self):
        """Обновление чекбоксов диапазонов"""
        # Очистка фрейма
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Создание новых чекбоксов
        self.range_vars = []
        for i, (start, end) in enumerate(self.ip_ranges, 1):
            var = tk.BooleanVar(value=(start, end) in self.selected_ranges)
            self.range_vars.append((var, (start, end)))
            
            chk = ttk.Checkbutton(
                self.scrollable_frame,
                text=f"Диапазон {i}: {start} — {end}",
                variable=var,
                command=lambda v=var, r=(start, end): self.toggle_range(v, r)
            )
            chk.pack(anchor="w", padx=5, pady=2)
    
    def toggle_range(self, var, range):
        """Переключение состояния диапазона"""
        if var.get():
            if range not in self.selected_ranges:
                self.selected_ranges.append(range)
        else:
            if range in self.selected_ranges:
                self.selected_ranges.remove(range)
    
    def load_ranges(self):
        """Загрузка диапазонов из файла"""
        try:
            os.makedirs("config", exist_ok=True)
            if os.path.exists("config/ranges.json"):
                with open("config/ranges.json", "r") as f:
                    self.ip_ranges = json.load(f)
            else:
                # Начальные диапазоны по умолчанию
                self.ip_ranges = [
                    ["10.119.190.21", "10.119.190.255"],
                    ["10.119.188.0", "10.119.188.255"],
                    ["10.119.189.0", "10.119.189.255"]
                ]
                self.save_ranges()
            
            # По умолчанию выбираем все диапазоны
            self.selected_ranges = self.ip_ranges.copy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить диапазоны: {str(e)}")
            self.ip_ranges = []
            self.selected_ranges = []
    
    def save_ranges(self):
        """Сохранение диапазонов в файл"""
        try:
            with open("config/ranges.json", "w") as f:
                json.dump(self.ip_ranges, f, indent=4)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить диапазоны: {str(e)}")
    
    def add_range_dialog(self):
        """Диалог добавления нового диапазона"""
        dialog = tk.Toplevel(self.master)
        dialog.title("Добавить диапазон IP")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        
        ttk.Label(dialog, text="Начальный IP:").pack(pady=5)
        start_entry = ttk.Entry(dialog)
        start_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Конечный IP:").pack(pady=5)
        end_entry = ttk.Entry(dialog)
        end_entry.pack(pady=5)
        
        def save_range():
            start = start_entry.get().strip()
            end = end_entry.get().strip()
            
            try:
                IPv4Address(start)
                IPv4Address(end)
                
                new_range = [start, end]
                if new_range not in self.ip_ranges:
                    self.ip_ranges.append(new_range)
                    self.selected_ranges.append(new_range)
                    self.save_ranges()
                    self.update_range_checkboxes()
                    dialog.destroy()
                else:
                    messagebox.showwarning("Внимание", "Такой диапазон уже существует")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Некорректные IP-адреса: {str(e)}")
        
        ttk.Button(dialog, text="Добавить", command=save_range).pack(pady=10)
        start_entry.focus()
    
    def remove_selected_ranges(self):
        """Удаление только отмеченных галочками диапазонов"""
        # Получаем только те диапазоны, которые отмечены галочками
        ranges_to_remove = []
        for var, rng in self.range_vars:
            if var.get():
                # Преобразуем кортеж обратно в список для сравнения
                ranges_to_remove.append(list(rng))
        
        if not ranges_to_remove:
            messagebox.showwarning("Внимание", "Не выбраны диапазоны для удаления")
            return
        
        if not messagebox.askyesno("Подтверждение", 
                                f"Удалить {len(ranges_to_remove)} выбранных диапазонов?"):
            return
        
        # Удаляем только отмеченные диапазоны
        self.ip_ranges = [r for r in self.ip_ranges if r not in ranges_to_remove]
        self.selected_ranges = [r for r in self.selected_ranges if r not in ranges_to_remove]
        
        # Сохраняем и обновляем интерфейс
        self.save_ranges()
        self.update_range_checkboxes()
        
        messagebox.showinfo("Успех", f"Удалено {len(ranges_to_remove)} диапазонов")
    
    def start_scan_thread(self):
        """Запуск сканирования в отдельном потоке"""
        if not self.selected_ranges:
            messagebox.showwarning("Ошибка", "Выберите хотя бы один диапазон!")
            return
        
        if self.running:
            messagebox.showwarning("Внимание", "Сканирование уже выполняется!")
            return
        
        self.stop_scan = False
        self.running = True
        self.data = []
        self.log.delete("1.0", tk.END)
        self.result_text.delete("1.0", tk.END)
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Создаем новый поток для сканирования
        self.scan_thread = threading.Thread(target=self.run_scan, daemon=True)
        self.scan_thread.start()
    
    def stop_scan_process(self):
        """Остановка сканирования"""
        if not self.running:
            return
        
        self.stop_scan = True
        self.running = False
        self.log.insert(tk.END, "\nСканирование остановлено пользователем\n")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def run_cable_test(self, ip, port_num):
        """Запуск кабель-тестера для доступных портов"""
        try:
            num_ports = int(port_num)
            # Определяем, какие порты нужно проверять (исключаем последние 3)
            test_ports = range(0, max(0, num_ports - 3))
            
            results = {}
            for port in test_ports:
                if self.stop_scan or not self.running:
                    return {}
                
                # Механизм для тестирования и отладки кабелей:
                
                # Запускаем тест для порта
                test_result = self.safe_get(f"http://{ip}/api/cableTesterStart?port={port}")
                if test_result is not None:
                    results[f'Тест кабеля порт {port+1}'] = self.clean_string(test_result)
                    self.safe_gui_update(lambda: self.log.insert(tk.END, f"Тест кабеля порт {port+1}: {test_result}\n"))
                time.sleep(1)  # Задержка между тестами
            
            return results
        except ValueError:
            self.safe_gui_update(lambda: self.log.insert(tk.END, f"Ошибка преобразования количества портов: {port_num}\n"))
            return {}
    
    def run_scan(self):
        """Основная функция сканирования"""
        try:
            total_ips = sum(
                len(list(summarize_address_range(IPv4Address(start), IPv4Address(end))))
                for start, end in self.selected_ranges
            )
            
            self.safe_gui_update(lambda: self.progress.config(maximum=total_ips))
            processed = 0
            
            for start, end in self.selected_ranges:
                for ip_range in summarize_address_range(IPv4Address(start), IPv4Address(end)):
                    for ip in ip_range:
                        if self.stop_scan or not self.running:
                            self.safe_gui_update(lambda: self.stop_btn.config(state=tk.DISABLED))
                            self.safe_gui_update(lambda: self.start_btn.config(state=tk.NORMAL))
                            self.running = False
                            return
                        
                        ip_str = str(ip)
                        self.safe_gui_update(lambda: self.log.insert(tk.END, f"Обработка {ip_str}...\n"))
                        self.safe_gui_update(lambda: self.log.see(tk.END))
                        
                        # Проверяем доступность IP
                        if self.ping_ip(ip_str):
                            switch_data = self.get_switch_data(ip_str)
                            if switch_data:
                                self.data.append(switch_data)
                                self.safe_gui_update(
                                    lambda: self.result_text.insert(tk.END, f"{ip_str}: {switch_data}\n"))
                        
                        processed += 1
                        self.safe_gui_update(lambda: self.progress.config(value=processed))
            
            self.safe_gui_update(lambda: self.start_btn.config(state=tk.NORMAL))
            self.safe_gui_update(lambda: self.stop_btn.config(state=tk.DISABLED))
            self.safe_gui_update(lambda: self.log.insert(tk.END, "\nСканирование завершено!\n"))
            
            # АКТИВИРУЕМ КНОПКУ AI АНАЛИЗА (для ручного запуска если нужно)
            self.safe_gui_update(lambda: self.ai_btn.config(state=tk.NORMAL))
            
            # ЕСЛИ ЕСТЬ РЕЗУЛЬТАТЫ AI - АКТИВИРУЕМ КНОПКУ СОХРАНЕНИЯ
            if self.ai_results:
                self.safe_gui_update(lambda: messagebox.showinfo(
                    "AI Анализ завершен", 
                    f"Автоматически проанализировано {len(self.ai_results)} коммутаторов. "
                    f"Результаты готовы для сохранения."
                ))
            
            self.running = False
            
        except Exception as e:
            self.safe_gui_update(lambda: self.log.insert(tk.END, f"\nОшибка при сканировании: {str(e)}\n"))
            self.safe_gui_update(lambda: self.start_btn.config(state=tk.NORMAL))
            self.safe_gui_update(lambda: self.stop_btn.config(state=tk.DISABLED))
            self.running = False
    
    def safe_gui_update(self, func):
        """Безопасное обновление GUI из другого потока"""
        if self.master.winfo_exists():
            self.master.after(0, func)
    
    def ping_ip(self, ip):
        """Проверка доступности IP без показа CMD окна"""
        try:
            import subprocess
            
            # Запускаем ping без окна CMD
            result = subprocess.run(
                ['ping', '-n', '1', ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,  # ⬅️ СКРЫВАЕМ ОКНО
                timeout=5  # Таймаут 5 секунд
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False
    
    def clean_string(self, value):
        """Очистка строки от недопустимых символов"""
        if isinstance(value, str):
            return re.sub(r'[^\x20-\x7E]', '', value)
        return value
    
    def get_switch_data(self, ip):
        """Получение данных с коммутатора T-Fortis"""
        switch_data = {'IP': ip, 'Тип устройства': 'Не коммутатор'}
        
        try:
            # Проверяем, является ли устройство коммутатором
            port_num = self.safe_get(f"http://{ip}/api/getPortNum")
            if not port_num:
                switch_data['Тип устройства'] = 'Не отвечает'
                return switch_data
            
            # Если получили количество портов - это коммутатор
            switch_data['Тип устройства'] = 'Коммутатор'
            switch_data['Портов'] = self.clean_string(port_num) if port_num else None


            dev_name = self.safe_get(f"http://{ip}/api/getDevName")
            if dev_name is not None:
                switch_data['Адрес'] = self.clean_string(dev_name)
            else:
                switch_data['Адрес'] = 'Не указан'

            # === ДОБАВЛЯЕМ ПОЛУЧЕНИЕ СЕРИЙНОГО НОМЕРА ===
            serial_num = self.safe_get(f"http://{ip}/api/getSerialNum")
            if serial_num is not None:
                switch_data['Серийный номер'] = self.clean_string(serial_num)
            else:
                switch_data['Серийный номер'] = 'Не доступен'
            # === КОНЕЦ ДОБАВЛЕНИЯ СЕРИЙНОГО НОМЕРА ===

            try:
                num_ports = int(switch_data['Портов']) if switch_data['Портов'] else 0
                occupied_ports = 0
                
                # Собираем данные портов в правильном порядке (1-10)
                ports_info = {}
                for port in range(1, num_ports + 1):
                    link_info = self.safe_get(f"http://{ip}/api/getLink?port={port-1}")
                    port_status = self.clean_string(link_info) if link_info else None
                    ports_info[f'Порт {port}'] = port_status
                    if port_status and port_status.lower() == 'up':
                        occupied_ports += 1
                
                # Добавляем порты в switch_data в правильном порядке
                for port in sorted(ports_info.keys(), key=lambda x: int(x.split()[1])):
                    switch_data[port] = ports_info[port]
                
                switch_data['Занятые порты'] = occupied_ports
                
                # Удаляем несуществующие порты (если их меньше 10)
                for port in range(num_ports + 1, 11):
                    switch_data.pop(f'Порт {port}', None)
                
                # Запускаем кабель-тестер для доступных портов
                cable_test_results = self.run_cable_test(ip, port_num)
                switch_data.update(cable_test_results)
                        
            except ValueError:
                self.log.insert(tk.END, f"Ошибка преобразования количества портов для IP {ip}\n")
        
            # Дополнительные параметры
            net_ip = self.safe_get(f"http://{ip}/api/getNetIp")
            if net_ip:
                switch_data['IP'] = self.clean_string(net_ip) if net_ip else ip
            
            mac_address = self.safe_get(f"http://{ip}/api/getNetMac")
            if mac_address:
                switch_data['MAC-адрес'] = self.clean_string(mac_address) if mac_address else None
            
            uptime = self.safe_get(f"http://{ip}/api/getUptime")
            if uptime:
                try:
                    uptime_sec = int(uptime)
                    hours = uptime_sec // 3600
                    minutes = (uptime_sec % 3600) // 60
                    seconds = uptime_sec % 60
                    switch_data['Время работы'] = f"{hours} часов {minutes} минут {seconds} секунд"
                except ValueError:
                    switch_data['Время работы'] = self.clean_string(uptime) if uptime else None
            
            fw_version = self.safe_get(f"http://{ip}/api/getFwVersion")
            if fw_version:
                switch_data['Прошивка'] = self.clean_string(fw_version) if fw_version else None
            
            mac_table = self.safe_get(f"http://{ip}/api/getPortMacList")
            if mac_table:
                switch_data['MAC-table'] = self.clean_string(mac_table) if mac_table else None
                
            # === АВТОМАТИЧЕСКИЙ AI АНАЛИЗ НО С СОХРАНЕНИЕМ В ОТДЕЛЬНЫЙ СПИСОК ===
            if switch_data['Тип устройства'] == 'Коммутатор':
                try:
                    # Подготавливаем данные для AI анализа
                    ai_input = {
                        'IP': ip,
                        'Время работы': switch_data.get('Время работы', ''),
                        'Прошивка': switch_data.get('Прошивка', ''),
                        'Тип устройства': 'Коммутатор'
                    }
                    
                    # Дополнительные данные для расширенного анализа
                    additional_data = {
                        'Error Count': self._count_errors(switch_data),
                        'Occupied Ports': switch_data.get('Занятые порты', 0),
                        'Total Ports': switch_data.get('Портов', 0),
                        'Uptime Hours': self._extract_uptime_hours(switch_data.get('Время работы', ''))
                    }
                    
                    # Выполняем AI анализ
                    risk_result = self.switch_analyzer.analyze_switch_data(ai_input)
                    
                    # СОХРАНЯЕМ РЕЗУЛЬТАТ AI В ОТДЕЛЬНЫЙ СПИСОК, а не в switch_data
                    ai_result = {
                        'IP Address': ip,
                        'Uptime': switch_data.get('Время работы', ''),
                        'Firmware Version': switch_data.get('Прошивка', ''),
                        'Risk Score': risk_result.get('Risk Score', 0.5),
                        'Recommendations': risk_result.get('Recommendations', 'Ошибка анализа'),
                        'Analysis Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Добавляем в список AI результатов
                    self.ai_results.append(ai_result)
                    
                    # Логируем в реальном времени (как было)
                    risk_percent = risk_result.get('Risk Score', 0.5) * 100
                    self.add_to_ai_log(f"Коммутатор {ip}: риск {risk_percent:.1f}%")
                    
                    # Выводим рекомендации
                    recommendations = risk_result.get('Recommendations', '')
                    if recommendations:
                        for rec in recommendations.split('; '):
                            if rec.strip():
                                self.add_to_ai_log(f"  → {rec}")
                                
                except Exception as e:
                    error_msg = f"Ошибка AI анализа для {ip}: {str(e)}"
                    self.add_to_ai_log(error_msg, level="error")
                    # Сохраняем ошибку тоже в AI результаты
                    self.ai_results.append({
                        'IP Address': ip,
                        'Error': error_msg,
                        'Risk Score': 0.5,
                        'Recommendations': 'Ошибка анализа'
                    })
            # === КОНЕЦ БЛОКА AI АНАЛИЗА ===
                    
        except Exception as e:
            self.log.insert(tk.END, f"Ошибка при получении данных с {ip}: {str(e)}\n")
            switch_data['Тип устройства'] = f'Ошибка: {str(e)}'
        
        return switch_data

    # Добавляем вспомогательные методы в класс
    def _extract_uptime_hours(self, uptime_str):
        """Извлекает количество часов из времени работы"""
        if not uptime_str:
            return 0
        try:
            # Парсим разные форматы
            if isinstance(uptime_str, (int, float)):
                # Если это число (секунды), конвертируем в часы
                return float(uptime_str) / 3600.0
                
            elif isinstance(uptime_str, str):
                # Парсим "123 часов 45 минут 12 секунд"
                hours_match = re.search(r'(\d+)\s*час', uptime_str)
                minutes_match = re.search(r'(\d+)\s*минут', uptime_str)
                seconds_match = re.search(r'(\d+)\s*секунд', uptime_str)
                
                hours = int(hours_match.group(1)) if hours_match else 0
                minutes = int(minutes_match.group(1)) if minutes_match else 0
                seconds = int(seconds_match.group(1)) if seconds_match else 0
                
                return hours + (minutes / 60.0) + (seconds / 3600.0)
            else:
                return 0
        except:
            return 0

    def _get_firmware_status(self, firmware_str):
        """Определяет статус прошивки (для обратной совместимости)"""
        if not firmware_str:
            return "unknown"
            
        firmware_lower = str(firmware_str).lower()
        if 'старая' in firmware_lower or 'old' in firmware_lower:
            return "outdated"
        elif 'актуаль' in firmware_lower or 'current' in firmware_lower:
            return "current"
        else:
            return "unknown"

    def _count_errors(self, switch_data):
        """Подсчет ошибок в данных коммутатора"""
        error_count = 0
        # Считаем порты с ошибками (если такая информация есть)
        for key in switch_data:
            if key.startswith('Порт ') and switch_data[key] and 'error' in str(switch_data[key]).lower():
                error_count += 1
        return error_count

    def safe_get(self, url):
        """Безопасный HTTP-запрос с обработкой 'Incorrect auth request'"""
        max_attempts = 3  # Уменьшаем количество попыток для скорости
        credentials = [('', ''), (None, None)]  # Сначала с авторизацией, потом без
        
        for auth in credentials:
            attempt = 0
            while attempt < max_attempts:
                try:
                    # Логирование попытки
                    auth_type = "с авторизацией" if auth[0] else "без авторизации"
                    self.log.insert(tk.END, f"Попытка {attempt+1}/{max_attempts} {auth_type}: {url}\n")
                    self.log.see(tk.END)
                    
                    # Настройка запроса
                    kwargs = {
                        'timeout': 10,  # Увеличенный таймаут
                        'verify': False,
                        'headers': {'User-Agent': 'TFortis-Scanner'}
                    }
                    if auth[0]:
                        kwargs['auth'] = HTTPDigestAuth(*auth)
                    
                    response = requests.get(url, **kwargs)
                    text = response.text
                    
                    # Обработка специфичной ошибки T-Fortis
                    if "Incorrect auth request" in text:
                        self.log.insert(tk.END, "Обнаружена ошибка авторизации, жду 10 секунд...\n")
                        time.sleep(12)  # Точное выполнение требования коммутатора
                        continue  # Пробуем снова
                    
                    if response.status_code == 200:
                        return text
                    
                    attempt += 1
                    time.sleep(1)
                
                except requests.exceptions.RequestException as e:
                    self.log.insert(tk.END, f"Ошибка соединения: {str(e)}\n")
                    attempt += 1
                    time.sleep(1)
        
        return None
    
    
    def save_to_excel(self):
        """Сохранение результатов в Excel с авто-форматированием"""
        if not self.data:
            messagebox.showwarning("Ошибка", "Нет данных для сохранения!")
            return
        
        # Фильтруем только коммутаторы и устройства с ошибками
        filtered_data = [
            d for d in self.data 
            if d.get('Тип устройства') == 'Коммутатор' 
        ]
        
        if not filtered_data:
            messagebox.showwarning("Ошибка", "Нет данных о коммутаторах для сохранения!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="tfortis_scan_results.xlsx"
        )
        
        if file_path:
            try:
                df = pd.DataFrame(filtered_data)
                
                # Упорядочиваем колонки - ДОБАВЛЯЕМ 'Серийный номер'
                base_columns = ['IP', 'Адрес', 'Серийный номер', 'Тип устройства', 'Портов', 'Занятые порты', 
                            'MAC-адрес', 'Прошивка', 'Время работы']
                
                # Получаем список портов в правильном порядке (1-10)
                port_columns = sorted(
                    [col for col in df.columns if col.startswith('Порт ')],
                    key=lambda x: int(x.split()[1])
                )
                
                # Добавляем остальные колонки (MAC-table, тесты кабеля и т.д.)
                other_columns = [
                    col for col in df.columns 
                    if col not in base_columns and col not in port_columns
                ]
                
                # Собираем окончательный порядок колонок
                # Если какие-то колонки из base_columns отсутствуют в данных, создаем их
                final_columns = []
                for col in base_columns:
                    if col in df.columns:
                        final_columns.append(col)
                    else:
                        # Если колонки нет в данных, добавляем ее с пустыми значениями
                        df[col] = None
                        final_columns.append(col)
                
                final_columns.extend(port_columns)
                final_columns.extend(other_columns)
                
                # Убеждаемся, что все колонки существуют перед выборкой
                available_columns = [col for col in final_columns if col in df.columns]
                df = df[available_columns]
                
                # ════════════════════════════════════════════════════════════════════
                # ДОБАВЛЯЕМ АВТО-ФОРМАТИРОВАНИЕ КАК В AI АНАЛИЗЕ
                # ════════════════════════════════════════════════════════════════════
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Результаты сканирования')
                    
                    workbook = writer.book
                    worksheet = writer.sheets['Результаты сканирования']
                    
                    # Авто-подбор ширины колонок
                    self._auto_adjust_columns_excel(worksheet, df)
                    
                    # Добавляем форматирование
                    self._apply_excel_formatting_main(worksheet, df)
                    
                    # Добавляем фильтры
                    worksheet.auto_filter.ref = worksheet.dimensions
                # ════════════════════════════════════════════════════════════════════
                
                messagebox.showinfo("Успех", f"Данные сохранены в {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

    def run_ai_analysis(self):
        """Запуск AI анализа найденных коммутаторов"""
        if not self.data:
            messagebox.showwarning("Ошибка", "Нет данных для анализа! Сначала выполните сканирование.")
            return
        
        try:
            # Фильтруем только коммутаторы
            switches_data = [d for d in self.data if d.get('Тип устройства') == 'Коммутатор']
            
            if not switches_data:
                messagebox.showwarning("Ошибка", "Не найдено данных о коммутаторах для анализа!")
                return
            
            self.add_to_ai_log("Запуск AI анализа коммутаторов...")
            
            # Запускаем анализ в отдельном потоке
            threading.Thread(target=self._run_ai_analysis_thread, args=(switches_data,), daemon=True).start()
            
        except Exception as e:
            self.add_to_ai_log(f"Ошибка запуска AI анализа: {str(e)}", level="error")
    
    def _run_ai_analysis_thread(self, switches_data):
        """Поток для выполнения AI анализа"""
        try:
            self.ai_results = self.switch_analyzer.analyze_switches(switches_data)
            
            # Выводим результаты в лог ИИ
            self.add_to_ai_log("=== РЕЗУЛЬТАТЫ AI АНАЛИЗА КОММУТАТОРОВ ===")
            
            for result in self.ai_results:
                risk_percent = result['Risk Score'] * 100
                ip = result['IP Address']
                
                self.add_to_ai_log(f"Коммутатор {ip}: риск {risk_percent:.1f}%")
                
                for line in result['Recommendations'].split('; '):
                    self.add_to_ai_log(f"  → {line}")
                
                self.add_to_ai_log("")  # Пустая строка между коммутаторами
            
            self.add_to_ai_log("AI анализ завершен!")
            
            # Также выводим краткую информацию в основной лог
            self.safe_gui_update(lambda: self.log.insert(tk.END, 
                f"\nAI анализ завершен! Проанализировано {len(self.ai_results)} коммутаторов\n"))
            
        except Exception as e:
            error_msg = f"Ошибка AI анализа: {str(e)}"
            self.add_to_ai_log(error_msg, level="error")
            self.safe_gui_update(lambda: self.log.insert(tk.END, f"\n{error_msg}\n"))
    
    def save_ai_to_excel(self):
        """Сохранение результатов AI анализа в Excel"""
        if not self.ai_results:
            messagebox.showwarning("Ошибка", "Нет результатов AI анализа для сохранения!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"tfortis_ai_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if file_path:
            try:
                self.switch_analyzer.save_ai_analysis_to_excel(self.ai_results, file_path)
                messagebox.showinfo("Успех", f"Результаты AI анализа сохранены в {file_path}")
                self.add_to_ai_log(f"Результаты сохранены в файл: {file_path}")
            except Exception as e:
                error_msg = f"Ошибка при сохранении AI анализа: {str(e)}"
                messagebox.showerror("Ошибка", error_msg)
                self.add_to_ai_log(error_msg, level="error")

if __name__ == "__main__":
    root = tk.Tk()
    app = TFortisWindow(root)
    root.mainloop()
