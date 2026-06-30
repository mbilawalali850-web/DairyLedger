import io
import os
import shutil
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, session, jsonify
from flask import send_file, request, flash, redirect, url_for

import pandas as pd
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import init_db
from helpers import (
    BASE_DIR,
    admin_required,
    calculate_rate,
    get_current_rates,
    get_db_connection,
    login_required,
    validate_fat,
)
from translations import languages
app = Flask(__name__)

PROFILE_PIC_DEFAULT = 'default.png'
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'profile_pics')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def profile_pic_filename(user_or_pic):
    """Return stored filename or None if default / missing."""
    if user_or_pic is None:
        return None
    if isinstance(user_or_pic, str):
        pic = user_or_pic
    elif hasattr(user_or_pic, 'keys') and 'profile_pic' in user_or_pic.keys():
        pic = user_or_pic['profile_pic']
    else:
        return None
    if not pic or pic == PROFILE_PIC_DEFAULT:
        return None
    return pic


def profile_pic_static_path(pic):
    """Relative path under static/ for url_for, or None for default icon."""
    if pic is None:
        return None
    if hasattr(pic, 'keys'):
        name = profile_pic_filename(pic)
    else:
        name = pic if pic and pic != PROFILE_PIC_DEFAULT else None
    if not name:
        return None
    full = os.path.join(UPLOAD_FOLDER, name)
    if os.path.isfile(full):
        return f'uploads/profile_pics/{name}'
    return None

import webauthn
from webauthn.helpers.structs import RegistrationCredential, AuthenticationCredential

# app = Flask(__name__)
app.secret_key = "aapki_secret_key"

RP_NAME = "Dairy Khata"
RP_ID = "localhost"  # Production mein aapki domain name aayegi (e.g., "dairykhata.com")
ORIGIN = "http://localhost:5000"

from flask import jsonify, request, session, url_for

# 1. Challenge/Options dene wala route (Pehla Fetch yahan aayega)
@app.route('/login-biometric-options', methods=['POST'])
def login_biometric_options():
    data = request.get_json() or {}
    username = data.get('username')
    
    if not username:
        return jsonify({"error": "Username zaroori hai!"}), 400
        
    # Yahan check karein ke kya user database me maujood hai
    # (Abhi ke liye hum sirf challenge options ka structure bhej rahe hain)
    
    # ⚠️ Yeh WebAuthn standard options hote hain jo biometric prompt kholte hain
    options = {
        "challenge": " some-random-secure-challenge-string-from-backend", # Base64 format me hona chahiye
        "timeout": 60000,
        "allowCredentials": [], # User ke registered fingerprints ki list
        "userVerification": "preferred"
    }
    
    return jsonify(options)


# 2. Fingerprint Verify karne wala route (Doosra Fetch yahan aayega)
@app.route('/verify-biometric-login', methods=['POST'])
def verify_biometric_login():
    credential = request.get_json()
    
    # Yahan aapka signature verification ka actual logic aayega
    # Agar match ho jaye toh user ko login karwaein:
    
    # Dummy success login logic testing ke liye:
    success = True 
    
    if success:
        # Session set karein jaise aam login me karte hain
        session['username'] = "Admin"  # Ya dynamic username
        session['role'] = "admin"
        
        return jsonify({
            "status": "success",
            "redirect": url_for('dashboard') # Dashboard par redirect karne ke liye
        })
    else:
        return jsonify({
            "status": "failed",
            "error": "Fingerprint verification fail ho gayi."
        }), 400


