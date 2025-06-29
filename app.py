from flask import Flask, request, redirect, flash, render_template_string, session, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
from models import db, Course
from datetime import timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'  # Use env variable in production
app.permanent_session_lifetime = timedelta(minutes=30)

# DB config
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload config
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Init DB
db.init_app(app)

with app.app_context():
    db.create_all()

# Utility
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def home():
    return "✅ Skill Boost Platform is live!"

@app.route('/courses')
def show_courses():
    courses = Course.query.all()
    return {
        "courses": [c.title for c in courses]
    }

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Basic hardcoded credentials (use env or DB later)
        if username == "admin" and password == "admin123":
            session.permanent = True
            session['admin'] = True
            flash("✅ Logged in successfully as admin")
            return redirect('/admin/upload')
        else:
            flash("❌ Invalid credentials")
            return redirect('/admin/login')

    return render_template_string('''
        <h2>Admin Login</h2>
        <form method="POST">
            Username: <input type="text" name="username"><br><br>
            Password: <input type="password" name="password"><br><br>
            <input type="submit" value="Login">
        </form>
    ''')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash("✅ Logged out successfully")
    return redirect('/')

@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_course():
    if not session.get('admin'):
        flash("❌ Unauthorized access. Please login as admin.")
        return redirect('/admin/login')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['pdf']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            new_course = Course(
                title=title,
                description=description,
                pdf_filename=filename
            )
            db.session.add(new_course)
            db.session.commit()

            flash("✅ Course uploaded successfully!")
            return redirect('/courses')
        else:
            flash("❌ Invalid file format. Please upload a PDF.")

    return render_template_string('''
        <h2>Upload New Course</h2>
        <form method="POST" enctype="multipart/form-data">
            Title: <input type="text" name="title" required><br><br>
            Description: <textarea name="description" required></textarea><br><br>
            PDF File: <input type="file" name="pdf" accept=".pdf" required><br><br>
            <input type="submit" value="Upload">
        </form>
        <br>
        <a href="/admin/logout">Logout</a>
    ''')

# Render port binding
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
