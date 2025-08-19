from flask import Flask, render_template, request, redirect, send_from_directory, abort
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def init_db():
    conn = sqlite3.connect('opportunities.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            filename TEXT,
            uploaded_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()


# --- Helper to format uploaded date
def format_date(value):
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except Exception:
        return value


# --- Home page
@app.route('/')
def home():
    conn = sqlite3.connect('opportunities.db')
    c = conn.cursor()
    c.execute("SELECT id, title, description, filename, uploaded_at FROM opportunities ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    opportunities = [(row[0], row[1], row[2], row[3], format_date(row[4])) for row in rows]

    return render_template('home.html', opportunities=opportunities)


# --- Add new opportunity
@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files.get('file')
        filename = None

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect('opportunities.db')
        c = conn.cursor()
        c.execute("INSERT INTO opportunities (title, description, filename, uploaded_at) VALUES (?, ?, ?, ?)",
                  (title, description, filename, uploaded_at))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('add.html')


# --- Edit opportunity
@app.route('/edit/<int:opp_id>', methods=['GET', 'POST'])
def edit(opp_id):
    conn = sqlite3.connect('opportunities.db')
    c = conn.cursor()
    c.execute("SELECT id, title, description, filename FROM opportunities WHERE id=?", (opp_id,))
    opportunity = c.fetchone()
    conn.close()

    if not opportunity:
        return redirect('/')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files.get('file')
        filename = opportunity[3]

        if file and file.filename != '':
            # Remove old file if exists
            if filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = sqlite3.connect('opportunities.db')
        c = conn.cursor()
        c.execute("UPDATE opportunities SET title=?, description=?, filename=? WHERE id=?",
                  (title, description, filename, opp_id))
        conn.commit()
        conn.close()
        return redirect('/')

    return render_template('edit.html', opportunity=opportunity)


# --- Delete opportunity
@app.route('/delete/<int:opp_id>', methods=['POST'])
def delete(opp_id):
    conn = sqlite3.connect('opportunities.db')
    c = conn.cursor()
    # Remove file if exists
    c.execute("SELECT filename FROM opportunities WHERE id=?", (opp_id,))
    row = c.fetchone()
    if row and row[0]:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
        if os.path.exists(filepath):
            os.remove(filepath)
    # Delete DB record
    c.execute("DELETE FROM opportunities WHERE id=?", (opp_id,))
    conn.commit()
    conn.close()
    return redirect('/')


# --- Download file
@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)


# --- View file in browser
@app.route('/view/<filename>')
def view_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)


if __name__ == '__main__':
    app.run(debug=True)