# --- PROFILE ROUTE (fingerprint action + existing change_password logic) ---
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        fingerprint_action = request.form.get('fingerprint_action', '')

        # --- Fingerprint remove ---
        if fingerprint_action == 'remove':
            conn.execute(
                'UPDATE users SET fingerprint_credential = NULL, fingerprint_enrolled = 0 WHERE id = ?',
                (session['user_id'],)
            )
            conn.commit()
            conn.close()
            flash('Fingerprint hata diya gaya.', 'info')
            return redirect(url_for('profile'))

    # --- Username update ---
    new_username_input = (request.form.get('new_username') or '').strip()
    old_pass = request.form.get('old_password', '')
    new_pass = request.form.get('new_password', '')
    confirm_pass = request.form.get('confirm_password', '')

    if not check_password_hash(user['password_hash'], old_pass):
        flash("Incorrect current password!", "danger")
        conn.close()
        return redirect(url_for('profile'))

    if new_username_input and new_username_input != user['username']:
        try:
            # Direct update ki koshish karein
            conn.execute('UPDATE users SET username = ? WHERE id = ?',
                        (new_username_input, session['user_id']))
            session['username'] = new_username_input
        except Exception as e:
            # Agar database level par UNIQUE constraint hit hoga, toh error crash nahi karega
            # Aur user ko agay jaane dega bina error ke (ya aap yahan koi soft warning de sakte hain)
            pass 

    if new_pass:
        if new_pass == confirm_pass:
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                        (generate_password_hash(new_pass), session['user_id']))
        else:
            flash("Passwords do not match!", "danger")
            conn.close()
            return redirect(url_for('profile'))

        # --- Profile picture ---
        file = request.files.get('profile_pic')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(
                f"user_{session['user_id']}_{int(datetime.now().timestamp())}.{ext}"
            )
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            old_pic = profile_pic_filename(user)
            if old_pic:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_pic)
                if os.path.isfile(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass
            conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?',
                         (filename, session['user_id']))
            session['profile_pic'] = filename

        conn.commit()
        conn.close()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('dashboard'))

    # --- GET ---
    conn.close()
    pic_path = profile_pic_static_path(user)
    profile_pic_url = url_for('static', filename=pic_path) if pic_path else None
    fp_enrolled = user['fingerprint_enrolled'] if 'fingerprint_enrolled' in user.keys() else False

    return render_template(
        'profile.html',
        user=user,
        current_username=user['username'],
        profile_pic_url=profile_pic_url,
        fingerprint_enrolled=bool(fp_enrolled),
    )

@app.context_processor
def inject_profile_helpers():
    def user_profile_pic_url():
        path = profile_pic_static_path(session.get('profile_pic'))
        return url_for('static', filename=path) if path else None

    return {
        'user_profile_pic_url': user_profile_pic_url,
        'profile_pic_default': PROFILE_PIC_DEFAULT,
        't': t(),
    }


def t():
    lang = session.get('lang', 'en')
    return languages.get(lang, languages['en'])


@app.errorhandler(Exception)
def handle_exception(e):
    # Generic error handler returning JSON for AJAX/API calls
    try:
        return jsonify({'error': str(e)}), 500
    except Exception:
        return 'Internal Server Error', 500


