@echo off
:: Установка необходимых пакетов для Network Scanner (Dahua + Axis + НИЦ)

:: Проверка и установка Net-SNMP (добавлено)
where snmpwalk >nul 2>&1
if %errorlevel% neq 0 (
    echo Net-SNMP not installed!
    echo installing Net-SNMP...
    
    :: Проверяем наличие установочного файла
    if exist "net-snmp-5.5.0-2.x64.exe" (
        start /wait net-snmp-5.5.0-2.x64.exe /S /v"/qn"
        echo Net-SNMP installed.
        
        :: Проверяем успешность установки
        where snmpwalk >nul 2>&1
        if %errorlevel% neq 0 (
            echo Error: Net-SNMP not installed!
            echo Please, install from https://net-snmp.sourceforge.io/
            pause
            exit /b 1
        )
    ) else (
        echo Ошибка: Установочный файл net-snmp-5.5.0-2.x64.exe не найден!
        echo Пожалуйста, скачайте его с https://net-snmp.sourceforge.io/
        pause
        exit /b 1
    )
)

:: 1. Основные зависимости
python -m pip show requests >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing requests...
    python -m pip install requests --user
)

:: 2. Для работы с Excel
python -m pip show openpyxl >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing openpyxl...
    python -m pip install openpyxl --user
)

:: 3. Для анализа данных
python -m pip show pandas >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pandas...
    python -m pip install pandas --user
)

:: 4. Для парсинга Axis
python -m pip show beautifulsoup4 >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing beautifulsoup4...
    python -m pip install beautifulsoup4 --user
)

:: 5. Для работы с Dahua (если используется)
python -m pip show hikvisionapi >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing hikvisionapi...
    python -m pip install hikvisionapi --user
)

:: 6. Дополнительные зависимости для GUI
python -m pip show tk >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing tk...
    python -m pip install tk --user
)

:: Создаем необходимые папки
if not exist "config" (
    mkdir config
    echo Created config folder for settings
)

if not exist "logs" (
    mkdir logs
    echo Created logs folder
)

:: Проверяем установку всех пакетов
echo.
echo Проверка установленных пакетов:
python -m pip list --user | findstr /i "requests pandas openpyxl beautifulsoup4 hikvisionapi tk"

:: Проверяем наличие Net-SNMP после всех установок
where snmpwalk >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Net-SNMP все еще не обнаружен!
    echo Программа не сможет работать с камерами НИЦ.
    echo Установите вручную с https://net-snmp.sourceforge.io/
    pause
)

:: Запускаем приложение
echo.
echo Starting Network Scanner...
python main.py

pause