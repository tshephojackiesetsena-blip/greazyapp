import os
import json
import secrets
import smtplib
import sqlite3
from datetime import datetime
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can still be set another way
    pass

app = Flask(__name__)

# --- Secret key -------------------------------------------------------
# Pull from the environment in production. Falls back to a randomly
# generated key for local dev so the app never ships with a hardcoded
# secret baked into source control.
_secret_key = os.getenv('FLASK_SECRET_KEY')
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    print("WARNING: FLASK_SECRET_KEY is not set. Using a random key for this "
          "run only, which will invalidate sessions on restart. Set "
          "FLASK_SECRET_KEY in your .env for production.")
app.config['SECRET_KEY'] = _secret_key

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Only send the session cookie over HTTPS when running in production
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'

# --- Config -------------------------------------------------------------
DATABASE = os.getenv('DATABASE_PATH', 'data/greazy.db')

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@greazy.co.za')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

VALID_ORDER_STATUSES = {'pending', 'preparing', 'ready', 'completed'}
VALID_PAYMENT_STATUSES = {'pending', 'completed'}
VALID_ORDER_TYPES = {'delivery', 'pickup', 'dine-in'}

PAYMENT_METHODS = [
    {'id': 'card', 'name': 'Credit/Debit Card', 'icon': '💳'},
    {'id': 'eft', 'name': 'EFT Transfer', 'icon': '🏦'},
    {'id': 'cash', 'name': 'Cash on Delivery', 'icon': '💵'},
    {'id': 'wallet', 'name': 'Greazy Wallet', 'icon': '👛'}
]
VALID_PAYMENT_METHODS = {m['id'] for m in PAYMENT_METHODS}

