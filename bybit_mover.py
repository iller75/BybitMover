#!/usr/bin/env python3
import json
import time
import re
import schedule
from datetime import datetime, timedelta
from pybit.unified_trading import HTTP
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
from web_interface import add_transfer
import random
import uuid
import sys
import logging
from logging.handlers import RotatingFileHandler

# Set up logging
def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    logger = logging.getLogger('BybitMover')
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/bybit_mover.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

class BybitMover:
    def __init__(self, config_path='config.json'):
        self.config = self.load_config(config_path)
        self.check_interval = self.parse_interval(self.config['check_interval'])
        self.profit_percentage = self.config['profit_percentage']
        self.min_profit_threshold = self.config['min_profit_threshold']
        self.test_mode = self.config.get('test_mode', False)
        self.api_sessions = {}
        self.initial_balances = {}
        self.last_balances = {}
        self.transfer_history = []
        self.load_transfer_history()
        
        # Initialize API sessions
        self.initialize_api_sessions()
        
        # Initialize balances
        self.initialize_balances()
        
        logger.info(f"Running in {'TEST' if self.test_mode else 'LIVE'} mode")
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Profit percentage: {self.profit_percentage}%")
        logger.info(f"Minimum profit threshold: {self.min_profit_threshold} USDT")

    def load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Parse the check_interval into minutes
                interval = config['check_interval']
                if not re.match(r'^\d+[mh]$', interval):
                    raise ValueError("check_interval must be in format: '5m' or '2h'")
                return config
        except FileNotFoundError:
            print("Error: config.json not found. Please create it with your settings.")
            exit(1)

    def initialize_sessions(self):
        """Initialize API sessions for all accounts"""
        # Initialize main account session
        main_account = self.config['accounts']['main_account']
        self.sessions[main_account['uid']] = HTTP(
            testnet=False,
            api_key=main_account['api_key'],
            api_secret=main_account['api_secret']
        )

        # Initialize sub-account sessions
        for sub_account in self.config['accounts']['sub_accounts']:
            self.sessions[sub_account['uid']] = HTTP(
                testnet=False,
                api_key=sub_account['api_key'],
                api_secret=sub_account['api_secret']
            )

    def get_account_balance(self, account_id):
        """Get the balance for a specific account"""
        try:
            # Find the API key for this account ID
            api_key = None
            if account_id == self.config['accounts']['main_account']['uid']:
                api_key = self.config['accounts']['main_account']['api_key']
            else:
                for sub_account in self.config['accounts']['sub_accounts']:
                    if sub_account['uid'] == account_id:
                        api_key = sub_account['api_key']
                        break
            
            if api_key not in self.api_sessions:
                print(f"Error: No session found for account {account_id}")
                return 0

            if self.test_mode:
                # Simulate balance with random fluctuations
                if account_id not in self.last_balances:
                    self.last_balances[account_id] = 100.0  # Start with 100 USDT
                
                # Simulate random profit/loss (-10 to +10 USDT)
                change = random.uniform(-10, 10)
                self.last_balances[account_id] += change
                return self.last_balances[account_id]

            response = self.api_sessions[api_key].get_wallet_balance(
                accountType="UNIFIED",
                coin="USDT"  # We're tracking USDT balance
            )
            if response['retCode'] == 0:
                return float(response['result']['list'][0]['totalWalletBalance'])
            return 0
        except Exception as e:
            print(f"Error getting balance for {account_id}: {str(e)}")
            return 0

    def initialize_balances(self):
        """Initialize the initial balances for all accounts"""
        print("\nInitializing account balances...")
        for sub_account in self.config['accounts']['sub_accounts']:
            account_uid = sub_account['uid']
            initial_balance = self.get_account_balance(account_uid)
            self.initial_balances[account_uid] = initial_balance
            self.last_balances[account_uid] = initial_balance
            print(f"Initial balance for {account_uid}: {initial_balance} USDT")

    def calculate_profit(self, account_id):
        """Calculate profit for a specific account since last check"""
        current_balance = self.get_account_balance(account_id)
        if account_id not in self.last_balances:
            self.last_balances[account_id] = current_balance
            return 0
        
        # Calculate profit since last check
        profit = current_balance - self.last_balances[account_id]
        self.last_balances[account_id] = current_balance
        
        # Calculate total profit since start
        total_profit = current_balance - self.initial_balances[account_id]
        
        print(f"Account {account_id}:")
        print(f"  Current balance: {current_balance} USDT")
        print(f"  Profit since last check: {profit} USDT")
        print(f"  Total profit since start: {total_profit} USDT")
        
        return profit

    def transfer_funds(self, from_account, to_account, amount):
        """Transfer funds between accounts with test mode support"""
        if self.test_mode:
            print(f"[TEST MODE] Would transfer {amount} USDT from {from_account} to {to_account}")
            # Simulate transfer success
            success = True
        else:
            try:
                from_session = self.api_sessions[from_account]
                to_session = self.api_sessions[to_account]
                
                # Get account UIDs from config
                from_uid = next(acc['uid'] for acc in self.config['accounts']['sub_accounts'] 
                              if acc['api_key'] == from_account)
                to_uid = self.config['accounts']['main_account']['uid']
                
                # Create transfer
                response = from_session.create_universal_transfer(
                    transferId=str(uuid.uuid4()),
                    fromAccountType="UNIFIED",
                    toAccountType="UNIFIED",
                    fromMemberId=from_uid,
                    toMemberId=to_uid,
                    coin="USDT",
                    amount=str(amount)
                )
                
                success = response.get('retCode') == 0
            except Exception as e:
                print(f"Error transferring funds: {str(e)}")
                success = False
        
        if success:
            self.record_transfer(from_account, to_account, amount)
            print(f"Successfully transferred {amount} USDT from {from_account} to {to_account}")
            return True
        else:
            print(f"Failed to transfer {amount} USDT from {from_account} to {to_account}")
            return False

    def get_interval_minutes(self):
        """Convert check_interval to minutes"""
        interval = self.config['check_interval']
        if interval.endswith('m'):
            return int(interval[:-1])
        elif interval.endswith('h'):
            return int(interval[:-1]) * 60
        return 60  # default to 1 hour if invalid format

    def check_margin_usage(self, account_id):
        """Check if margin usage is below threshold"""
        if not self.config.get('margin_check', {}).get('enabled', False):
            return True  # Skip check if margin checking is disabled
            
        if self.test_mode:
            return True  # In test mode, assume margin is fine
            
        try:
            # Get position info from Bybit
            response = self.api_sessions[account_id].get_position_list(
                category="linear",
                settleCoin="USDT"
            )
            if response['retCode'] != 0:
                print(f"Error getting position info: {response['retMsg']}")
                return False
                
            positions = response['result']['list']
            total_margin_used = sum(float(pos['positionValue']) for pos in positions)
            current_balance = self.get_account_balance(account_id)
            
            if current_balance == 0:
                return False
                
            margin_percentage = (total_margin_used / current_balance) * 100
            max_margin = self.config['margin_check']['max_margin_used_percent']
            
            print(f"  Margin usage: {margin_percentage:.2f}% (max allowed: {max_margin}%)")
            return margin_percentage < max_margin
            
        except Exception as e:
            print(f"Error checking margin: {str(e)}")
            return False

    def check_remaining_balance(self, account_id, transfer_amount):
        """Check if enough balance will remain after transfer"""
        current_balance = self.get_account_balance(account_id)
        min_remaining = self.config.get('min_remaining_balance', 50)  # Default 50 USDT
        remaining = current_balance - transfer_amount
        
        print(f"  Balance after transfer would be: {remaining:.2f} USDT (min required: {min_remaining} USDT)")
        return remaining > min_remaining

    def process_profits(self):
        """Process profits for all source accounts"""
        current_time = datetime.now()
        print(f"\nProcessing profits at {current_time}")
        
        main_account_uid = self.config['accounts']['main_account']['uid']
        
        for sub_account in self.config['accounts']['sub_accounts']:
            account_uid = sub_account['uid']
            current_balance = self.get_account_balance(account_uid)
            initial_balance = self.initial_balances[account_uid]
            
            # Calculate total profit since start
            total_profit = current_balance - initial_balance
            
            print(f"\nAccount {account_uid}:")
            print(f"  Current balance: {current_balance:.2f} USDT")
            print(f"  Initial balance: {initial_balance:.2f} USDT")
            print(f"  Total profit: {total_profit:.2f} USDT")
            
            if total_profit > self.min_profit_threshold:
                transfer_amount = total_profit * (self.profit_percentage / 100)
                print(f"  Profit exceeds threshold ({self.min_profit_threshold} USDT)")
                print(f"  Calculated transfer amount: {transfer_amount:.2f} USDT")
                
                # Check margin usage if enabled
                if not self.check_margin_usage(account_uid):
                    print("  Transfer skipped: Margin usage too high")
                    continue
                
                # Check minimum remaining balance
                if not self.check_remaining_balance(account_uid, transfer_amount):
                    print("  Transfer skipped: Would leave insufficient balance")
                    continue
                
                if transfer_amount > 0:
                    success = self.transfer_funds(
                        account_uid,
                        main_account_uid,
                        transfer_amount
                    )
                    if success:
                        # Update initial balance after successful transfer
                        self.initial_balances[account_uid] = current_balance - total_profit + transfer_amount
                        print(f"  New initial balance set to: {self.initial_balances[account_uid]:.2f} USDT")
            else:
                print(f"  No significant profit (needs > {self.min_profit_threshold} USDT) to transfer")
        
        self.last_check_time = current_time

    def get_balance(self, session, account_uid):
        """Get account balance with test mode support"""
        if self.test_mode:
            # Simulate balance with random fluctuations
            if account_uid not in self.last_balances:
                self.last_balances[account_uid] = 100.0  # Start with 100 USDT
            
            # Simulate small random profit/loss
            change = random.uniform(-5, 5)
            self.last_balances[account_uid] += change
            
            return {
                'retCode': 0,
                'retMsg': 'OK',
                'result': {
                    'list': [{
                        'coin': 'USDT',
                        'walletBalance': str(self.last_balances[account_uid]),
                        'availableBalance': str(self.last_balances[account_uid])
                    }]
                }
            }
        
        try:
            response = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            return response
        except Exception as e:
            print(f"Error getting balance for account {account_uid}: {str(e)}")
            return None

    def initialize_api_sessions(self):
        """Initialize API sessions for all accounts"""
        # Initialize main account session
        main_account = self.config['accounts']['main_account']
        self.api_sessions[main_account['api_key']] = HTTP(
            testnet=False,
            api_key=main_account['api_key'],
            api_secret=main_account['api_secret']
        )

        # Initialize sub-account sessions
        for sub_account in self.config['accounts']['sub_accounts']:
            self.api_sessions[sub_account['api_key']] = HTTP(
                testnet=False,
                api_key=sub_account['api_key'],
                api_secret=sub_account['api_secret']
            )

    def load_transfer_history(self):
        """Load transfer history from file"""
        try:
            with open('transfer_history.json', 'r') as f:
                self.transfer_history = json.load(f)
        except FileNotFoundError:
            print("Warning: transfer_history.json not found. Starting with empty history.")

    def record_transfer(self, from_account, to_account, amount):
        """Record a transfer in the transfer history"""
        transfer = {
            'from_account': from_account,
            'to_account': to_account,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        }
        self.transfer_history.append(transfer)
        self.save_transfer_history()

    def save_transfer_history(self):
        """Save transfer history to file"""
        with open('transfer_history.json', 'w') as f:
            json.dump(self.transfer_history, f)

    def parse_interval(self, interval):
        """Parse interval string into seconds"""
        if not re.match(r'^\d+[mh]$', interval):
            raise ValueError("check_interval must be in format: '5m' or '2h'")
        
        number = int(interval[:-1])
        unit = interval[-1]
        
        if unit == 'm':
            return number * 60
        elif unit == 'h':
            return number * 3600
        else:
            raise ValueError("Invalid interval unit. Use 'm' for minutes or 'h' for hours")

def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    mover = BybitMover(config_path)
    
    # Get interval in minutes
    minutes = mover.get_interval_minutes()
    
    # Schedule the profit processing
    schedule.every(minutes).minutes.do(mover.process_profits)
    
    print(f"BybitMover started. Checking every {mover.config['check_interval']}")
    print("Press Ctrl+C to stop")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping BybitMover...")
            break

if __name__ == "__main__":
    main() 