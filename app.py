from flask import Flask, render_template
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] ='postgresql://skillsdb_user:FQzUpOS4Znc8iscCAhFS3bpXa7YRxVZd@dpg-d1fsp1ripnbc73a0hvlg-a/skillsdb'

@app.route('/')
def home():
    return render_template('index.html')  # Make sure you have templates/index.html

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render-assigned port
    app.run(host='0.0.0.0', port=port)
