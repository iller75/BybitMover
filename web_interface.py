from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reloading
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24))  # Generate a random secret key

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Set up logging
logger = logging.getLogger('WebInterface')
logger.setLevel(logging.INFO)

if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler(
    'logs/web_interface.log',
    maxBytes=1024 * 1024,
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
))
logger.addHandler(file_handler)

# Default credentials from environment variables
DEFAULT_USERNAME = os.getenv('DEFAULT_USERNAME', 'admin')
DEFAULT_PASSWORD = os.getenv('DEFAULT_PASSWORD', 'changeme')

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, username):
        self.id = username

def load_users():
    """Load users from file"""
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("users.json not found - please create it with proper credentials")
        return {}

def save_users(users_dict):
    """Save users to file"""
    with open('users.json', 'w') as f:
        json.dump(users_dict, f)

def get_users():
    """Get the current users dictionary"""
    return app.config.get('users', {})

def set_users(users_dict):
    """Set the users dictionary"""
    app.config['users'] = users_dict

# Load users on startup
set_users(load_users())

@login_manager.user_loader
def load_user(username):
    users = get_users()
    if username in users:
        return User(username)
    return None

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        users = get_users()
        if not check_password_hash(users[current_user.id]['password'], current_password):
            flash('Current password is incorrect')
            return render_template('change_password.html')
            
        if new_password != confirm_password:
            flash('New passwords do not match')
            return render_template('change_password.html')
            
        if new_password == DEFAULT_PASSWORD:
            flash('Cannot use default password')
            return render_template('change_password.html')
            
        # Update password
        users[current_user.id]['password'] = generate_password_hash(new_password)
        users[current_user.id]['is_default'] = False
        save_users(users)
        set_users(users)
        
        logger.info(f"Password changed successfully for user {current_user.id}")
        flash('Password changed successfully')
        return redirect(url_for('index'))
        
    return render_template('change_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Reload users from file
        users = load_users()
        set_users(users)
        
        if username in users and check_password_hash(users[username]['password'], password):
            user = User(username)
            login_user(user)
            logger.info(f"User {username} logged in successfully")
            
            # If using default password, force password change
            if users[username].get('is_default', False):
                flash('Please change your password')
                return redirect(url_for('change_password'))
                
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
        logger.warning(f"Failed login attempt for username: {username}")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found")
        return {"web_port": 5001}

def load_transfer_history():
    """Load transfer history from file if it exists"""
    try:
        with open('transfer_history.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("transfer_history.json not found, starting with empty history")
        return []

def calculate_totals(transfers):
    """Calculate totals for main account and sub-accounts"""
    main_account_total = 0
    sub_account_totals = {}
    
    for transfer in transfers:
        amount = float(transfer['amount'])
        from_account = transfer['from_account']
        
        # Add to main account total
        main_account_total += amount
        
        # Add to sub-account totals
        if from_account not in sub_account_totals:
            sub_account_totals[from_account] = 0
        sub_account_totals[from_account] += amount
    
    return main_account_total, sub_account_totals

def calculate_growth_prediction(transfers, days_to_predict=30):
    """Calculate predicted growth based on average daily transfers"""
    if not transfers:
        return 0, 0
    
    # Group transfers by date
    daily_totals = {}
    for transfer in transfers:
        date = transfer['timestamp'].split('T')[0]
        amount = float(transfer['amount'])
        daily_totals[date] = daily_totals.get(date, 0) + amount
    
    # Calculate average daily transfer
    avg_daily_transfer = sum(daily_totals.values()) / len(daily_totals)
    predicted_growth = avg_daily_transfer * days_to_predict
    
    return avg_daily_transfer, predicted_growth

@app.route('/')
@login_required
def index():
    """Display the transfer history with totals and predictions"""
    transfers = load_transfer_history()
    
    # Calculate totals and predictions
    main_account_total, sub_account_totals = calculate_totals(transfers)
    avg_daily, predicted_30d = calculate_growth_prediction(transfers)
    
    # Prepare data for charts
    chart_data = prepare_chart_data(transfers)
    
    return render_template('index.html', 
                         transfers=transfers,
                         main_account_total=main_account_total,
                         sub_account_totals=sub_account_totals,
                         num_transfers=len(transfers),
                         avg_daily_transfer=avg_daily,
                         predicted_30d_growth=predicted_30d,
                         chart_data=chart_data)

def prepare_chart_data(transfers):
    """Prepare data for the growth charts"""
    # Sort transfers by date
    sorted_transfers = sorted(transfers, key=lambda x: x['timestamp'])
    
    # Accumulate balances over time
    dates = []
    main_balance = []
    running_total = 0
    
    for transfer in sorted_transfers:
        date = transfer['timestamp'].split('T')[0]
        amount = float(transfer['amount'])
        running_total += amount
        
        dates.append(date)
        main_balance.append(running_total)
    
    return {
        'dates': dates,
        'main_balance': main_balance
    }

def add_transfer(from_account, to_account, amount, timestamp=None):
    """Add a new transfer to the history"""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    transfer = {
        'from_account': from_account,
        'to_account': to_account,
        'amount': amount,
        'timestamp': timestamp
    }
    
    # Load existing transfers
    transfers = load_transfer_history()
    transfers.append(transfer)
    
    # Save updated transfers
    with open('transfer_history.json', 'w') as f:
        json.dump(transfers, f)
    
    logger.info(f"Added transfer: {amount} USDT from {from_account} to {to_account}")

if __name__ == '__main__':
    # Load configuration
    config = load_config()
    port = config.get('web_port', 5001)
    
    print(f"Starting web interface on port {port}...")
    print(f"Access the interface at http://localhost:{port}")
    print("Default credentials:")
    print(f"Username: {DEFAULT_USERNAME}")
    print(f"Password: {DEFAULT_PASSWORD}")
    print("Press Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=port, debug=True) 