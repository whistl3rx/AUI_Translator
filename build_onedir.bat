@echo off
setlocal

REM Windows onedir build script (faster startup than onefile)
REM Output: dist\AUI_Translator\AUI_Translator.exe

echo [INFO] Dependencies telepitese/frissitese (requirements.txt)...
python -m pip install -r requirements.txt

echo [INFO] PyInstaller ellenorzese...
python -m pip install pyinstaller

if not exist "dist" mkdir dist
if not exist "build" mkdir build

python -m PyInstaller ^
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
