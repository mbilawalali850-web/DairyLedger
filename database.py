import sqlite3
from werkzeug.security import generate_password_hash
# Agar helpers file nahi hai to aap DB_PATH = 'dairy_khata.db' direct likh sakte hain
try:
    from helpers import DB_PATH
except ImportError:
    DB_PATH = 'dairy_khata.db'


def _add_column_if_missing(cursor, table, column, col_def):
    try:
        # Hum direct column add karne ki koshish karenge
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_def}')
    except sqlite3.OperationalError as e:
        # Agar error "duplicate column" ka hai, toh ignore karein
        if "duplicate column name" in str(e):
            pass
        else:
            print(f"Notice: {e}")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'helper')''')

    # 2. Customers Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 3. Rates Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        base_rate REAL NOT NULL,
        fat_base REAL NOT NULL,
        fat_rate_per_point REAL NOT NULL,
        snf_base REAL DEFAULT 8.5,
        snf_rate_per_point REAL DEFAULT 0,
        lr_base REAL DEFAULT 28.0,
        lr_rate_per_point REAL DEFAULT 0,
        date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 4. Milk Entries Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS milk_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        manual_name TEXT,
        entry_date TEXT NOT NULL,
        shift TEXT NOT NULL,
        litre REAL NOT NULL,
        fat REAL NOT NULL,
        snf REAL,
        lr REAL,
        rate_applied REAL NOT NULL,
        total_amount REAL NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers (id))''')

    # ========== ✅ NEW: Biometric Credentials Table (Fingerprint/WebAuthn) ==========
    cursor.execute('''CREATE TABLE IF NOT EXISTS biometric_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        credential_id TEXT NOT NULL UNIQUE,
        public_key TEXT NOT NULL,
        sign_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # --- Column Missing Check (Updates) ---
    _add_column_if_missing(cursor, 'customers', 'date_added', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    _add_column_if_missing(cursor, 'rates', 'snf_base', 'REAL DEFAULT 8.5')
    _add_column_if_missing(cursor, 'rates', 'snf_rate_per_point', 'REAL DEFAULT 0')
    _add_column_if_missing(cursor, 'rates', 'lr_base', 'REAL DEFAULT 28.0')
    _add_column_if_missing(cursor, 'rates', 'lr_rate_per_point', 'REAL DEFAULT 0')
    _add_column_if_missing(cursor, 'rates', 'date_updated', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    _add_column_if_missing(cursor, 'milk_entries', 'manual_name', 'TEXT')
    _add_column_if_missing(cursor, 'users', 'profile_pic', "TEXT DEFAULT 'default.png'")
    

    # Default Admin Check
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', hashed_pw, 'admin'),
        )

    # Default Rates Check
    cursor.execute('SELECT id FROM rates LIMIT 1')
    if not cursor.fetchone():
        cursor.execute(
            '''INSERT INTO rates
               (base_rate, fat_base, fat_rate_per_point, snf_base, snf_rate_per_point, lr_base, lr_rate_per_point)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (80.0, 6.0, 5.0, 8.5, 0.0, 28.0, 0.0),
        )

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print('Database ready:', DB_PATH)