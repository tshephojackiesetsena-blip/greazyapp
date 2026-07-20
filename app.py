
from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'greazy_secret_key_dev_2024'

# Database setup
DATABASE = 'data/greazy.db'

# Menu data with real Unsplash images
MENU_ITEMS = [
    {"id": 1, "name": "Beef Kebab", "price": 79, "category": "sandwich", "description": "Char-grilled kebab cubes, roti, Mediterranean spice, fresh salad.", "image": "https://images.unsplash.com/photo-1593560708920-61dd98c46a1e?auto=format&fit=crop&w=800&q=80"},
    {"id": 2, "name": "Beef Kofta", "price": 75, "category": "sandwich", "description": "Char-grilled smashed kofta roti, Mediterranean spice, fresh salad.", "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80"},
    {"id": 3, "name": "Chicken Kebab", "price": 69, "category": "sandwich", "description": "Char-grilled chicken cubes roti, 24h marinated, fresh salad.", "image": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=800&q=80"},
    {"id": 4, "name": "Beef Shawarma", "price": 79, "category": "sandwich", "description": "Grilled beef strips roll — caramelised onion, garlic & Greazy spices.", "image": "https://images.unsplash.com/photo-1571091718767-18b5b1457add?auto=format&fit=crop&w=800&q=80"},
    {"id": 5, "name": "Chicken Shawarma", "price": 65, "category": "sandwich", "description": "Grilled chicken strips roll — rich tomato, pepper & onion sauce.", "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80"},
    {"id": 6, "name": "Bombay Sausage", "price": 75, "category": "sandwich", "description": "Signature Bombay sausage roll — rich tomato, pepper, onion & garlic sauce.", "image": "https://images.unsplash.com/photo-1612874742237-6526221588e3?auto=format&fit=crop&w=800&q=80"},
    {"id": 7, "name": "Alexandria Liver", "price": 69, "category": "sandwich", "description": "Signature liver roll — 24h marinated, flash-fried with garlic, pepper & chilli.", "image": "https://images.unsplash.com/photo-1607083206869-4c7672e72a8a?auto=format&fit=crop&w=800&q=80"},
    {"id": 8, "name": "Lamb Mix", "price": 149, "category": "meals", "description": "2 skewers: lamb kebab cubes & smashed kofta, 24h marinated in Middle Eastern spices.", "image": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80"},
    {"id": 9, "name": "Beef Kebab Meal", "price": 125, "category": "meals", "description": "2 skewers: beef kebab cubes, 24h marinated in Mediterranean spices.", "image": "https://images.unsplash.com/photo-1603360946369-fc0093607680?auto=format&fit=crop&w=800&q=80"},
    {"id": 10, "name": "Beef Kofta Meal", "price": 119, "category": "meals", "description": "2 skewers: beef smashed kofta, 24h marinated in Mediterranean spices.", "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80"},
    {"id": 11, "name": "Half Chicken", "price": 115, "category": "meals", "description": "Char-grilled half chicken, Greazy's signature spice.", "image": "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?auto=format&fit=crop&w=800&q=80"},
    {"id": 12, "name": "Beef Shawarma Plate", "price": 125, "category": "meals", "description": "180g grilled beef strips — caramelised onion, garlic & Greazy spices.", "image": "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?auto=format&fit=crop&w=800&q=80"},
    {"id": 13, "name": "Chicken Shawarma Plate", "price": 115, "category": "meals", "description": "200g grilled chicken strips — rich tomato, pepper & onion sauce.", "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80"},
    {"id": 14, "name": "Bombay Sausage Plate", "price": 135, "category": "meals", "description": "180g signature Bombay sausage plate — rich tomato, pepper, onion & garlic sauce.", "image": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=800&q=80"},
    {"id": 15, "name": "Alexandria Liver Plate", "price": 115, "category": "meals", "description": "200g signature liver plate — 24h marinated, flash-fried with garlic, pepper & chilli.", "image": "https://images.unsplash.com/photo-1571070259538-9b2d4b20a719?auto=format&fit=crop&w=800&q=80"},
    {"id": 16, "name": "Cheesy Fries", "price": 55, "category": "fries", "description": "Crispy fries topped with melted cheddar cheese and sliced pickled jalapeños.", "image": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=800&q=80"},
    {"id": 17, "name": "BBQ Beef Fries", "price": 69, "category": "fries", "description": "Crispy fries with grilled beef strips & BBQ sauce.", "image": "https://images.unsplash.com/photo-1567016376408-0226e4d0c1ea?auto=format&fit=crop&w=800&q=80"},
    {"id": 18, "name": "Creamy Chicken Fries", "price": 65, "category": "fries", "description": "Crispy fries with grilled chicken strips & creamy garlic sauce.", "image": "https://images.unsplash.com/photo-1567016376408-0226e4d0c1ea?auto=format&fit=crop&w=800&q=80"},
    {"id": 19, "name": "Bombay Fries", "price": 59, "category": "fries", "description": "Crispy fries with Greazy's special hot sausage.", "image": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=800&q=80"},
    {"id": 20, "name": "Greazy Fire 4 Wings", "price": 35, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=800&q=80"},
    {"id": 21, "name": "Greazy Fire 6 Wings", "price": 49, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=800&q=80"},
    {"id": 22, "name": "Crispy Fries - Regular", "price": 29, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=800&q=80"},
    {"id": 23, "name": "Crispy Fries - Large", "price": 35, "category": "fries", "description": "", "image": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=800&q=80"},
    {"id": 24, "name": "Dirty Chai", "price": 35, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=800&q=80"},
    {"id": 25, "name": "Karak Tea", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=800&q=80"},
    {"id": 26, "name": "Cappuccino", "price": 31, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=800&q=80"},
    {"id": 27, "name": "Café Latte", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=800&q=80"},
    {"id": 28, "name": "Espresso", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1511920170033-f8396924c348?auto=format&fit=crop&w=800&q=80"},
    {"id": 29, "name": "Double Espresso", "price": 25, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1511920170033-f8396924c348?auto=format&fit=crop&w=800&q=80"},
    {"id": 30, "name": "Tea (Five Roses, Rooibos)", "price": 19, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=800&q=80"},
    {"id": 31, "name": "Tropical Twist / Sunshine / Blueberry Smoothie", "price": 45, "category": "drinks", "description": "Smoothies, made fresh.", "image": "https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=800&q=80"},
    {"id": 32, "name": "Strawberry / Passion Fruit Mocktail", "price": 35, "category": "drinks", "description": "Mocktails.", "image": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=800&q=80"},
    {"id": 33, "name": "Chocolate / Bar One Milkshake", "price": 39, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=800&q=80"},
    {"id": 34, "name": "Soft Drink", "price": 21, "category": "drinks", "description": "Cola / lemon / orange / berries / pomegranate.", "image": "https://images.unsplash.com/photo-1585518860155-1f61007a0d62?auto=format&fit=crop&w=800&q=80"},
    {"id": 35, "name": "Switch", "price": 23, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1585518860155-1f61007a0d62?auto=format&fit=crop&w=800&q=80"},
    {"id": 36, "name": "Still Water", "price": 15, "category": "drinks", "description": "", "image": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?auto=format&fit=crop&w=800&q=80"}
]

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            order_type TEXT NOT NULL,
            delivery_address TEXT,
            order_notes TEXT,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            timestamp INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def generate_order_id():
    timestamp = datetime.now().strftime('%y%m%d')
    random_suffix = os.urandom(2).hex().upper()
    return f'GRZ-{timestamp}-{random_suffix}'

# Routes
@app.route('/')
def index():
    return render_template('index.html', menu=MENU_ITEMS)

@app.route('/menu')
def menu():
    return render_template('index.html', menu=MENU_ITEMS)

@app.route('/staff')
def staff():
    return render_template('staff.html')

# API Routes
@app.route('/api/menu')
def api_menu():
    return jsonify(MENU_ITEMS)

@app.route('/api/orders', methods=['GET', 'POST'])
def api_orders():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.get_json()
        order_id = generate_order_id()
        items_json = json.dumps(data['items'])
        c.execute('''
            INSERT INTO orders (id, customer_name, customer_phone, order_type, delivery_address, order_notes, items, total, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            data['customerName'],
            data['customerPhone'],
            data['orderType'],
            data.get('deliveryAddress', ''),
            data.get('orderNotes', ''),
            items_json,
            data['total'],
            'pending',
            int(datetime.now().timestamp())
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'orderId': order_id})
    else:
        c.execute('SELECT * FROM orders ORDER BY timestamp DESC')
        orders = c.fetchall()
        conn.close()
        result = []
        for order in orders:
            result.append({
                'id': order['id'],
                'customerName': order['customer_name'],
                'customerPhone': order['customer_phone'],
                'orderType': order['order_type'],
                'deliveryAddress': order['delivery_address'],
                'orderNotes': order['order_notes'],
                'items': json.loads(order['items']),
                'total': order['total'],
                'status': order['status'],
                'timestamp': order['timestamp']
            })
        return jsonify(result)

@app.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (data['status'], order_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

