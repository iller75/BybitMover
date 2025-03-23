# BybitMover

A tool for automatically moving profits from Bybit sub-accounts to the main account.

## Features

- Automatic profit transfer from sub-accounts to main account
- Configurable profit percentage and minimum threshold
- Margin usage monitoring
- Web interface for monitoring transfers
- Secure user authentication
- Detailed logging
- Growth tracking and predictions

## Prerequisites

- Python 3.8 or higher
- Bybit API keys (main account and sub-accounts)
- A web browser for accessing the interface

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bybitmover.git
cd bybitmover
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the example environment file and configure it:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Configuration

1. Edit `config.json` with your settings:
```json
{
    "check_interval": "5m",  // Format: "5m" for 5 minutes, "2h" for 2 hours
    "profit_percentage": 50,  // Percentage of profit to transfer (1-100)
    "min_profit_threshold": 5,  // Minimum profit in USDT before transferring
    "min_remaining_balance": 50,  // Minimum balance to keep in sub-accounts
    "margin_check": {
        "enabled": true,
        "max_margin_used_percent": 80  // Maximum allowed margin usage percentage
    },
    "accounts": {
        "main_account": {
            "uid": "your_main_account_uid",
            "api_key": "your_main_api_key",
            "api_secret": "your_main_api_secret"
        },
        "sub_accounts": [
            {
                "uid": "sub_account_1_uid",
                "api_key": "sub_account_1_api_key",
                "api_secret": "sub_account_1_api_secret"
            }
        ]
    }
}
```

2. Edit `.env` with your settings:
```bash
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=production
DEFAULT_USERNAME=admin
DEFAULT_PASSWORD=changeme
WEB_PORT=5001
```

## Usage

### Local Development

1. Start the main script:
```bash
python bybit_mover.py
```

2. Start the web interface:
```bash
python web_interface.py
```

3. Access the web interface at `http://localhost:5001`

### VPS Deployment (using PM2)

1. Install PM2 globally:
```bash
npm install -g pm2
```

2. Start the application:
```bash
# Start the main script
pm2 start bybit_mover.py --name bybit_mover --interpreter python3

# Start the web interface
pm2 start web_interface.py --name web_interface --interpreter python3

# Save the PM2 process list to start on system boot
pm2 save

# Set PM2 to start on system boot
pm2 startup
```

3. Monitor the processes:
```bash
# View all processes
pm2 list

# View logs
pm2 logs bybit_mover
pm2 logs web_interface
```

## Security Notes

- Never commit API keys or sensitive data to version control
- Use strong passwords and change default credentials
- Keep dependencies updated
- Monitor logs for suspicious activity

## Disclaimer

This tool is for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this tool.