@app.before_request
def set_lang():
    if 'lang' not in session:
        session['lang'] = 'en'


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            # Login ke waqt pic session mein save kar rahe hain
            session['profile_pic'] = (
                user['profile_pic'] if 'profile_pic' in user.keys() else PROFILE_PIC_DEFAULT
            )
            return redirect(url_for('dashboard'))
        flash('Invalid Username or Password!', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


@app.route('/switch_lang')
@login_required
def change_lang():
    if session.get('lang') == 'ur':
        session['lang'] = 'en'
    else:
        session['lang'] = 'ur'
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        new_username_input = (request.form.get('new_username') or '').strip()
        old_pass = request.form.get('old_password')
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')
        user_id = user['id']

        # 1. Purana password verify karna zaroori hai
        if not check_password_hash(user['password_hash'], old_pass):
            flash("Incorrect current password!", "danger")
            conn.close()
            return redirect(url_for('change_password'))

        # 2. Username update — blank field = keep current; filled = new name
        if new_username_input:
            if new_username_input != user['username']:
                taken = conn.execute(
                    'SELECT username FROM users WHERE LOWER(username) = LOWER(?) AND id != ?',
                    (new_username_input, user_id),
                ).fetchone()
                if taken:
                    flash(
                        f"Username '{new_username_input}' is already used by another account. "
                        f"Your current login is '{user['username']}'. Try a different name.",
                        "danger",
                    )
                    conn.close()
                    return redirect(url_for('change_password'))
                conn.execute(
                    'UPDATE users SET username = ? WHERE id = ?',
                    (new_username_input, user_id),
                )
                session['username'] = new_username_input
        elif request.form.get('change_username') == '1':
            flash("Please enter a new username or leave the field empty to keep your current one.", "warning")
            conn.close()
            return redirect(url_for('change_password'))

        # 3. Password Update Logic
        if new_pass:
            if new_pass == confirm_pass:
                new_hashed = generate_password_hash(new_pass)
                conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hashed, session['user_id']))
            else:
                flash("Passwords do not match!", "danger")
                conn.close()
                return redirect(url_for('change_password'))

        # 4. Profile picture upload
        file = request.files.get('profile_pic')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"user_{session['user_id']}_{int(datetime.now().timestamp())}.{ext}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            old_pic = profile_pic_filename(user)
            if old_pic:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_pic)
                if os.path.isfile(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass
            conn.execute(
                'UPDATE users SET profile_pic = ? WHERE id = ?',
                (filename, session['user_id']),
            )
            session['profile_pic'] = filename

        conn.commit()
        conn.close()
        flash("Profile updated successfully!", "success")


        return redirect(url_for('dashboard'))

    conn.close()
    pic_path = profile_pic_static_path(user)
    profile_pic_url = url_for('static', filename=pic_path) if pic_path else None
    return render_template(
        'change_password.html',
        user=user,
        current_username=user['username'],
        profile_pic_url=profile_pic_url,
    )


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    stats = conn.execute(
        '''SELECT COALESCE(SUM(litre), 0) as total_milk,
                  COALESCE(SUM(total_amount), 0) as total_cash
           FROM milk_entries WHERE entry_date = ?''',
        (today,),
    ).fetchone()
    shift_stats = conn.execute(
        '''SELECT shift, COALESCE(SUM(litre), 0) as s_milk
           FROM milk_entries WHERE entry_date = ? GROUP BY shift''',
        (today,),
    ).fetchall()
    conn.close()
    return render_template(
        'dashboard.html',
        stats=stats,
        shift_stats=shift_stats,
        t=t(),
        is_admin=session.get('role') == 'admin',
    )


@app.route('/rates', methods=['GET', 'POST'])
@admin_required
def rates():
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute(
            '''INSERT INTO rates
               (base_rate, fat_base, fat_rate_per_point, snf_base, snf_rate_per_point, lr_base, lr_rate_per_point)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (
                float(request.form['base_rate']),
                float(request.form['fat_base']),
                float(request.form['fat_rate_per_point']),
                float(request.form.get('snf_base') or 8.5),
                float(request.form.get('snf_rate_per_point') or 0),
                float(request.form.get('lr_base') or 28),
                float(request.form.get('lr_rate_per_point') or 0),
            ),
        )
        conn.commit()
        flash('Rates updated successfully.', 'success')
    rates_row = get_current_rates(conn)
    conn.close()
    return render_template('rates.html', rates=rates_row, t=t())


@app.route('/api/rates')
@login_required
def api_rates():
    conn = get_db_connection()
    rates = get_current_rates(conn)
    conn.close()
    return jsonify(rates)


@app.route('/api/calculate-rate', methods=['POST'])
@login_required
def api_calculate_rate():
    data = request.get_json(silent=True) or {}
    ok, fat_val = validate_fat(data.get('fat'))
    if not ok:
        return jsonify({'error': fat_val}), 400
    conn = get_db_connection()
    rates = get_current_rates(conn)
    conn.close()
    rate = calculate_rate(
        fat_val,
        data.get('snf') or 0,
        data.get('lr') or 0,
        rates,
    )
    litre = float(data.get('litre') or 0)
    return jsonify({'rate': rate, 'total': round(litre * rate, 2)})


@app.route('/customers')
@login_required
def customer_list():
    q = request.args.get('q', '').strip()
    conn = get_db_connection()
    if q:
        like = f'%{q}%'
        customers = conn.execute(
            '''SELECT * FROM customers
               WHERE name LIKE ? OR code LIKE ? OR phone LIKE ?
               ORDER BY name''',
            (like, like, like),
        ).fetchall()
    else:
        customers = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
    conn.close()
    return render_template('customers.html', customers=customers, q=q, t=t())


@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        code = request.form['code'].strip()
        name = request.form['name'].strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        if not code or not name:
            flash('Code and name are required.', 'danger')
            return render_template('add_customer.html', t=t())
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO customers (code, name, phone, address) VALUES (?, ?, ?, ?)',
                (code, name, phone, address),
            )
            conn.commit()
            flash('Customer added!', 'success')
            conn.close()
            return redirect(url_for('customer_list'))
        except sqlite3.IntegrityError:
            flash('Error: Code already exists!', 'danger')
        finally:
            conn.close()
    return render_template('add_customer.html', t=t())


@app.route('/customers/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(cid):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (cid,)).fetchone()
    if not customer:
        conn.close()
        flash('Customer not found.', 'danger')
        return redirect(url_for('customer_list'))
    if request.method == 'POST':
        try:
            conn.execute(
                '''UPDATE customers SET code=?, name=?, phone=?, address=?
                   WHERE id=?''',
                (
                    request.form['code'].strip(),
                    request.form['name'].strip(),
                    request.form.get('phone', '').strip(),
                    request.form.get('address', '').strip(),
                    cid,
                ),
            )
            conn.commit()
            flash('Customer updated.', 'success')
            conn.close()
            return redirect(url_for('customer_list'))
        except sqlite3.IntegrityError:
            flash('Code already used by another customer.', 'danger')
    conn.close()
    return render_template('edit_customer.html', customer=customer, t=t())


@app.route('/customers/<int:cid>/delete', methods=['POST'])
@login_required
def delete_customer(cid):
    conn = get_db_connection()
    entries = conn.execute(
        'SELECT COUNT(*) FROM milk_entries WHERE customer_id = ?', (cid,)
    ).fetchone()[0]
    if entries > 0:
        conn.close()
        flash('Cannot delete: customer has milk entries.', 'danger')
        return redirect(url_for('customer_list'))
    conn.execute('DELETE FROM customers WHERE id = ?', (cid,))
    conn.commit()
    conn.close()
    flash('Customer deleted.', 'success')
    return redirect(url_for('customer_list'))


@app.route('/entry/add', methods=['GET', 'POST'])
@login_required
def add_entry():
    conn = get_db_connection()
    customers = conn.execute('SELECT id, code, name FROM customers ORDER BY name').fetchall()
    rates = get_current_rates(conn)
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    current_shift = 'Morning' if 4 <= now.hour < 16 else 'Evening'
    is_admin = session.get('role') == 'admin'

    if request.method == 'POST':
        ok, fat_val = validate_fat(request.form.get('fat'))
        if not ok:
            flash(fat_val, 'danger')
        else:
            try:
                litre = float(request.form.get('litre', 0))
                if litre <= 0:
                    raise ValueError('Litre must be greater than 0')
                c_id = request.form.get('customer_id') or None
                m_name = request.form.get('manual_customer_name', '').strip()
                if not c_id and not m_name:
                    raise ValueError('Select customer or enter manual name')
                snf = float(request.form.get('snf') or 0)
                lr = float(request.form.get('lr') or 0)
                if is_admin and request.form.get('rate'):
                    rate = float(request.form['rate'])
                else:
                    rate = calculate_rate(fat_val, snf, lr, rates)
                total = round(litre * rate, 2)
                conn.execute(
                    '''INSERT INTO milk_entries
                       (customer_id, manual_name, entry_date, shift, litre, fat, snf, lr, rate_applied, total_amount)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        c_id,
                        m_name or None,
                        request.form['date'],
                        request.form['shift'],
                        litre,
                        fat_val,
                        snf,
                        lr,
                        rate,
                        total,
                    ),
                )
                conn.commit()
                flash('Entry saved successfully!', 'success')
                conn.close()
                return redirect(url_for('add_entry'))
            except ValueError as e:
                flash(str(e), 'danger')
            except Exception as e:
                flash(f'Error saving data: {e}', 'danger')

    today_entries = conn.execute(
        '''SELECT e.*, c.name as customer_name, c.code as customer_code
           FROM milk_entries e
           LEFT JOIN customers c ON e.customer_id = c.id
           WHERE e.entry_date = ? ORDER BY e.id DESC''',
        (current_date,),
    ).fetchall()
    conn.close()
    return render_template(
        'add_entry.html',
        customers=customers,
        current_date=current_date,
        current_shift=current_shift,
        rates=rates,
        today_entries=today_entries,
        is_admin=is_admin,
        t=t(),
    )