# Menu data with real Unsplash images
MENU_ITEMS = [
    {"id": 1, "name": "Beef Kebab", "price": 79, "category": "sandwich", "description": "Char-grilled kebab cubes, roti, Mediterranean spice, fresh salad.", "image": "https://images.unsplash.com/photo-1699728088614-7d1d4277414b?auto=format&fit=crop&w=800&q=80"},
    {"id": 2, "name": "Beef Kofta", "price": 75, "category": "sandwich", "description": "Char-grilled smashed kofta roti, Mediterranean spice, fresh salad.", "image": "https://images.unsplash.com/photo-1633321702518-7feccafb94d5?auto=format&fit=crop&w=800&q=80"},
    {"id": 3, "name": "Chicken Kebab", "price": 69, "category": "sandwich", "description": "Char-grilled chicken cubes roti, 24h marinated, fresh salad.", "image": "https://images.unsplash.com/photo-1779086646395-00668466d0d0?auto=format&fit=crop&w=800&q=80"},
    {"id": 4, "name": "Beef Shawarma", "price": 79, "category": "sandwich", "description": "Grilled beef strips roll — caramelised onion, garlic & Greazy spices.", "image": "https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=800&q=80"},
    {"id": 5, "name": "Chicken Shawarma", "price": 65, "category": "sandwich", "description": "Grilled chicken strips roll — rich tomato, pepper & onion sauce.", "image": "https://images.unsplash.com/photo-1662116765994-1e4200c43589?auto=format&fit=crop&w=800&q=80"},
    {"id": 6, "name": "Bombay Sausage", "price": 75, "category": "sandwich", "description": "Signature Bombay sausage roll — rich tomato, pepper, onion & garlic sauce.", "image": "https://images.unsplash.com/photo-1612874742237-6526221588e3?auto=format&fit=crop&w=800&q=80"},
    {"id": 7, "name": "Alexandria Liver", "price": 69, "category": "sandwich", "description": "Signature liver roll — 24h marinated, flash-fried with garlic, pepper & chilli.", "image": "https://images.unsplash.com/photo-1607083206869-4c7672e72a8a?auto=format&fit=crop&w=800&q=80"},
    {"id": 8, "name": "Lamb Mix", "price": 149, "category": "meals", "description": "2 skewers: lamb kebab cubes & smashed kofta, 24h marinated in Middle Eastern spices.", "image": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80"},
    {"id": 9, "name": "Beef Kebab Meal", "price": 125, "category": "meals", "description": "2 skewers: beef kebab cubes, 24h marinated in Mediterranean spices.", "image": "https://images.unsplash.com/photo-1717250180256-2cedbc62180d?auto=format&fit=crop&w=800&q=80"},
    {"id": 10, "name": "Beef Kofta Meal", "price": 119, "category": "meals", "description": "2 skewers: beef smashed kofta, 24h marinated in Mediterranean spices.", "image": "https://images.unsplash.com/photo-1653983194833-7a10838b12f4?auto=format&fit=crop&w=800&q=80"},
    {"id": 11, "name": "Half Chicken", "price": 115, "category": "meals", "description": "Char-grilled half chicken, Greazy's signature spice.", "image": "https://images.unsplash.com/photo-1630564510761-a560db92a09b?auto=format&fit=crop&w=800&q=80"},
    {"id": 12, "name": "Beef Shawarma Plate", "price": 125, "category": "meals", "description": "180g grilled beef strips — caramelised onion, garlic & Greazy spices.", "image": "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?auto=format&fit=crop&w=800&q=80"},
    {"id": 13, "name": "Chicken Shawarma Plate", "price": 115, "category": "meals", "description": "200g grilled chicken strips — rich tomato, pepper & onion sauce.", "image": "https://images.unsplash.com/photo-1719282431987-2382e77e5a1b?auto=format&fit=crop&w=800&q=80"},
    {"id": 14, "name": "Bombay Sausage Plate", "price": 135, "category": "meals", "description": "180g signature Bombay sausage plate — rich tomato, pepper, onion & garlic sauce.", "image": "https://images.unsplash.com/photo-1633436375795-12b3b339712f?auto=format&fit=crop&w=800&q=80"},
    {"id": 15, "name": "Alexandria Liver Plate", "price": 115, "category": "meals", "description": "200g signature liver plate — 24h marinated, flash-fried with garlic, pepper & chilli.", "image": "https://images.unsplash.com/photo-1571070259538-9b2d4b20a719?auto=format&fit=crop&w=800&q=80"},
    {"id": 37, "name": "The Flix", "price": 65, "category": "braam-deals", "description": "Char-Grilled Quarter Chicken, Greazy's signature spice. Served with: Fries + Sauce", "image": "https://images.unsplash.com/photo-1639131285716-3fc7f624f138?auto=format&fit=crop&w=800&q=80"},
    {"id": 38, "name": "Mix & Match", "price": 115, "category": "braam-deals", "description": "Pick any 2 Roll Sandwiches: Bombay Sausage - Beef Shawarma - Chicken Shawarma - Alexandria Liver. Served with: Fries + Sauce", "image": "https://images.unsplash.com/photo-1773620494884-940e0db95e46?auto=format&fit=crop&w=800&q=80"},
    {"id": 39, "name": "Full Chicken Feast", "price": 199, "category": "braam-deals", "description": "Char-Grilled Full Chicken, Greazy's signature spice. Served with: Fries + Sauce", "image": "https://images.unsplash.com/photo-1712579733874-c3a79f0f9d12?auto=format&fit=crop&w=800&q=80"},
    {"id": 16, "name": "Cheesy Fries", "price": 55, "category": "fries", "description": "Crispy fries topped with melted cheddar cheese and sliced pickled jalapeños.", "image": "https://images.unsplash.com/photo-1639744210631-209fce3e256c?auto=format&fit=crop&w=800&q=80"},
    {"id": 17, "name": "BBQ Beef Fries", "price": 69, "category": "fries", "description": "Crispy fries with grilled beef strips & BBQ sauce.", "image": "https://images.unsplash.com/photo-1771818708792-d671ae9b4b46?auto=format&fit=crop&w=800&q=80"},
    {"id": 18, "name": "Creamy Chicken Fries", "price": 65, "category": "fries", "description": "Crispy fries with grilled chicken strips & creamy garlic sauce.", "image": "https://images.unsplash.com/photo-1609530127564-bee93ebe1c9e?auto=format&fit=crop&w=800&q=80"},
    {"id": 19, "name": "Bombay Fries", "price": 59, "category": "fries", "description": "Crispy fries with Greazy's special hot sausage.", "image": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=800&q=80"},
    {"id": 20, "name": "Greazy Fire 4 Wings", "price": 35, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1608039755401-742074f0548d?auto=format&fit=crop&w=800&q=80"},
    {"id": 21, "name": "Greazy Fire 6 Wings", "price": 49, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1637273484026-11d51fb64024?auto=format&fit=crop&w=800&q=80"},
    {"id": 22, "name": "Crispy Fries - Regular", "price": 29, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1584378868074-1ebfd5a636c7?auto=format&fit=crop&w=800&q=80"},
    {"id": 23, "name": "Crispy Fries - Large", "price": 35, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1639744091981-2f826321fae6?auto=format&fit=crop&w=800&q=80"},
    {"id": 24, "name": "Dirty Chai", "price": 35, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1636920272028-c27f1ae474c3?auto=format&fit=crop&w=800&q=80"},
    {"id": 25, "name": "Karak Tea", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1619581073186-5b4ae1b0caad?auto=format&fit=crop&w=800&q=80"},
    {"id": 26, "name": "Cappuccino", "price": 31, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1550731358-491ded4af838?auto=format&fit=crop&w=800&q=80"},
    {"id": 27, "name": "Café Latte", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1559001724-fbad036dbc9e?auto=format&fit=crop&w=800&q=80"},
    {"id": 28, "name": "Espresso", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1511426420268-4cfdd3763b77?auto=format&fit=crop&w=800&q=80"},
    {"id": 29, "name": "Double Espresso", "price": 25, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1503240778100-fd245e17a273?auto=format&fit=crop&w=800&q=80"},
    {"id": 30, "name": "Tea (Five Roses, Rooibos)", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1594137260937-f59050746e36?auto=format&fit=crop&w=800&q=80"},
    {"id": 31, "name": "Tropical Twist / Sunshine / Blueberry Smoothie", "price": 45, "category": "drinks", "description": "Smoothies, made fresh.", "image": "https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=800&q=80"},
    {"id": 32, "name": "Strawberry / Passion Fruit Mocktail", "price": 35, "category": "drinks", "description": "Mocktails.", "image": "https://images.unsplash.com/photo-1570696516188-ade861b84a49?auto=format&fit=crop&w=800&q=80"},
    {"id": 33, "name": "Chocolate / Bar One Milkshake", "price": 39, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1653085315536-1379bc836161?auto=format&fit=crop&w=800&q=80"},
    {"id": 34, "name": "Soft Drink", "price": 21, "category": "drinks", "description": "Cola / lemon / orange / berries / pomegranate.", "image": "https://images.unsplash.com/photo-1761281137117-42da05306117?auto=format&fit=crop&w=800&q=80"},
    {"id": 35, "name": "Switch", "price": 23, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1761281137117-42da05306117?auto=format&fit=crop&w=800&q=80"},
    {"id": 36, "name": "Still Water", "price": 15, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1561041695-d2fadf9f318c?auto=format&fit=crop&w=800&q=80"},
    {"id": 40, "name": "Bread", "price": 8, "category": "sides", "description": "Roti or Roll.", "image": "https://images.unsplash.com/photo-1640625314547-aee9a7696589?auto=format&fit=crop&w=800&q=80"},
    {"id": 41, "name": "Rice", "price": 25, "category": "sides", "description": "Rice with Vermicelli.", "image": "https://images.unsplash.com/photo-1536304993881-ff6e9eefa2a6?auto=format&fit=crop&w=800&q=80"},
    {"id": 42, "name": "Salad", "price": 15, "category": "sides", "description": "Greazy's Special Salad.", "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80"},
    {"id": 43, "name": "Extra Sauce", "price": 9, "category": "sides", "description": "Tahina / Tzatziki / Garlic / Ketchup / Chilli.", "image": "https://images.unsplash.com/photo-1563599175592-c58dc214deff?auto=format&fit=crop&w=800&q=80"}
]

# Fast lookup used to price orders server-side instead of trusting the client
MENU_BY_ID = {item['id']: item for item in MENU_ITEMS}


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    db_dir = os.path.dirname(DATABASE)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            last_login INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            order_type TEXT NOT NULL,
            delivery_address TEXT,
            order_notes TEXT,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            status TEXT DEFAULT 'pending',
            timestamp INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Seed (or fix up) the admin account. If ADMIN_PASSWORD changes in the
    # environment, re-hash and update it so the .env is the source of truth.
    c.execute('SELECT id, password FROM users WHERE email = ?', (ADMIN_EMAIL,))
    existing_admin = c.fetchone()
    if not existing_admin:
        c.execute('''
            INSERT INTO users (email, password, full_name, phone, is_admin, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), 'Greazy Admin',
              '+27000000000', 1, int(datetime.now().timestamp())))
        if ADMIN_PASSWORD == 'admin123':
            print("WARNING: Using the default admin password ('admin123'). "
                  "Set ADMIN_PASSWORD in your .env before deploying.")

    conn.commit()
    conn.close()


def generate_order_id():
    timestamp = datetime.now().strftime('%y%m%d')
    random_suffix = os.urandom(2).hex().upper()
    return f'GRZ-{timestamp}-{random_suffix}'


def send_admin_notification(order_id, customer_name, customer_phone, total, payment_method):
    """Send email notification to admin when order is placed"""
    try:
        if not SMTP_USER or not SMTP_PASSWORD:
            print(f"Email config not set. Order {order_id} placed by {customer_name}")
            return True

        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = f'🍽️ New Order Received: {order_id}'

        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #FF6B35;">New Order Received! 🎉</h2>
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Customer Name:</strong> {customer_name}</p>
                <p><strong>Customer Phone:</strong> {customer_phone}</p>
                <p><strong>Total Amount:</strong> R{total}</p>
                <p><strong>Payment Method:</strong> {payment_method}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><a href="{os.getenv('APP_BASE_URL', 'http://localhost:5000')}/staff" style="background-color: #FF6B35; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View in Dashboard</a></p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email notification: {e}")
        return False


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
        user = c.fetchone()
        conn.close()

        if not user or not user['is_admin']:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# --- Authentication routes ----------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        full_name = (data.get('fullName') or '').strip()
        phone = (data.get('phone') or '').strip()

        if not all([email, password, full_name, phone]):
            return jsonify({'success': False, 'message': 'All fields required'}), 400

        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'success': False, 'message': 'Please enter a valid email address'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

        conn = get_db()
        c = conn.cursor()

        try:
            hashed_password = generate_password_hash(password)
            c.execute('''
                INSERT INTO users (email, password, full_name, phone, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, hashed_password, full_name, phone, int(datetime.now().timestamp())))
            conn.commit()

            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = c.fetchone()
            session.clear()
            session['user_id'] = user['id']
            session['email'] = email
            session['full_name'] = full_name
            session['is_admin'] = 0

            conn.close()
            return jsonify({'success': True, 'message': 'Registration successful!'}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'message': 'Email already registered'}), 409
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, password, full_name, is_admin FROM users WHERE email = ?', (email,))
        user = c.fetchone()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['email'] = email
            session['full_name'] = user['full_name']
            session['is_admin'] = user['is_admin']

            c.execute('UPDATE users SET last_login = ? WHERE id = ?', (int(datetime.now().timestamp()), user['id']))
            conn.commit()
            conn.close()

            if user['is_admin']:
                return jsonify({'success': True, 'redirect': '/staff'}), 200
            return jsonify({'success': True, 'redirect': '/'}), 200

        conn.close()
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# --- Page routes ----------------------------------------------------------
@app.route('/')
def index():
    user_logged_in = 'user_id' in session
    return render_template('index.html', menu=MENU_ITEMS, user_logged_in=user_logged_in,
                            user_name=session.get('full_name'))


@app.route('/menu')
def menu():
    user_logged_in = 'user_id' in session
    return render_template('index.html', menu=MENU_ITEMS, user_logged_in=user_logged_in,
                            user_name=session.get('full_name'))


@app.route('/staff')
@admin_required
def staff():
    return render_template('staff.html')


# --- API routes -------------------------------------------------------------
@app.route('/api/menu')
def api_menu():
    return jsonify(MENU_ITEMS)


@app.route('/api/payment-methods')
def api_payment_methods():
    return jsonify(PAYMENT_METHODS)


@app.route('/api/orders', methods=['GET', 'POST'])
def api_orders():
    if request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Must be logged in to place order'}), 401

        data = request.get_json(silent=True) or {}

        customer_name = (data.get('customerName') or '').strip()
        customer_phone = (data.get('customerPhone') or '').strip()
        order_type = data.get('orderType', 'pickup')
        delivery_address = (data.get('deliveryAddress') or '').strip()
        order_notes = (data.get('orderNotes') or '').strip()
        payment_method = data.get('paymentMethod', 'cash')
        raw_items = data.get('items')

        if not customer_name or not customer_phone:
            return jsonify({'success': False, 'message': 'Name and phone are required'}), 400

        if order_type not in VALID_ORDER_TYPES:
            return jsonify({'success': False, 'message': 'Invalid order type'}), 400

        if order_type == 'delivery' and not delivery_address:
            return jsonify({'success': False, 'message': 'Delivery address is required'}), 400

        if payment_method not in VALID_PAYMENT_METHODS:
            return jsonify({'success': False, 'message': 'Invalid payment method'}), 400

        if not raw_items or not isinstance(raw_items, list):
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400

        # Re-price the order from the server-side menu instead of trusting
        # whatever total/prices the client sent. This is the fix for the
        # "edit the request body to pay whatever you want" bug.
        priced_items = []
        total = 0
        for raw_item in raw_items:
            try:
                item_id = int(raw_item.get('id'))
                quantity = int(raw_item.get('quantity', 1))
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'Invalid item in cart'}), 400

            if quantity < 1 or quantity > 50:
                return jsonify({'success': False, 'message': 'Invalid item quantity'}), 400

            menu_item = MENU_BY_ID.get(item_id)
            if not menu_item:
                return jsonify({'success': False, 'message': f'Unknown menu item: {item_id}'}), 400

            priced_items.append({
                'id': menu_item['id'],
                'name': menu_item['name'],
                'price': menu_item['price'],
                'quantity': quantity
            })
            total += menu_item['price'] * quantity

        if total <= 0:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400

        order_id = generate_order_id()
        items_json = json.dumps(priced_items)

        conn = get_db()
        c = conn.cursor()

        try:
            c.execute('''
                INSERT INTO orders (id, user_id, customer_name, customer_phone, order_type, delivery_address, order_notes, items, total, payment_method, payment_status, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_id,
                session['user_id'],
                customer_name,
                customer_phone,
                order_type,
                delivery_address,
                order_notes,
                items_json,
                total,
                payment_method,
                'pending',
                'pending',
                int(datetime.now().timestamp())
            ))
            conn.commit()
            conn.close()

            send_admin_notification(order_id, customer_name, customer_phone, total, payment_method)

            return jsonify({'success': True, 'orderId': order_id, 'total': total}), 201
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        conn = get_db()
        c = conn.cursor()

        if 'user_id' in session:
            c.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY timestamp DESC', (session['user_id'],))
        else:
            conn.close()
            return jsonify([]), 200

        orders = c.fetchall()
        conn.close()
        return jsonify([_serialize_order(order) for order in orders]), 200


@app.route('/api/admin/orders', methods=['GET'])
@admin_required
def api_admin_orders():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM orders ORDER BY timestamp DESC')
    orders = c.fetchall()
    conn.close()
    return jsonify([_serialize_order(order) for order in orders]), 200


def _serialize_order(order):
    return {
        'id': order['id'],
        'customerName': order['customer_name'],
        'customerPhone': order['customer_phone'],
        'orderType': order['order_type'],
        'deliveryAddress': order['delivery_address'],
        'orderNotes': order['order_notes'],
        'items': json.loads(order['items']),
        'total': order['total'],
        'paymentMethod': order['payment_method'],
        'paymentStatus': order['payment_status'],
        'status': order['status'],
        'timestamp': order['timestamp']
    }


@app.route('/api/orders/<order_id>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    if new_status not in VALID_ORDER_STATUSES:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    conn.commit()
    updated = c.rowcount
    conn.close()

    if not updated:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    return jsonify({'success': True})


@app.route('/api/orders/<order_id>/payment', methods=['PUT'])
@admin_required
def update_payment_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get('paymentStatus')
    if new_status not in VALID_PAYMENT_STATUSES:
        return jsonify({'success': False, 'message': 'Invalid payment status'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE orders SET payment_status = ? WHERE id = ?', (new_status, order_id))
    conn.commit()
    updated = c.rowcount
    conn.close()

    if not updated:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    return jsonify({'success': True})


if __name__ == '__main__':
    init_db()
    debug_mode = os.getenv('FLASK_ENV', 'development') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
