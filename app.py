from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

from models import db, Course  # ✅ Make sure both db and Course are imported

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Setup DB config
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB with app
db.init_app(app)

# ✅ Create tables inside app context
with app.app_context():
    db.create_all()

# Sample route
@app.route('/')
def home():
    return "✅ Skill Boost Platform is live!"

# Test route to fetch courses
@app.route('/courses')
def show_courses():
    courses = Course.query.all()
    return {
        "courses": [c.title for c in courses]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT not found
    app.run(host="0.0.0.0", port=port)
