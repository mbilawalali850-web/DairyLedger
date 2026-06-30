import os
import sqlite3
from functools import wraps
from flask import session, redirect, url_for, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'dairy_khata.db')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def get_current_rates(conn):
    row = conn.execute(
        'SELECT * FROM rates ORDER BY id DESC LIMIT 1'
    ).fetchone()
    if not row:
        return {
            'base_rate': 80.0,
            'fat_base': 6.0,
            'fat_rate_per_point': 5.0,
            'snf_base': 8.5,
            'snf_rate_per_point': 0.0,
            'lr_base': 28.0,
            'lr_rate_per_point': 0.0,
        }
    return dict(row)


def calculate_rate(fat, snf, lr, rates):
    """Final Rate = base + (fat - fat_base) * fat_pt + SNF/LR adjustments."""
    rate = float(rates['base_rate'])
    rate += (float(fat) - float(rates['fat_base'])) * float(rates['fat_rate_per_point'])
    snf_base = rates.get('snf_base')
    if snf_base is not None and rates.get('snf_rate_per_point'):
        rate += (float(snf or 0) - float(snf_base)) * float(rates['snf_rate_per_point'])
    lr_base = rates.get('lr_base')
    if lr_base is not None and rates.get('lr_rate_per_point'):
        rate += (float(lr or 0) - float(lr_base)) * float(rates['lr_rate_per_point'])
    return round(max(rate, 0), 2)


def validate_fat(fat):
    try:
        f = float(fat)
    except (TypeError, ValueError):
        return False, 'Fat is required'
    if f < 0 or f > 12:
        return False, 'Fat must be between 0 to 12'
    return True, f


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Only admin can access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped
