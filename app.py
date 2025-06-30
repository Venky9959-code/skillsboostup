from flask import Flask, jsonify, request, redirect, flash, render_template, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import razorpay
from datetime import timedelta
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_babel import Babel, gettext
from flask_migrate import Migrate

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)

# Razorpay Keys
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail Config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

# Database instance
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Babel for i18n
babel = Babel(app)
app.config['BABEL_DEFAULT_LOCALE'] = 'en'

# Utility function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        db_conn = db.engine.raw_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM user WHERE email=%s", (email,))
        existing = cursor.fetchone()
        if existing:
            flash(gettext("Email already exists"))
            return redirect('/register')
        cursor.execute("INSERT INTO user (email, password) VALUES (%s, %s)", (email, password))
        db_conn.commit()
        cursor.close()
        db_conn.close()
        flash(gettext("Registered successfully. Please login."))
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db_conn = db.engine.raw_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT id, password FROM user WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db_conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            flash(gettext("Logged in"))
            return redirect('/dashboard')
        else:
            flash(gettext("Invalid credentials"))
            return redirect('/login')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash(gettext("Logged out"))
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash(gettext("Login required"))
        return redirect("/login")

    db_conn = db.engine.raw_connection()
    cursor = db_conn.cursor()
    cursor.execute("SELECT email FROM user WHERE id=%s", (session['user_id'],))
    user_email = cursor.fetchone()[0]
    cursor.execute("SELECT course_id FROM purchase WHERE user_id=%s", (session['user_id'],))
    course_ids = cursor.fetchall()
    course_list = []
    for c_id in course_ids:
        cursor.execute("SELECT * FROM course WHERE id=%s", (c_id[0],))
        course = cursor.fetchone()
        if course:
            course_list.append(course)
    cursor.close()
    db_conn.close()

    return render_template('dashboard.html', user_email=user_email, courses=course_list)

@app.route('/buy/<int:course_id>')
def buy_course(course_id):
    if 'user_id' not in session:
        flash("Login required")
        return redirect('/login')

    db_conn = db.engine.raw_connection()
    cursor = db_conn.cursor()
    cursor.execute("SELECT price FROM course WHERE id=%s", (course_id,))
    course = cursor.fetchone()
    cursor.close()
    db_conn.close()
    if not course:
        flash("Course not found")
        return redirect('/dashboard')

    payment = razorpay_client.order.create({
        "amount": course[0] * 100,
        "currency": "INR",
        "payment_capture": 1
    })
    return render_template('buy.html', course_id=course_id, amount=payment['amount'], key_id=RAZORPAY_KEY_ID, order_id=payment['id'])

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    user_id = session.get('user_id')
    course_id = request.form.get('course_id')
    if not user_id or not course_id:
        flash("Invalid session or course")
        return redirect('/')

    db_conn = db.engine.raw_connection()
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM purchase WHERE user_id=%s AND course_id=%s", (user_id, course_id))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute("INSERT INTO purchase (user_id, course_id) VALUES (%s, %s)", (user_id, course_id))
        db_conn.commit()

    cursor.execute("SELECT email FROM user WHERE id=%s", (user_id,))
    email = cursor.fetchone()[0]
    cursor.execute("SELECT title, pdf_filename FROM course WHERE id=%s", (course_id,))
    course = cursor.fetchone()

    try:
        msg = Message(
            subject="📘 Your Course Access – Skills Boost",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Thank you for purchasing '{course[0]}'!\nDownload: https://{request.host}/static/uploads/{course[1]}"
        mail.send(msg)

        cursor.execute("INSERT INTO email_log (user_email, course_id) VALUES (%s, %s)", (email, course_id))
        db_conn.commit()
        flash("Payment successful and email sent!")
    except Exception as e:
        flash(f"Payment successful but email failed: {str(e)}")

    cursor.close()
    db_conn.close()
    return redirect(f"/course/{course_id}/access")

@app.route('/course/<int:course_id>/access')
def access_course(course_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Login required")
        return redirect("/login")

    db_conn = db.engine.raw_connection()
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM purchase WHERE user_id=%s AND course_id=%s", (user_id, course_id))
    access = cursor.fetchone()
    if not access:
        flash("Please purchase this course first")
        return redirect(f"/buy/{course_id}")

    cursor.execute("SELECT * FROM course WHERE id=%s", (course_id,))
    course = cursor.fetchone()
    cursor.close()
    db_conn.close()

    return render_template("access.html", course=course)

@app.route('/chatbot', methods=['GET'])
def chatbot():
    return render_template('chatbot.html')

@app.route('/upload_course', methods=['GET', 'POST'])
def upload_course():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = int(request.form['price'])
        pdf_file = request.files['pdf']
        thumbnail_file = request.files['thumbnail']

        if pdf_file and allowed_file(pdf_file.filename):
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            pdf_file.save(pdf_path)
        else:
            flash("Invalid PDF file")
            return redirect('/upload_course')

        thumbnail_filename = None
        if thumbnail_file and allowed_file(thumbnail_file.filename):
            thumbnail_filename = secure_filename(thumbnail_file.filename)
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename)
            thumbnail_file.save(thumbnail_path)

        db_conn = db.engine.raw_connection()
        cursor = db_conn.cursor()
        cursor.execute("INSERT INTO course (title, description, price, pdf_filename, thumbnail) VALUES (%s, %s, %s, %s, %s)",
                       (title, description, price, pdf_filename, thumbnail_filename))
        db_conn.commit()
        cursor.close()
        db_conn.close()

        flash("Course uploaded successfully")
        return redirect('/upload_course')

    return render_template('upload_course.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
