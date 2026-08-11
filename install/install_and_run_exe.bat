@echo off
title Network Scanner AI - Installation
echo ========================================
echo    Network Scanner AI - Installer
echo ========================================
echo.

:: Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from https://python.org
    echo Then run this script again.
    pause
    exit /b 1
)

:: Проверка Net-SNMP
where snmpwalk >nul 2>&1
if %errorlevel% neq 0 (
    echo Net-SNMP not found!
    echo Installing Net-SNMP...
    
    if exist "net-snmp-5.5.0-2.x64.exe" (
        echo Installing Net-SNMP silently...
        start /wait net-snmp-5.5.0-2.x64.exe /S /v"/qn"
        timeout /t 5
        
        :: Повторная проверка
        where snmpwalk >nul 2>&1
        if %errorlevel% neq 0 (
            echo ERROR: Net-SNMP installation failed!
            echo Please install manually from https://net-snmp.sourceforge.io/
            pause
        ) else (
            echo Net-SNMP successfully installed!
        )
    ) else (
        echo ERROR: net-snmp-5.5.0-2.x64.exe not found!
        echo Please download from https://net-snmp.sourceforge.io/
        pause
    )
)

:: УСТАНОВКА PYTHON ПАКЕТОВ
echo.
echo ========================================
echo    Installing Python packages...
echo ========================================
echo.

python -m pip install requests --user
python -m pip install pandas --user
python -m pip install openpyxl --user
python -m pip install beautifulsoup4 --user
python -m pip install pillow --user
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu --user
python -m pip install scikit-learn --user

:: Создание структуры папок
echo.
echo Creating folder structure...
if not exist "config" mkdir config
if not exist "logs" mkdir logs
if not exist "ScanResults" mkdir ScanResults
if not exist "data" mkdir data

:: Запуск приложения
echo.
echo ========================================
echo    Starting Network Scanner AI...
echo ========================================
echo.

if exist "NetworkScannerAI.exe" (
    NetworkScannerAI.exe
) else (
    echo ERROR: NetworkScannerAI.exe not found!
    echo Building the application first...
    
    :: Попытка автоматической сборки
    if exist "build.bat" (
        call build.bat
        if exist "dist\NetworkScannerAI.exe" (
            copy "dist\NetworkScannerAI.exe" "NetworkScannerAI.exe"
            NetworkScannerAI.exe
        ) else (
            echo Build failed! Please build manually.
            pause
        )
    ) else (
        echo Please build the application first using PyInstaller.
        pause
    )
)