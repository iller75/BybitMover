#!/bin/bash

echo "Starting BybitMover Setup..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python is not installed! Please install Python 3.7 or higher."
    echo "You can install it using your package manager."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip is not installed! Please install pip."
    exit 1
fi

# Check if config.json exists
if [ ! -f config.json ]; then
    echo "config.json not found! Please create it with your settings."
    echo "See README.md for configuration instructions."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to stop all processes
stop_processes() {
    echo "Stopping BybitMover processes..."
    pkill -f "python3 bybit_mover.py"
    pkill -f "python3 web_interface.py"
    exit 0
}

# Set up trap for Ctrl+C
trap stop_processes SIGINT SIGTERM

# Start the main script in the background
echo "Starting BybitMover main script..."
python3 bybit_mover.py > logs/bybit_mover.log 2>&1 &
MAIN_PID=$!

# Start the web interface in the background
echo "Starting web interface..."
python3 web_interface.py > logs/web_interface.log 2>&1 &
WEB_PID=$!

echo
echo "BybitMover is now running!"
echo
echo "Main script log: logs/bybit_mover.log"
echo "Web interface log: logs/web_interface.log"
echo
echo "Press Ctrl+C to stop all processes..."

# Wait for user input
while true; do
    sleep 1
done 