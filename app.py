import os
import smtplib
import base64
import re
import secrets
import json # NEW
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, send_from_directory, make_response, redirect
from flask_cors import CORS
import mysql.connector
from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()

# Configure Gemini API
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def generate_otp(length=6):
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))

def send_otp_email(to_email, otp):
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    if not username or not password:
        print("[EMAIL ERROR] MAIL_USERNAME or MAIL_PASSWORD missing in .env")
        return False
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Your BankEase OTP'
    msg['From']    = f'BankEase <{username}>'
    msg['To']      = to_email
    html_body = f"""
    <div style="font-family:Arial,sans-serif;background:#f3f4f6;padding:40px 20px">
      <div style="max-width:460px;margin:auto;background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,.09)">
        <div style="background:linear-gradient(135deg,#4f46e5,#6366f1);padding:26px;text-align:center;color:#fff">
          <h1 style="margin:0;font-size:24px;font-weight:800">BankEase</h1>
          <p style="margin:4px 0 0;opacity:.8;font-size:13px">Secure Login Verification</p>
        </div>
        <div style="padding:30px;text-align:center">
          <p style="color:#374151;font-size:15px;margin-bottom:20px">Your One-Time Password:</p>
          <div style="background:#eef2ff;border:2px dashed #818cf8;border-radius:12px;padding:20px;margin-bottom:20px">
            <span style="font-size:40px;font-weight:900;color:#4338ca;letter-spacing:12px;display:block">{otp}</span>
          </div>
          <p style="color:#9ca3af;font-size:13px">Valid for <b>5 minutes</b> only.</p>
          <p style="color:#9ca3af;font-size:12px">Never share this OTP with anyone.</p>
        </div>
        <div style="background:#f9fafb;padding:14px;text-align:center;border-top:1px solid #e5e7eb">
          <p style="color:#9ca3af;font-size:11px;margin:0">&copy; 2026 BankEase. All rights reserved.</p>
        </div>
      </div>
    </div>"""
    msg.attach(MIMEText(html_body, 'html'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(username, password)
            server.sendmail(username, to_email, msg.as_string())
        print(f"[EMAIL] OTP sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL ERROR] Auth failed. Check MAIL_PASSWORD in .env")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def require_login():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    return None

def require_manager():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    if session.get('role') != 'manager':
        return jsonify({"success": False, "message": "Access denied - Manager only"}), 403
    return None

# ─── Static Routes ────────────────────────────────────────────────────────────
@app.route('/')
def serve_index():
    r = make_response(send_from_directory('.', 'index.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/login.html')
def serve_login():
    r = make_response(send_from_directory('.', 'login.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/dashboard.html')
def serve_dashboard():
    if session.get('role') == 'manager':
        return make_response(redirect('/manager.html'))
    r = make_response(send_from_directory('.', 'dashboard.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/profile.html')
def serve_profile():
    r = make_response(send_from_directory('.', 'profile.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/chatbot.html')
def serve_chatbot():
    r = make_response(send_from_directory('.', 'chatbot.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/manager.html')
def serve_manager():
    r = make_response(send_from_directory('.', 'manager.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/statement.html')
def serve_statement():
    r = make_response(send_from_directory('.', 'statement.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/support.html')
def serve_support():
    if session.get('role') == 'manager':
        if not request.args.get('ticket_id'):
            return make_response(redirect('/manager.html'))
    r = make_response(send_from_directory('.', 'support.html'))
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return r

@app.route('/test-email')
def test_email():
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as s:
            s.starttls()
            s.login(username, password)
        return jsonify({"success": True, "message": f"SMTP OK for {username}"})
    except smtplib.SMTPAuthenticationError as e:
        return jsonify({"success": False, "message": f"Auth failed: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ─── Register ─────────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        pin      = data.get('pin')
        full_name = data.get('full_name')
        phone    = data.get('phone')
        dob      = data.get('dob')
        aadhaar  = data.get('aadhaar')
        pan      = data.get('pan')
        address  = data.get('address')
        if not all([username, password, pin, full_name, phone, dob, aadhaar, pan, address]):
            return jsonify({"success": False, "message": "All fields required"}), 400
        if len(pin) != 4:
            return jsonify({"success": False, "message": "PIN must be 4 digits"}), 400
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Username already registered"}), 400
        cursor.execute(
            "INSERT INTO users (username, password, pin, role, is_active, full_name, phone, dob, aadhaar, pan, address) VALUES (%s, %s, %s, 'user', 1, %s, %s, %s, %s, %s, %s)",
            (username, password, pin, full_name, phone, dob, aadhaar, pan, address)
        )
        conn.commit()
        user_id = cursor.lastrowid
        account_number = f"ACCT-{user_id}-{secrets.randbelow(9000)+1000}"
        cursor.execute(
            "INSERT INTO accounts (user_id, account_number, balance, is_frozen) VALUES (%s, %s, 10000.00, 0)",
            (user_id, account_number)
        )
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Registration successful", "account_id": account_number}), 201
    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Login ────────────────────────────────────────────────────────────────────
login_attempts = {}

@app.route('/api/login-start', methods=['POST'])
def login_start():
    try:
        data = request.json
        username = data.get('username') or data.get('email')
        password = data.get('password')
        role     = data.get('role', 'user')
        if not username:
            return jsonify({"success": False, "message": "Email/Username required"}), 400
        now = datetime.now()
        if username not in login_attempts:
            login_attempts[username] = []
        recent = [t for t in login_attempts[username] if now - t < timedelta(minutes=10)]
        login_attempts[username] = recent
        if len(recent) >= 5:
            return jsonify({"success": False, "message": "Too many attempts. Wait 10 minutes."}), 429
        login_attempts[username].append(now)
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        query = "SELECT id, username, password, role FROM users WHERE username = %s AND is_active = 1"
        params = [username]
        if role:
            query += " AND role = %s"
            params.append(role)
        cursor.execute(query, tuple(params))
        user = cursor.fetchone()
        if not user:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Invalid credentials"}), 401
        if role == 'manager' and password:
            if user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                cursor.close(); conn.close()
                return jsonify({
                    "success": True, "requires_otp": False,
                    "user": {"id": user['id'], "username": user['username'], "role": user['role']}
                }), 200
            else:
                cursor.close(); conn.close()
                return jsonify({"success": False, "message": "Incorrect password"}), 401
        otp = generate_otp()
        expires = datetime.now() + timedelta(minutes=5)
        cursor.execute("UPDATE users SET otp_code = %s, otp_expires_at = %s WHERE id = %s", (otp, expires, user['id']))
        conn.commit()
        email_sent = send_otp_email(username, otp)
        print(f"DEBUG OTP for {username}: {otp}")
        cursor.close(); conn.close()
        return jsonify({
            "success": True,
            "message": "OTP sent to your email" if email_sent else "OTP generated (check terminal)",
            "user_id": user['id']
        }), 200
    except Exception as e:
        print(f"Login-start error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/login-verify', methods=['POST'])
def login_verify():
    try:
        data = request.json
        user_id = data.get('user_id')
        otp     = data.get('otp')
        if not user_id or not otp:
            return jsonify({"success": False, "message": "User ID and OTP required"}), 400
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, full_name, role, phone, dob, aadhaar, pan, address, otp_code, otp_expires_at FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        if not user:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "User not found"}), 404
        if not user['otp_code'] or not user['otp_expires_at']:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "OTP not found or already used"}), 400
        if datetime.now() > user['otp_expires_at']:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "OTP has expired"}), 400
        if user['otp_code'] != otp:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Invalid OTP"}), 401
        cursor.execute("UPDATE users SET otp_code = NULL, otp_expires_at = NULL WHERE id = %s", (user['id'],))
        conn.commit()
        cursor.execute("SELECT account_number, balance FROM accounts WHERE user_id = %s", (user['id'],))
        acc = cursor.fetchone()
        cursor.close(); conn.close()
        session['user_id'] = user['id']
        session['role']    = user.get('role', 'user')
        return jsonify({
            "success": True, "message": "Login successful",
            "user": {
                "id": user['id'], "username": user['username'],
                "full_name": user.get('full_name') or user['username'],
                "email": user['username'], "phone": user.get('phone'),
                "dob": user.get('dob').isoformat() if user.get('dob') else None,
                "aadhaar": user.get('aadhaar'), "pan": user.get('pan'),
                "address": user.get('address'), "role": user.get('role', 'user'),
                "account_id": acc['account_number'] if acc else 'N/A',
                "balance": float(acc['balance']) if acc and acc['balance'] else 0.0
            }
        }), 200
    except Exception as e:
        print(f"Login-verify error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Profile ──────────────────────────────────────────────────────────────────
@app.route('/api/profile', methods=['GET'])
def get_profile():
    err = require_login()
    if err: return err
    try:
        user_id = session['user_id']
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT u.*, a.account_number, a.balance FROM users u LEFT JOIN accounts a ON u.id = a.user_id WHERE u.id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close(); conn.close()
        if user:
            return jsonify({
                "success": True,
                "user": {
                    "id": user['id'], "username": user['username'],
                    "full_name": user.get('full_name') or user['username'],
                    "email": user['username'], "phone": user.get('phone'),
                    "dob": user.get('dob').isoformat() if user.get('dob') else None,
                    "aadhaar": user.get('aadhaar'), "pan": user.get('pan'),
                    "address": user.get('address'), "role": user.get('role', 'user'),
                    "account_id": user['account_number'] if user['account_number'] else 'N/A',
                    "balance": float(user['balance']) if user['balance'] else 0.0,
                    "profile_image": user.get('profile_image')
                }
            }), 200
        return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    err = require_login()
    if err: return err
    try:
        user_id = session.get('user_id')
        data = request.json
        conn = get_db(); cursor = conn.cursor()
        updates, values = [], []
        fields = ['username','pin','profile_image','full_name','phone','dob','aadhaar','pan','address']
        for f in fields:
            v = data.get(f)
            if v:
                if f == 'pin' and len(v) != 4:
                    cursor.close(); conn.close()
                    return jsonify({"success": False, "message": "PIN must be 4 digits"}), 400
                updates.append(f"{f} = %s"); values.append(v)
        if updates:
            values.append(user_id)
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", tuple(values))
            conn.commit()
        cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Profile updated"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Verify PIN ───────────────────────────────────────────────────────────────
@app.route('/api/verify-pin', methods=['POST'])
def verify_pin():
    err = require_login()
    if err: return err
    try:
        user_id = session.get('user_id')
        pin = request.json.get('pin')
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT u.pin, a.balance FROM users u LEFT JOIN accounts a ON u.id = a.user_id WHERE u.id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close(); conn.close()
        if user and user['pin'] == pin:
            return jsonify({"success": True, "balance": float(user['balance']) if user['balance'] else 0.0}), 200
        return jsonify({"success": False, "message": "Invalid PIN"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Users List ───────────────────────────────────────────────────────────────
@app.route('/api/users', methods=['GET'])
def get_all_users():
    err = require_login()
    if err: return err
    try:
        user_id = session.get('user_id')
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT u.username, a.account_number as account_id FROM users u JOIN accounts a ON u.id = a.user_id WHERE u.id != %s AND u.is_active = 1 LIMIT 20",
            (user_id,)
        )
        users = cursor.fetchall()
        cursor.close(); conn.close()
        return jsonify({"success": True, "users": users}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Transfer ─────────────────────────────────────────────────────────────────
@app.route('/api/transfer', methods=['POST'])
def transfer():
    err = require_login()
    if err: return err
    try:
        user_id = session.get('user_id')
        data = request.json
        recipient_account = data.get('recipient_account')
        amount = float(data.get('amount', 0))
        pin    = data.get('pin')
        camera_image = data.get('camera_image')
        if not all([recipient_account, pin]) or amount <= 0:
            return jsonify({"success": False, "message": "Recipient, amount, and PIN are required"}), 400
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT u.pin, u.username as sender_name, a.id as account_id, a.account_number, a.balance, a.is_frozen FROM users u JOIN accounts a ON u.id = a.user_id WHERE u.id = %s",
            (user_id,)
        )
        sender = cursor.fetchone()
        if not sender:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Account not found"}), 404
        if sender['is_frozen']:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Your account is frozen"}), 403
        if sender['pin'] != pin:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Invalid PIN"}), 401
        if float(sender['balance']) < amount:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Insufficient balance"}), 400
        cursor.execute(
            "SELECT a.*, u.username as recipient_name FROM accounts a JOIN users u ON a.user_id = u.id WHERE a.account_number = %s",
            (recipient_account,)
        )
        recipient = cursor.fetchone()
        if not recipient:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Recipient account not found"}), 404
        if recipient['is_frozen']:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Recipient account is frozen"}), 403
        if recipient.get('is_flagged'):
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Transaction Blocked: Recipient account is flagged."}), 403
        if sender['account_number'] == recipient_account:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Cannot transfer to same account"}), 400
        transaction_photo_path = None
        if camera_image and camera_image != 'skipped':
            try:
                app_root = os.path.dirname(os.path.abspath(__file__))
                folder = os.path.join(app_root, 'static', 'transaction_photos')
                os.makedirs(folder, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                fname = f"txn_{sender['account_id']}_{ts}.jpg"
                fpath = os.path.join(folder, fname)
                image_data = re.sub(r'^data:image/.+;base64,', '', camera_image)
                with open(fpath, 'wb') as f:
                    f.write(base64.b64decode(image_data))
                transaction_photo_path = f"/static/transaction_photos/{fname}"
            except Exception as e:
                print(f"Photo save error: {e}")
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (amount, sender['account_id']))
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount, recipient['id']))
        cursor.execute(
            "INSERT INTO transactions (account_id, type, amount, status, transaction_photo, recipient_account, recipient_name) VALUES (%s, 'transfer-debit', %s, 'success', %s, %s, %s)",
            (sender['account_id'], amount, transaction_photo_path, recipient_account, recipient['recipient_name'])
        )
        cursor.execute(
            "INSERT INTO transactions (account_id, type, amount, status, transaction_photo, recipient_account, recipient_name) VALUES (%s, 'transfer-credit', %s, 'success', %s, %s, %s)",
            (recipient['id'], amount, transaction_photo_path, sender['account_number'], sender['sender_name'])
        )
        conn.commit()
        cursor.execute("SELECT balance FROM accounts WHERE id = %s", (sender['account_id'],))
        new_balance = float(cursor.fetchone()['balance'])
        cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Transfer successful", "new_balance": new_balance, "recipient_name": recipient['recipient_name']}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Transactions ─────────────────────────────────────────────────────────────
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    err = require_login()
    if err: return err
    try:
        user_id = session.get('user_id')
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM accounts WHERE user_id = %s", (user_id,))
        account = cursor.fetchone()
        if not account:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Account not found"}), 404
        cursor.execute("SELECT * FROM transactions WHERE account_id = %s ORDER BY timestamp DESC LIMIT 50", (account['id'],))
        transactions = cursor.fetchall()
        cursor.close(); conn.close()
        formatted = [{
            'id': t['id'], 'type': 'credit' if t['type'] == 'transfer-credit' else 'debit',
            'amount': float(t['amount']), 'recipient_account': t.get('recipient_account'),
            'recipient_name': t.get('recipient_name'), 'status': t['status'],
            'camera_image': t.get('transaction_photo'),
            'created_at': t['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if t['timestamp'] else None
        } for t in transactions]
        return jsonify({"success": True, "transactions": formatted}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Chatbot ──────────────────────────────────────────────────────────────────
@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    err = require_login()
    if err: return err
    try:
        user_id = session.get('user_id')
        data = request.json
        message = data.get('message', '').lower().strip()
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT u.username, u.full_name, a.account_number, a.balance FROM users u LEFT JOIN accounts a ON u.id = a.user_id WHERE u.id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("SELECT id FROM accounts WHERE user_id = %s", (user_id,))
        acc = cursor.fetchone()
        recent_txns = []
        if acc:
            cursor.execute("SELECT type, amount, recipient_name, timestamp FROM transactions WHERE account_id = %s ORDER BY timestamp DESC LIMIT 5", (acc['id'],))
            recent_txns = cursor.fetchall()
        response = generate_smart_response(message, user, recent_txns)
        try:
            cursor.execute("INSERT INTO chat_history (user_id, sender, text) VALUES (%s, 'user', %s)", (user_id, data.get('message', '')))
            cursor.execute("INSERT INTO chat_history (user_id, sender, text) VALUES (%s, 'ai', %s)", (user_id, response['text']))
            conn.commit()
        except: pass
        cursor.close(); conn.close()
        return jsonify({"success": True, "response": response['text'], "action": response.get('action')}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
def generate_smart_response(msg, user, recent_txns):
    name = user.get('full_name') or user.get('username') if user else 'Valued Client'
    acct_num = user.get('account_number', 'N/A') if user else 'N/A'
    
    # Format recent transactions for the AI to read
    tx_str = "No recent transactions."
    if recent_txns:
        tx_list = []
        for t in recent_txns:
            direction = "Received from" if t['type'] == 'transfer-credit' else "Sent to"
            tx_list.append(f"- {direction} {t['recipient_name'] or 'Unknown'} (Rs.{float(t['amount']):,.2f}) on {t['timestamp'].strftime('%Y-%m-%d')}")
        tx_str = "\n".join(tx_list)

    # Build the prompt instructing Gemini how to act
    # Build the prompt instructing Gemini how to act
    prompt = f"""
    You are 'BankEase AI', a highly professional, secure, and helpful banking concierge.
    You are chatting directly with the user. Be concise, polite, and conversational.

    *** IMPORTANT LANGUAGE RULE ***
    Always detect the language the user is speaking in the 'User Message' and reply in that EXACT SAME LANGUAGE. 
    - If the user types in pure Hindi, reply in pure Hindi.
    - If the user types in Hinglish (e.g., "mera balance kya hai"), reply in Hinglish.
    - If the user types in English, reply in English.
    - If they type in any other global or regional language, reply in that specific language.

    --- USER CONTEXT ---
    Name: {name}
    Account Number: {acct_num}
    Recent Transactions:
    {tx_str}

    --- INSTRUCTIONS ---
    You must evaluate the user's message and respond in strict JSON format. 
    Do not use markdown formatting like ```json in your output. Just output the raw JSON object.
    
    The JSON object must have exactly two keys: "text" and "action".
    1. "text": Your conversational reply (Must be in the user's language). (If they ask for balance, tell them you need their PIN to verify first).
    2. "action": A UI command. Use exactly one of the following based on intent:
       - "show_balance_pin" (IF the user asks to check their balance/funds)
       - "open_transfer" (IF the user asks to send, transfer, or pay money)
       - "download_statement" (IF the user asks for a bank statement)
       - null (If they are just chatting, asking about history, or asking a general question)

    User Message: "{msg}"
    """
    try:
        # Call the new Gemini 2.5 Flash model using the updated SDK
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", # Forces the AI to output clean JSON
                temperature=0.4
            )
        )
        
        # Clean the response to ensure it's valid JSON (Fallback cleanup)
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        result = json.loads(raw_text.strip())
        return result

    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        # Fallback response if the API fails or JSON parsing breaks
        return {
            "text": f"I apologize {name}, I am experiencing a temporary connection issue. How else may I assist you?", 
            "action": None
        }
# ─── Admin / Manager ──────────────────────────────────────────────────────────
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    err = require_manager()
    if err: return err
    try:
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        
        # YAHAN CHANGE KIYA HAI: a.is_flagged as is_frozen ko a.is_frozen kiya hai
        cursor.execute("""
            SELECT u.id, u.username, u.full_name, u.role, u.is_active,
                   a.account_number, a.balance, a.is_frozen
            FROM users u LEFT JOIN accounts a ON u.id = a.user_id
            WHERE u.role = 'user' ORDER BY u.id DESC
        """)
        
        users = cursor.fetchall()
        cursor.close(); conn.close()
        for u in users:
            if u['balance'] is not None:
                u['balance'] = float(u['balance'])
        return jsonify({"success": True, "users": users}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/add-money', methods=['POST'])
def admin_add_money():
    err = require_manager()
    if err: return err
    try:
        data = request.json
        account_number = data.get('account_number')
        amount = float(data.get('amount', 0))
        if not account_number or amount <= 0:
            return jsonify({"success": False, "message": "Account and positive amount required"}), 400
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM accounts WHERE account_number = %s", (account_number,))
        acc = cursor.fetchone()
        if not acc:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Account not found"}), 404
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_number = %s", (amount, account_number))
        conn.commit()
        cursor.execute("SELECT balance FROM accounts WHERE account_number = %s", (account_number,))
        new_bal = float(cursor.fetchone()['balance'])
        cursor.close(); conn.close()
        return jsonify({"success": True, "message": f"Rs.{amount:,.0f} added successfully", "new_balance": new_bal}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/freeze', methods=['POST'])
def admin_freeze():
    err = require_manager()
    if err: return err
    try:
        data = request.json
        account_number = data.get('account_number')
        freeze = bool(data.get('freeze', True))
        conn = get_db(); cursor = conn.cursor()
        
        # YAHAN CHANGE KIYA HAI: is_flagged ki jagah is_frozen
        cursor.execute("UPDATE accounts SET is_frozen = %s WHERE account_number = %s", (1 if freeze else 0, account_number))
        
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": f"Account {'frozen' if freeze else 'unfrozen'} successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    err = require_manager()
    if err: return err
    try:
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE role='user'")
        total_users = cursor.fetchone()['total_users']
        cursor.execute("SELECT SUM(balance) as total_balance FROM accounts")
        total_balance = cursor.fetchone()['total_balance'] or 0
        cursor.execute("SELECT COUNT(*) as frozen_accounts FROM accounts WHERE is_flagged=1")
        frozen_accounts = cursor.fetchone()['frozen_accounts']
        cursor.execute("SELECT COUNT(*) as pending_tickets FROM support_tickets WHERE status='Pending'")
        pending_tickets = cursor.fetchone()['pending_tickets']
        cursor.close(); conn.close()
        return jsonify({"success": True, "total_users": total_users, "total_balance": float(total_balance),
                        "frozen_accounts": frozen_accounts, "pending_tickets": pending_tickets}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Support ──────────────────────────────────────────────────────────────────
@app.route('/api/support/request', methods=['POST'])
def support_request():
    err = require_login()
    if err: return err
    try:
        data = request.json
        subject = data.get('subject', 'General Inquiry')
        preferred_time = data.get('preferred_time', None)
        user_id = session.get('user_id')
        conn = get_db(); cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO support_tickets (user_id, subject, preferred_time) VALUES (%s, %s, %s)",
                (user_id, subject, preferred_time)
            )
        except Exception:
            cursor.execute(
                "INSERT INTO support_tickets (user_id, subject) VALUES (%s, %s)",
                (user_id, subject)
            )
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Support request submitted."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/support/tickets', methods=['GET'])
def support_tickets():
    err = require_login()
    if err: return err
    try:
        user_id = session.get('user_id')
        role = session.get('role')
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        if role == 'manager':
            cursor.execute("SELECT t.*, u.full_name, u.username FROM support_tickets t JOIN users u ON t.user_id = u.id ORDER BY t.created_at DESC")
        else:
            cursor.execute("SELECT t.*, u.full_name, u.username FROM support_tickets t JOIN users u ON t.user_id = u.id WHERE t.user_id = %s ORDER BY t.created_at DESC", (user_id,))
        tickets = cursor.fetchall()
        for t in tickets:
            if t.get('appointment_time'):
                t['appointment_time'] = t['appointment_time'].isoformat()
            if t.get('preferred_time'):
                t['preferred_time'] = t['preferred_time'].isoformat() if hasattr(t['preferred_time'], 'isoformat') else t['preferred_time']
            t['created_at'] = t['created_at'].isoformat()
        cursor.close(); conn.close()
        return jsonify({"success": True, "tickets": tickets}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/support/schedule', methods=['POST'])
def support_schedule():
    err = require_manager()
    if err: return err
    try:
        data = request.json
        ticket_id = data.get('ticket_id')
        appointment_time = data.get('appointment_time')
        if not ticket_id or not appointment_time:
            return jsonify({"success": False, "message": "Ticket ID and Appointment Time required"}), 400
        conn = get_db(); cursor = conn.cursor()
        cursor.execute(
            "UPDATE support_tickets SET appointment_time = %s, status = 'Scheduled' WHERE id = %s",
            (appointment_time, ticket_id)
        )
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Appointment scheduled successfully."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/support/resolve', methods=['POST'])
def support_resolve():
    err = require_manager()
    if err: return err
    try:
        ticket_id = request.json.get('ticket_id')
        conn = get_db(); cursor = conn.cursor()
        cursor.execute("UPDATE support_tickets SET status = 'Resolved' WHERE id = %s", (ticket_id,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Ticket resolved"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/support/messages/<int:ticket_id>', methods=['GET'])
def get_support_messages(ticket_id):
    err = require_login()
    if err: return err
    try:
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT m.*, u.full_name, u.role FROM ticket_messages m JOIN users u ON m.sender_id = u.id WHERE m.ticket_id = %s ORDER BY m.created_at ASC",
            (ticket_id,)
        )
        messages = cursor.fetchall()
        for m in messages:
            m['created_at'] = m['created_at'].isoformat()
        cursor.close(); conn.close()
        return jsonify({"success": True, "messages": messages}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/support/message', methods=['POST'])
def send_support_message():
    err = require_login()
    if err: return err
    try:
        data = request.json
        ticket_id    = data.get('ticket_id')
        message_text = data.get('message_text', '')
        file_data    = data.get('file_data', None)
        sender_id    = session.get('user_id')
        if not ticket_id or (not message_text and not file_data):
            return jsonify({"success": False, "message": "Message or file is required"}), 400
        file_url = None
        if file_data:
            app_root = os.path.dirname(os.path.abspath(__file__))
            folder = os.path.join(app_root, 'static', 'support_uploads')
            os.makedirs(folder, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = 'jpg'
            if 'pdf' in file_data[:30]: ext = 'pdf'
            elif 'png' in file_data[:30]: ext = 'png'
            elif 'gif' in file_data[:30]: ext = 'gif'
            fname = f"file_{ticket_id}_{sender_id}_{ts}.{ext}"
            fpath = os.path.join(folder, fname)
            clean_b64 = re.sub(r'^data:(image|application)/.+;base64,', '', file_data)
            with open(fpath, 'wb') as f:
                f.write(base64.b64decode(clean_b64))
            file_url = f"/static/support_uploads/{fname}"
        conn = get_db(); cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ticket_messages (ticket_id, sender_id, message_text, file_url) VALUES (%s, %s, %s, %s)",
            (ticket_id, sender_id, message_text, file_url)
        )
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Message sent"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500





# ─── Fraud Detection Engine ────────────────────────────────────
from datetime import datetime, timedelta

def fraud_check(cursor, account_id, amount, balance, recipient_account):
    flags = []
    risk_score = 0
    if amount > 50000:
        flags.append("Large transaction (>Rs.50,000)")
        risk_score += 40
    if balance > 0 and (amount / balance) > 0.80:
        flags.append("Draining 80%+ of balance")
        risk_score += 30
    two_min_ago = datetime.now() - timedelta(minutes=2)
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE account_id=%s AND timestamp >= %s",
        (account_id, two_min_ago)
    )
    if cursor.fetchone()['cnt'] >= 3:
        flags.append("Rapid fire (3+ txns in 2 mins)")
        risk_score += 50
    hour = datetime.now().hour
    if 1 <= hour <= 4:
        flags.append("Transaction at odd hours (1AM-4AM)")
        risk_score += 20
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE account_id=%s AND timestamp >= %s",
        (account_id, today_start)
    )
    if cursor.fetchone()['cnt'] >= 10:
        flags.append("Too many transactions today (10+)")
        risk_score += 35
    return {"is_fraud": risk_score >= 50, "risk_score": risk_score, "flags": flags}


# ─── Fraud Alerts — GET ────────────────────────────────────────
@app.route('/api/admin/fraud-alerts', methods=['GET'])
def get_fraud_alerts():
    err = require_manager()
    if err: return err
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.id, f.risk_score, f.flags, f.amount, f.is_reviewed, f.created_at,
                   a.account_number, u.full_name, u.username
            FROM fraud_alerts f
            JOIN accounts a ON f.account_id = a.id
            JOIN users u ON a.user_id = u.id
            ORDER BY f.created_at DESC LIMIT 100
        """)
        alerts = cursor.fetchall()
        cursor.close(); conn.close()
        for a in alerts:
            a['created_at'] = a['created_at'].isoformat()
            a['amount'] = float(a['amount'] or 0)
        return jsonify({"success": True, "alerts": alerts}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ─── Fraud Review — POST ───────────────────────────────────────
@app.route('/api/admin/fraud-review', methods=['POST'])
def fraud_review():
    err = require_manager()
    if err: return err
    try:
        alert_id = request.json.get('alert_id')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE fraud_alerts SET is_reviewed=1 WHERE id=%s", (alert_id,))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Marked as reviewed"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n===== BankEase Server Starting =====")
    print(f"App: {os.path.abspath(__file__)}")
    print("URL: http://localhost:5000/")
    print("Email test: http://localhost:5000/test-email")
    print("=====================================\n")
    app.run(debug=True, port=5000, host='0.0.0.0')