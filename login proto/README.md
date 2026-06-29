# FileDrive — Flask File Sharing App

A mini Google Drive: sign up, log in, upload and download files. Built with Flask + PostgreSQL.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your PostgreSQL database
Open psql and run:
```sql
CREATE DATABASE flask_drive;
```

### 3. Set environment variables
Set these before running (or edit the defaults in app.py):
```bash
export DB_HOST=localhost
export DB_NAME=flask_drive
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_PORT=5432
```

On Windows (Command Prompt):
```cmd
set DB_HOST=localhost
set DB_NAME=flask_drive
set DB_USER=postgres
set DB_PASSWORD=your_password
```

### 4. Run the app
```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

---

## Folder structure
```
flask_file_app/
├── app.py              # Main Flask app
├── requirements.txt
├── README.md
├── templates/
│   ├── login.html
│   ├── signup.html
│   └── dashboard.html
├── static/
│   └── style.css
└── uploads/            # Created automatically on first run
```

## Allowed file types
txt, pdf, png, jpg, jpeg, gif, doc, docx, zip, mp4, mp3

## Max upload size
50 MB per file
