from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to Skill Boost Platform! Coming Soon."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "skillboost_secret")

# ✅ Replace this with your actual MySQL connection info
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://skillsdb_user:FQzUpOS4Znc8iscCAhFS3bpXa7YRxVZd@dpg-d1fsp1ripnbc73a0hvlg-a/skillsdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

@app.route('/')
def home():
    if 'user' in session:
        return f"Welcome {session['user']}! PDFs/Sessions coming soon..."
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(email=email).first():
            return "Email already registered."

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.name
            return redirect('/')
        return "Invalid email or password"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
