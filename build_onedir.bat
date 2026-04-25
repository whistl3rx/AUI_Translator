@echo off
setlocal

REM Windows onedir build script (faster startup than onefile)
REM Output: dist\AUI_Translator\AUI_Translator.exe

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [INFO] PyInstaller nincs telepitve. Telepites...
  python -m pip install pyinstaller
)

if not exist "dist" mkdir dist
if not exist "build" mkdir build

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --console ^
  --name "AUI_Translator" ^
  --collect-all PyQt5 ^
  src\main.py

if errorlevel 1 (
  echo [ERROR] Build sikertelen.
  exit /b 1
)

echo [OK] Build kesz: dist\AUI_Translator\AUI_Translator.exe
endlocal
