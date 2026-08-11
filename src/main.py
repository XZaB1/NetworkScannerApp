import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
from utils.path_manager import PathManager
from cameras.switches_tfortis import TFortisWindow
from cameras.cameras_hikvision import HikvisionWindow
from cameras.cameras_dahua import DahuaWindow
from cameras.cameras_axis import AxisWindow
from cameras.cameras_nits import NitsWindow
import os
import subprocess


class InstructionWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Инструкция по использованию")
        self.master.geometry("800x600")
        self.master.resizable(False, False)
        
        # Устанавливаем желтоватый фон как у бумаги для всего окна
        self.master.configure(bg="#ffffff")  # Бежевый цвет (цвет старой бумаги)
        
        self.create_widgets()
        self.center_window()
    
    def center_window(self):
        self.master.update_idletasks()
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        x = (self.master.winfo_screenwidth() // 2) - (width // 2)
        y = (self.master.winfo_screenheight() // 2) - (height // 2)
        self.master.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        # content_frame тоже с желтоватым фоном
        content_frame = ttk.Frame(self.master)
        content_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        
        instruction_text = """
1. Убедитесь, что все пакеты приложения установлены 
(Все пакеты устанавливаются при помощи bat-файла, идущего в комплекте с приложением)        

2. Выберите тип устройства для сканирования:
   - Коммутаторы TFortis
   - Камеры Hikvision
   - Камеры Dahua
   - Камеры Axis
   - Камеры НИЦ

3. Настройте диапазоны IP-адресов 
(Если сканируете коммутаторы TFortis и Вам нужно видеть AI лог - нажмите соответствующую кнопку в верхней части окна и инициируйте AI)
Рекомендация: Для TFortis используйте диапазон сканирования до 50 адресов.

4. Нажмите "Начать сканирование"

5. Просмотрите результаты в логе

6. Сохраните результаты при необходимости

Дополнительные функции:
- Добавление своих диапазонов IP
- Фильтрация результатов (общий файл|AI)
- Экспорт в Excel/TXT"""
        
        text_widget = tk.Text(
            content_frame, 
            wrap=tk.WORD, 
            font=('Helvetica', 12),
            padx=10,
            pady=10,
            bg="#f7f7d9",  # Светло-желтый фон для текстового поля (цвет слоновой кости)
            fg="#1B1B1B",  # Темно-серый текст для лучшей читаемости
            relief='solid',  # Добавляем рамку
            bd=1  # Толщина рамки
        )
        text_widget.insert(tk.END, instruction_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(
            self.master, 
            text="Закрыть", 
            command=self.master.destroy,
            style="Accent.TButton"
        ).pack(pady=10)


class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ГКУ ВО Безопасный регион - NetworkScannerApp v4.1")
        self.root.geometry("500x500")
        self.root.minsize(400, 400)
        
        self.root.resizable(False, False)

        self.set_window_icon()

        self.setup_styles()
        self.create_background()
        self.create_menu()
        self.create_device_buttons()
        
        # Инициализация PathManager
        PathManager().init_paths()
        self.center_window()


    def silent_subprocess(cmd, **kwargs):
        """Запускает subprocess без показа CMD окна"""
        if isinstance(cmd, str):
            cmd = cmd.split()
        
        kwargs.setdefault('stdout', subprocess.PIPE)
        kwargs.setdefault('stderr', subprocess.PIPE)
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
    
        return subprocess.run(cmd, **kwargs)
    
    def open_window(self, window_class):
        """Универсальный метод для открытия окон"""
        try:
            print(f"Попытка открыть окно: {window_class}")
            window = tk.Toplevel(self.root)
            window_class(window)
            print(f"Окно {window_class} успешно открыто")
        except Exception as e:
            print(f"ОШИБКА при открытии окна {window_class}: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Ошибка", f"Не удалось открыть окно: {e}")

    def set_window_icon(self):
        """Установка иконки для главного окна"""
        try:
            # Просто проверяем файлы в текущей директории
            if os.path.exists("br_logo.ico"):
                self.root.iconbitmap("br_logo.ico")
                print("Иконка окна установлена из ICO файла")
            elif os.path.exists("br_logo_blur.png"):
                img = Image.open("br_logo_blur.png")
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                print("Иконка окна установлена из PNG файла")
            else:
                print("Файлы иконок не найдены, используется стандартная иконка")
        except Exception as e:
            print(f"Ошибка при загрузке иконки: {e}")

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")
    
    def setup_styles(self):
        style = ttk.Style()
        style.configure("TButton", padding=10, font=('Helvetica', 12))
        style.configure("Title.TLabel", font=('Helvetica', 18, 'bold'), foreground='black', Background='')
        style.configure("Accent.TButton", foreground='black', background='#2c3e50')
        style.map("Accent.TButton", background=[('active', "#686B54")])
    
    def create_background(self):
        """Создание фонового изображения"""
        try:
            # Создание Canvas для фона
            self.canvas = tk.Canvas(self.root)
            self.canvas.pack(fill="both", expand=True)
            
            # Попытка загрузить изображение (замените путь на свой)
            image_path = Path("br_logo_blur.png")  # Укажите путь к вашему изображению
            
            if image_path.exists():
                # Загрузка изображения
                self.original_image = Image.open(image_path)
                self.bg_image = None
                self.update_background()  # Первоначальная установка фона
                
                # Привязка события изменения размера окна
                self.root.bind('<Configure>', self.on_resize)
            else:
                # Создание градиентного фона если изображение не найдено
                self.create_gradient_background()
                
        except Exception as e:
            print(f"Ошибка загрузки фонового изображения: {e}")
            # Создание градиентного фона в случае ошибки
            self.create_gradient_background()
    
    def on_resize(self, event):
        """Обработчик изменения размера окна"""
        if hasattr(self, 'original_image') and event.widget == self.root:
            self.update_background()
    
    def update_background(self):
        """Обновление фонового изображения при изменении размера окна"""
        if hasattr(self, 'original_image'):
            # Получаем текущий размер окна
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            if width > 1 and height > 1:  # Проверяем, что окно уже отобразилось
                # Масштабируем изображение под размер окна
                resized_image = self.original_image.resize((width, height), Image.LANCZOS)
                
                # Создаем полупрозрачный оверлей для лучшей читаемости текста
                overlay = Image.new('RGBA', (width, height), (0, 0, 0, 50))  # 20% прозрачности
                resized_image = resized_image.convert('RGBA')
                final_image = Image.alpha_composite(resized_image, overlay)
                
                self.bg_image = ImageTk.PhotoImage(final_image)
                
                # Обновляем изображение на Canvas
                self.canvas.delete("background")
                self.canvas.create_image(0, 0, image=self.bg_image, anchor="nw", tags="background")
    
    def create_gradient_background(self):
        """Создание градиентного фона если изображение недоступно"""
        def update_gradient(event=None):
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            self.canvas.delete("gradient")
            for i in range(height):
                # Градиент от #1e3c72 до #2a5298
                r = int(30 + (42 - 30) * i / height)
                g = int(60 + (82 - 60) * i / height)
                b = int(114 + (152 - 114) * i / height)
                color = f'#{r:02x}{g:02x}{b:02x}'
                self.canvas.create_line(0, i, width, i, fill=color, tags="gradient")
        
        # Создаем первоначальный градиент
        self.root.after(100, update_gradient)
        # Обновляем при изменении размера
        self.root.bind('<Configure>', update_gradient)
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Инструкция", command=self.show_instructions)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Приложение", menu=file_menu)
        
        self.root.config(menu=menubar)

    def show_instructions(self):
        window = tk.Toplevel(self.root)
        InstructionWindow(window)

    def create_device_buttons(self):
        # Откладываем построение кнопок и текста, чтобы Canvas успел получить размеры
        self.root.after(100, self._draw_device_ui)

    def draw_text_with_outline(self, canvas, x, y, text, font, fill='white', outline='black'):
        """Рисует текст с тройным контуром"""
        # Первый слой контура (самый толстый)
        for dx in [-3, 0, 3]:
            for dy in [-3, 0, 3]:
                if dx != 0 or dy != 0:
                    canvas.create_text(x + dx, y + dy, text=text, font=font, fill=outline, tags="ui")
        
        # Второй слой контура (средний)
        for dx in [-2, 0, 2]:
            for dy in [-2, 0, 2]:
                if dx != 0 or dy != 0:
                    canvas.create_text(x + dx, y + dy, text=text, font=font, fill=outline, tags="ui")
        
        # Третий слой контура (тонкий)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    canvas.create_text(x + dx, y + dy, text=text, font=font, fill=outline, tags="ui")
        
        # Основной текст
        canvas.create_text(x, y, text=text, font=font, fill=fill, tags="ui")

    def _draw_device_ui(self):
        self.canvas.update_idletasks()  # Обновляем геометрию окна
        x_center = self.canvas.winfo_width() // 2
        y_center = 100  # вертикальная позиция надписи
        
        # Очищаем предыдущие элементы UI (если нужно перерисовать)
        self.canvas.delete("ui")
        
        # Используем метод для текста с контуром
        self.draw_text_with_outline(
            self.canvas, 
            x_center, 
            y_center, 
            "Выберите тип устройства", 
            ('Helvetica', 28, 'bold'),
            fill='Red',      # Цвет текста
            outline="#000000",   # Цвет контура
      # Толщина контура
        )

        # Кнопки
        buttons = [
            ("Коммутаторы TFortis", self.open_tfortis),
            ("Камеры Hikvision", self.open_hikvision),
            ("Камеры Dahua", self.open_dahua),
            ("Камеры Axis", self.open_axis),
            ("Камеры НИЦ", self.open_nits)
        ]

        y = 180
        for text, command in buttons:
            btn = ttk.Button(self.canvas, text=text, command=command, style="TButton")
            self.canvas.create_window(x_center, y, window=btn, width=250, tags="ui")
            y += 55


    def open_window(self, window_class):
        """Универсальный метод для открытия окон"""
        window = tk.Toplevel(self.root)
        window_class(window)

    def open_tfortis(self):
        self.open_window(TFortisWindow)

    def open_hikvision(self):
        self.open_window(HikvisionWindow)

    def open_dahua(self):
        self.open_window(DahuaWindow)

    def open_axis(self):
        self.open_window(AxisWindow)

    def open_nits(self):
        self.open_window(NitsWindow)


if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()