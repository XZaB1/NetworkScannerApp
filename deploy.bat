@echo off
title Network Scanner AI - Launcher
echo ========================================
echo    ГКУ ВО "Безопасный регион"
echo    Network Scanner AI v4.1
echo ========================================
echo.

:: Проверка административных прав
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ВНИМАНИЕ: Запуск без прав администратора
    echo Для установки Net-SNMP могут потребоваться права администратора
    echo.
)

:: Проверка Net-SNMP
where snmpwalk >nul 2>&1
if %errorlevel% neq 0 (
    echo Net-SNMP не обнаружен!
    echo Установка Net-SNMP...
    echo.
    
    if exist "net-snmp-5.5.0-2.x64.exe" (
        echo Запуск установки Net-SNMP...
        net-snmp-5.5.0-2.x64.exe /S /v"/qn"
        timeout /t 7
        echo Ожидание завершения установки...
        
        :: Повторная проверка
        where snmpwalk >nul 2>&1
        if %errorlevel% neq 0 (
            echo.
            echo ОШИБКА: Установка Net-SNMP не удалась!
            echo Пожалуйста, установите вручную с:
            echo https://net-snmp.sourceforge.io/
            echo.
            pause
        ) else (
            echo Net-SNMP успешно установлен!
        )
    ) else (
        echo.
        echo ОШИБКА: Файл net-snmp-5.5.0-2.x64.exe не найден!
        echo.
        echo Пожалуйста, скачайте Net-SNMP с:
        echo https://net-snmp.sourceforge.io/
        echo и поместите в папку с программой
        echo.
        pause
        exit /b 1
    )
) else (
    echo Net-SNMP обнаружен, проверка пройдена.
)

:: Создание структуры папок
echo.
echo Создание структуры папок...
if not exist "config" (
    mkdir config
    echo Создана папка config
)
if not exist "logs" (
    mkdir logs
    echo Создана папка logs
)
if not exist "ScanResults" (
    mkdir ScanResults
    echo Создана папка ScanResults
)
if not exist "data" (
    mkdir data
    echo Создана папка data
)

:: Создание ярлыка на рабочем столе
echo.
echo Создание ярлыка на рабочем столе...
set SHORTCUT_PATH=%userprofile%\Desktop\Network Scanner AI.lnk
if not exist "%SHORTCUT_PATH%" (
    powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%userprofile%\Desktop\Network Scanner AI.lnk'); $Shortcut.TargetPath = '%~dp0NetworkScannerAI.exe'; $Shortcut.IconLocation = '%~dp0br_logo.ico'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = 'Network Scanner AI v4.1'; $Shortcut.Save()"
    echo Ярлык создан: %SHORTCUT_PATH%
) else (
    echo Ярлык уже существует
)

:: Запуск приложения
echo.
echo ========================================
echo    Запуск Network Scanner AI...
echo ========================================
echo.
timeout /t 2

if exist "NetworkScannerAI.exe" (
    echo Запуск приложения...
    NetworkScannerAI.exe
) else (
    echo.
    echo ОШИБКА: Файл NetworkScannerAI.exe не найден!
    echo.
    echo Убедитесь, что:
    echo 1. Файл находится в этой папке
    echo 2. Название файла: NetworkScannerAI.exe
    echo.
    pause
)