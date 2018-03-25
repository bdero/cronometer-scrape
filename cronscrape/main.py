from flask import Flask


app = Flask(__name__)


@app.route('/')
def index():
    return 'index'


@app.route('/_ah/health')
def health_check():
    return 'healthy', 200


if __name__ == '__main__':
    app.run('127.0.0.1', port=8080, debug=True)
