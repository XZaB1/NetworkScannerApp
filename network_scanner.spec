# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],  # ⬅️ ДОБАВЛЕНО - добавляем src в пути поиска
    binaries=[],
    datas=[
        # МОДЕЛИ ИИ - явно указываем каждый файл
        ('src/ai/models/mac_model.pth', 'ai/models'),  # ⬅️ конкретный файл
        ('src/ai/models/switch_model.pth', 'ai/models'),  # ⬅️ конкретный файл
        
        # КОД ИИ 
        ('src/ai/*.py', 'ai'),
        ('src/ai/*.py', 'ai'),
        
        # МОДУЛИ СКАНЕРОВ
        ('src/cameras/*.py', 'cameras'),
        
        ('src/utils/*.py', 'utils'),
        
        # КОНФИГИ
        ('config/*.json', 'config'),
        
        # СТАТИЧЕСКИЕ ФАЙЛЫ
        ('*.png', '.'),
        ('*.ico', '.'),
    ],
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.scrolledtext', 'tkinter.filedialog',
        'pathlib', 'threading', 'json', 'os', 'ipaddress', 're', 'time', 'datetime', 
        'collections', 'collections.defaultdict', 'subprocess',
        'requests', 'requests.auth', 'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw',
        'pandas', 'numpy', 'torch', 'torch.nn', 'torch.optim', 'torch.utils.data',
        'sklearn', 'sklearn.model_selection', 'sklearn.preprocessing',
        'bs4', 'BeautifulSoup', 'hikvisionapi',
        'openpyxl', 'openpyxl.utils', 'openpyxl.styles', 'openpyxl.formatting.rule',
        'utils.path_manager',
        'cameras.switches_tfortis', 'cameras.cameras_hikvision', 'cameras.cameras_dahua', 
        'cameras.cameras_axis', 'cameras.cameras_nits',
        'ai.mac_analyzer', 'ai.mac_model', 'ai.mac_utils', 'ai.mac_train_improved', 
        'ai.mac_train', 'ai.switch_analyzer', 'ai.switch_test', 'ai.switch_train',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NetworkScannerAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='br_logo.ico',
)