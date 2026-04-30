@echo off
setlocal
REM ============================================================
REM patentdoc-conv: Build distributable .exe for Windows
REM
REM Usage:
REM   1) Activate venv (.venv\Scripts\activate)
REM   2) Run this script (double-click or cmd/PowerShell)
REM
REM Output:
REM   dist\PatentdocConv.exe  (standalone, no Python required)
REM ============================================================

echo [1/3] Installing required packages...
python -m pip install --upgrade pip >nul
python -m pip install -e . pyinstaller
if errorlevel 1 (
    echo ERROR: Package install failed.
    pause
    exit /b 1
)

echo [2/3] Removing old build / dist...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [3/3] Running PyInstaller...
python -m PyInstaller --noconfirm --clean PatentdocConv.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Build complete: dist\PatentdocConv.exe
echo Double-click the exe to verify the GUI launches correctly.
echo ============================================================
pause
endlocal
