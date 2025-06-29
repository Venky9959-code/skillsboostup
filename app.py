from flask import Flask, request, redirect, flash, render_template, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import razorpay
from models import db, Course, User, Purchase, EmailLog
from datetime import timedelta
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_babel import Babel, gettext

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

# Babel for i18n
babel = Babel(app)
app.config['BABEL_DEFAULT_LOCALE'] = 'en'

# Init DB
db.init_app(app)
with app.app_context():
    db.create_all()

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
        if User.query.filter_by(email=email).first():
            flash(gettext("Email already exists"))
            return redirect('/register')
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash(gettext("Registered successfully. Please login."))
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
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

@app.route('/courses')
def show_courses():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    query = Course.query.filter(Course.title.ilike(f"%{search}%"))
    pagination = query.paginate(page=page, per_page=per_page)
    return render_template('courses.html', courses=pagination.items, pagination=pagination, search=search)

@app.route('/buy/<int:course_id>')
def buy_course(course_id):
    if 'user_id' not in session:
        flash(gettext("Login required"))
        return redirect('/login')
    course = Course.query.get_or_404(course_id)
    payment = razorpay_client.order.create({
        "amount": course.price * 100,
        "currency": "INR",
        "payment_capture": 1
    })
    return render_template('buy.html', course=course, amount=payment['amount'], key_id=RAZORPAY_KEY_ID, order_id=payment['id'])

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    course_id = int(request.form.get("course_id"))
    user_id = session.get("user_id")
    if not user_id:
        flash(gettext("Login required"))
        return redirect("/login")

    if not Purchase.query.filter_by(user_id=user_id, course_id=course_id).first():
        db.session.add(Purchase(user_id=user_id, course_id=course_id))
        db.session.commit()

    course = Course.query.get_or_404(course_id)
    user = User.query.get(user_id)

    try:
        msg = Message(
            subject="📘 Your Course Access – Skills Boost",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email]
        )
        msg.body = f"Thank you for purchasing '{course.title}'!\nDownload: https://{request.host}/static/uploads/{course.pdf_filename}"
        mail.send(msg)

        db.session.add(EmailLog(user_email=user.email, course_id=course.id))
        db.session.commit()

        flash(gettext("Payment successful! Confirmation email sent."))
    except Exception as e:
        flash(gettext(f"Email sending failed. {str(e)}"))

    return redirect(f'/course/{course_id}/access')

@app.route('/course/<int:course_id>/access')
def access_course(course_id):
    user_id = session.get("user_id")
    if not user_id:
        flash(gettext("Login required"))
        return redirect("/login")

    if not Purchase.query.filter_by(user_id=user_id, course_id=course_id).first():
        flash(gettext("You must complete payment first."))
        return redirect(f'/buy/{course_id}')

    course = Course.query.get_or_404(course_id)
    return render_template('access.html', course=course)

@app.route('/dashboard')
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        flash(gettext("Login required"))
        return redirect("/login")

    user = User.query.get(user_id)
    purchases = Purchase.query.filter_by(user_id=user_id).all()
    course_list = [Course.query.get(p.course_id) for p in purchases]
    return render_template('dashboard.html', user=user, courses=course_list)

@app.route('/admin')
def admin_panel():
    users = User.query.all()
    purchases = Purchase.query.all()
    return render_template('admin.html', users=users, purchases=purchases)

@app.route('/chatbot', methods=['GET'])
def chatbot():
    return render_template('chatbot.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