@app.route('/entry/<int:eid>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(eid):
    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM milk_entries WHERE id = ?', (eid,)).fetchone()
    if not entry:
        conn.close()
        flash('Entry not found.', 'danger')
        return redirect(url_for('add_entry'))
    today = datetime.now().strftime('%Y-%m-%d')
    if entry['entry_date'] != today:
        conn.close()
        flash('Only same-day entries can be edited.', 'danger')
        return redirect(url_for('add_entry'))
    rates = get_current_rates(conn)
    customers = conn.execute('SELECT id, code, name FROM customers ORDER BY name').fetchall()
    is_admin = session.get('role') == 'admin'

    if request.method == 'POST':
        ok, fat_val = validate_fat(request.form.get('fat'))
        if not ok:
            flash(fat_val, 'danger')
        else:
            try:
                litre = float(request.form.get('litre', 0))
                snf = float(request.form.get('snf') or 0)
                lr = float(request.form.get('lr') or 0)
                rate = (
                    float(request.form['rate'])
                    if is_admin and request.form.get('rate')
                    else calculate_rate(fat_val, snf, lr, rates)
                )
                total = round(litre * rate, 2)
                conn.execute(
                    '''UPDATE milk_entries SET customer_id=?, manual_name=?, shift=?, litre=?, fat=?,
                       snf=?, lr=?, rate_applied=?, total_amount=? WHERE id=?''',
                    (
                        request.form.get('customer_id') or None,
                        request.form.get('manual_customer_name') or None,
                        request.form['shift'],
                        litre,
                        fat_val,
                        snf,
                        lr,
                        rate,
                        total,
                        eid,
                    ),
                )
                conn.commit()
                conn.close()
                flash('Entry updated.', 'success')
                return redirect(url_for('add_entry'))
            except Exception as e:
                flash(str(e), 'danger')
    conn.close()
    return render_template(
        'edit_entry.html',
        entry=entry,
        customers=customers,
        rates=rates,
        is_admin=is_admin,
        t=t(),
    )


@app.route('/entry/<int:eid>/delete', methods=['POST'])
@login_required
def delete_entry(eid):
    conn = get_db_connection()
    entry = conn.execute('SELECT entry_date FROM milk_entries WHERE id = ?', (eid,)).fetchone()
    if not entry:
        conn.close()
        flash('Entry not found.', 'danger')
        return redirect(url_for('add_entry'))
    today = datetime.now().strftime('%Y-%m-%d')
    if entry['entry_date'] != today:
        conn.close()
        flash('Only same-day entries can be deleted.', 'danger')
        return redirect(url_for('add_entry'))
    conn.execute('DELETE FROM milk_entries WHERE id = ?', (eid,))
    conn.commit()
    conn.close()
    flash('Entry deleted.', 'success')
    return redirect(url_for('add_entry'))


@app.route('/customer/<int:id>/ledger')
@login_required
def customer_ledger(id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (id,)).fetchone()
    if not customer:
        conn.close()
        flash('Customer not found.', 'danger')
        return redirect(url_for('customer_list'))
    query = 'SELECT * FROM milk_entries WHERE customer_id = ?'
    params = [id]
    if start_date and end_date:
        query += ' AND entry_date BETWEEN ? AND ?'
        params.extend([start_date, end_date])
    query += ' ORDER BY entry_date DESC, shift DESC'
    entries = conn.execute(query, params).fetchall()
    summary = conn.execute(
        f'''SELECT COALESCE(SUM(litre), 0) as total_litre,
                   COALESCE(AVG(fat), 0) as avg_fat,
                   COALESCE(SUM(total_amount), 0) as total_bill
            FROM milk_entries WHERE customer_id = ?'''
        + (' AND entry_date BETWEEN ? AND ?' if start_date and end_date else ''),
        params,
    ).fetchone()
    conn.close()
    return render_template(
        'ledger.html',
        customer=customer,
        entries=entries,
        summary=summary,
        sd=start_date,
        ed=end_date,
        t=t(),
    )


@app.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    conn = get_db_connection()
    customers = conn.execute('SELECT id, code, name FROM customers ORDER BY name').fetchall()
    today = datetime.now().strftime('%Y-%m-%d')
    report_date = request.args.get('date', today)
    start_date = request.args.get('start_date', report_date)
    end_date = request.args.get('end_date', report_date)
    customer_id = request.args.get('customer_id')

    daily = conn.execute(
        '''SELECT COALESCE(SUM(litre), 0) as total_milk,
                  COALESCE(SUM(total_amount), 0) as total_value,
                  COALESCE(AVG(fat), 0) as avg_fat
           FROM milk_entries WHERE entry_date = ?''',
        (report_date,),
    ).fetchone()

    bill_entries = []
    bill_summary = None
    if customer_id:
        params = [customer_id, start_date, end_date]
        bill_entries = conn.execute(
            '''SELECT e.*, c.name, c.code FROM milk_entries e
               JOIN customers c ON e.customer_id = c.id
               WHERE e.customer_id = ? AND e.entry_date BETWEEN ? AND ?
               ORDER BY e.entry_date, e.shift''',
            params,
        ).fetchall()
        bill_summary = conn.execute(
            '''SELECT COALESCE(SUM(litre), 0) as total_litre,
                      COALESCE(AVG(fat), 0) as avg_fat,
                      COALESCE(SUM(total_amount), 0) as total_bill
               FROM milk_entries
               WHERE customer_id = ? AND entry_date BETWEEN ? AND ?''',
            params,
        ).fetchone()
    conn.close()
    return render_template(
        'reports.html',
        customers=customers,
        daily=daily,
        report_date=report_date,
        start_date=start_date,
        end_date=end_date,
        customer_id=customer_id,
        bill_entries=bill_entries,
        bill_summary=bill_summary,
        t=t(),
    )

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Agar aapko profile settings ka data database se laana hai to yahan fetch kar sakte hain
    return render_template('settings.html', t=t())

@app.route('/export/excel')
@login_required
def export_excel():
    customer_id = request.args.get('customer_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    conn = get_db_connection()
    query = '''
        SELECT e.entry_date as Date, e.shift as Shift,
               COALESCE(c.code, '') as Customer_Code,
               COALESCE(c.name, e.manual_name, '') as Customer_Name,
               e.litre as Liters, e.fat as Fat, e.lr as LR,
               e.snf as SNF, e.rate_applied as Rate, e.total_amount as Total_Amount
        FROM milk_entries e
        LEFT JOIN customers c ON e.customer_id = c.id
        WHERE 1=1
    '''
    params = []
    if customer_id:
        query += ' AND e.customer_id = ?'
        params.append(customer_id)
    if start_date and end_date:
        query += ' AND e.entry_date BETWEEN ? AND ?'
        params.extend([start_date, end_date])
    query += ' ORDER BY e.entry_date DESC'
    df = pd.read_sql_query(query, conn, params=params or None)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Milk_Collection')
        ws = writer.sheets['Milk_Collection']
        for col in ws.columns:
            letter = col[0].column_letter
            max_len = max((len(str(cell.value or '')) for cell in col), default=10)
            ws.column_dimensions[letter].width = min(max_len + 2, 40)
    output.seek(0)
    fname = f'Milk_Report_{datetime.now().strftime("%Y-%m-%d")}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=fname,
    )


DB_FILE = 'dairy_khata.db'  # ⚠️ Apni asli database file ka naam yahan likhein

# 1. Backup Download Karne Ka Route
@app.route('/backup/download')
@login_required
def download_backup():
    if session.get('role') != 'admin':
        flash("You are not authorized!", "danger")
        return redirect(url_for('dashboard'))
        
    if os.path.exists(DB_FILE):
        # Yeh user ko direct .db file download karwa dega
        return send_file(DB_FILE, as_attachment=True, download_name=f"backup_{datetime.now().strftime('%Y%md_%H%M%S')}.db")
    else:
        flash("Database file not found!", "danger")
        return redirect(url_for('dashboard'))

# 2. Backup Restore (Upload) Karne Ka Route
@app.route('/backup/restore', methods=['POST'])
@login_required
def restore_backup():
    if session.get('role') != 'admin':
        flash("You are not authorized!", "danger")
        return redirect(url_for('dashboard'))

    if 'backup_file' not in request.files:
        flash("No file part!", "danger")
        return redirect(url_for('backup_restore'))

    file = request.files['backup_file']
    if file.filename == '':
        flash("No selected file!", "danger")
        return redirect(url_for('backup_restore'))

    if file and file.filename.endswith('.db'):
        try:
            # Purani file ka temporary backup banayein safety ke liye
            if os.path.exists(DB_FILE):
                shutil.copy(DB_FILE, DB_FILE + '.tmp')
            
            # Nayi file ko save kar dein asli database ki jagah
            file.save(DB_FILE)
            
            # Agar sab sahi raha toh tmp file delete kar dein
            if os.path.exists(DB_FILE + '.tmp'):
                os.remove(DB_FILE + '.tmp')
                
            flash("Database restored successfully!", "success")
        except Exception as e:
            # Agar koi error aaye toh purani file wapas le aayein
            if os.path.exists(DB_FILE + '.tmp'):
                shutil.move(DB_FILE + '.tmp', DB_FILE)
            flash(f"Error restoring backup: {str(e)}", "danger")
    else:
        flash("Invalid file format! Only .db files are allowed.", "danger")

    return redirect(url_for('backup_restore'))

# 3. Backup Page Render Karne Ka Route
@app.route('/backup-panel')
@login_required
def backup_restore():
    if session.get('role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('dashboard'))
    return render_template('backup.html', t=t())


if __name__ == '__main__':
    app.run(debug=True, port=5000)