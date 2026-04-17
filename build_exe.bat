@echo off
cls
echo ========================================================
echo   NI-XNET TELEMETRY EXPLORER - BUILD SYSTEM
echo ========================================================

:: 1. Activate Virtual Environment
:: Assumes your venv folder is named 'venv'
echo [1/4] Activating Virtual Environment...
call venv\Scripts\activate

:: 2. Clean up previous build artifacts
echo [2/4] Cleaning up old build files...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: 3. Execute PyInstaller
echo [3/4] Starting PyInstaller build process...
:: --onefile: Create a single executable
:: --noconsole: Hide the terminal window
:: --icon: Set the EXE icon
:: --add-data: Include the assets folder (Semicolon ; is the separator on Windows)
pyinstaller --onefile ^
            --noconsole ^
            --icon="assets/icon.ico" ^
            --add-data "assets;assets" ^
            --name "IXXAT Plotter" ^
            main.py

:: 4. Finalizing
echo [4/4] Build process finished.
echo.
echo Your standalone executable is located in the 'dist' folder.
echo ========================================================
pause