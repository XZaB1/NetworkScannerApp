@echo off
title Network Scanner AI - Builder
echo ========================================
echo    Network Scanner AI - Build Tool
echo ========================================
echo.

:: Проверка PyInstaller
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

:: Проверка иконки
if not exist "br_logo.ico" (
    echo Creating ICO file from PNG...
    python -c "from PIL import Image; Image.open('br_logo_blur.png').save('br_logo.ico', format='ICO')"
    if exist "br_logo.ico" (
        echo ICO file created successfully!
    ) else (
        echo WARNING: ICO file not created
    )
)

:: Очистка предыдущих сборок
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

:: Сборка (main.py находится в src/)
echo Building EXE file...
pyinstaller network_scanner.spec

echo.
echo ========================================
echo BUILD COMPLETED!
echo EXE file: dist\NetworkScannerAI.exe
echo ========================================
echo.
pause