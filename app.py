from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from models import db  # Import your db instance

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/courses')
def show_courses():from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

from models import db, Course  # ✅ Make sure Course is also imported

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ✅ Create tables safely using app context (instead of before_first_request)
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return "🎓 Skill Boost Platform is Live!"

@app.route('/courses')
def show_courses():
    courses = Course.query.all()
    return {
        "courses": [c.title for c in courses]
    }

    courses = Course.query.all()
    return {
        "courses": [c.title for c in courses]
    }

