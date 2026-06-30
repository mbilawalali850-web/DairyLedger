-- Table for Users (Admin/Helper)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'helper' -- 'admin' or 'helper'
);

-- Table for Customers
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for Rates (Settings)
CREATE TABLE IF NOT EXISTS rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_rate REAL NOT NULL,
    fat_base REAL NOT NULL,
    fat_rate_per_point REAL NOT NULL,
    snf_base REAL DEFAULT 8.5,
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for Milk Entries (The Core)
CREATE TABLE IF NOT EXISTS milk_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    entry_date DATE NOT NULL,
    shift TEXT CHECK(shift IN ('Morning', 'Evening')),
    litre REAL NOT NULL,
    fat REAL NOT NULL,
    snf REAL,
    lr REAL,
    rate_applied REAL NOT NULL,
    total_amount REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);