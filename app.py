from sqlalchemy import text  # Add this import at the top
db.session.execute(text('SELECT 1'))

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Replace this with your Render PostgreSQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://skillsdb_user:FQzUpOS4Znc8iscCAhFS3bpXa7YRxVZd@dpg-d1fsp1ripnbc73a0hvlg-a/skillsdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.route('/test-db')
def test_db():
    try:
        db.session.execute('SELECT 1')
        return "✅ Database connected successfully!"
    except Exception as e:
        return f"❌ Database error: {e}"


@app.route('/')
def home():
    return render_template('index.html')  # Make sure you have templates/index.html




if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render-assigned port
    app.run(host='0.0.0.0', port=port)
