import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'mp4', 'mp3'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'flask_drive')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'psqldd')
DB_PORT = os.getenv('DB_PORT', '5432')


def get_db():
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
    except Exception as e:
        raise RuntimeError(f'Unable to connect to PostgreSQL: {e}') from e

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            uploaded_by INTEGER REFERENCES users(id) ON DELETE CASCADE,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size BIGINT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    return f"{size_bytes / (1024 ** 3):.1f} GB"

app.jinja_env.filters['format_size'] = format_size

def get_icon(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    icons = {
        'pdf': '📄', 'doc': '📝', 'docx': '📝', 'txt': '📃',
        'png': '🖼', 'jpg': '🖼', 'jpeg': '🖼', 'gif': '🖼',
        'mp4': '🎬', 'mp3': '🎵', 'zip': '🗜', 'csv': '📊',
    }
    return icons.get(ext, '📁')

app.jinja_env.globals['get_icon'] = get_icon

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        if not all([username, email, password, confirm]):
            flash('All fields are required.', 'error')
            return render_template('signup.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('signup.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE email = %s OR username = %s', (email, username))
        if cur.fetchone():
            flash('Email or username already taken.', 'error')
            cur.close(); conn.close()
            return render_template('signup.html')
        hashed = generate_password_hash(password)
        cur.execute(
            'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
            (username, email, hashed)
        )
        conn.commit()
        cur.close(); conn.close()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id, username, password FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user[2], password):
            session['user_id']  = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        '''SELECT f.id, f.original_name, f.upload_date, f.file_size
           FROM files f
           WHERE f.uploaded_by = %s
           ORDER BY f.upload_date DESC''',
        (session['user_id'],)
    )
    files = cur.fetchall()
    cur.close(); conn.close()
    return render_template('dashboard.html', files=files, username=session['username'])

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('dashboard'))
    if not allowed_file(file.filename):
        flash('File type not allowed.', 'error')
        return redirect(url_for('dashboard'))
    original_name = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    saved_name = f"{session['user_id']}_{timestamp}{original_name}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_name)
    file.save(filepath)
    size = os.path.getsize(filepath)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO files (filename, original_name, uploaded_by, file_size) VALUES (%s, %s, %s, %s)',
        (saved_name, original_name, session['user_id'], size)
    )
    conn.commit()
    cur.close(); conn.close()
    flash(f'"{original_name}" uploaded successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/download/<int:file_id>')
@login_required
def download(file_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT filename, original_name, uploaded_by FROM files WHERE id = %s', (file_id,))
    file = cur.fetchone()
    cur.close(); conn.close()
    if not file:
        flash('File not found.', 'error')
        return redirect(url_for('dashboard'))
    if file[2] != session['user_id']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file[0])
    if not os.path.exists(file_path):
        flash('The uploaded file is missing from the server.', 'error')
        return redirect(url_for('dashboard'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], file[0], as_attachment=True, download_name=file[1])


def initialize_app():
    try:
        init_db()
        print('Database tables ready.')
    except Exception as e:
        print(f'Database initialization failed: {e}')


initialize_app()


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
