from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Website is working perfectly!"

if __name__ == '__main__':
    app.run()