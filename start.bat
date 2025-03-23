@echo off
echo Starting BybitMover Setup...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.7 or higher.
    echo You can download it from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check if pip is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo pip is not installed! Please install pip.
    pause
    exit /b 1
)

:: Check if config.json exists
if not exist config.json (
    echo config.json not found! Please create it with your settings.
    echo See README.md for configuration instructions.
    pause
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Start the main script in a new window
echo Starting BybitMover main script...
start "BybitMover Main" cmd /k "python bybit_mover.py > logs\bybit_mover.log 2>&1"

:: Start the web interface in a new window
echo Starting web interface...
start "BybitMover Web" cmd /k "python web_interface.py > logs\web_interface.log 2>&1"

echo.
echo BybitMover is now running!
echo.
echo Main script log: logs\bybit_mover.log
echo Web interface log: logs\web_interface.log
echo.
echo Press any key to stop all processes...
pause

:: Kill the processes
taskkill /F /FI "WINDOWTITLE eq BybitMover Main" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq BybitMover Web" >nul 2>&1

echo.
echo BybitMover stopped.
pause 