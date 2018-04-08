from functools import wraps
import logging
import sys

from flask import Flask, jsonify, render_template, request

from cronscrape import settings
from cronscrape.scrape import collect_latest_reports


logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

app = Flask(__name__)


def authenticated(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if request.args.get('token') == settings.get('token'):
            return func(*args, **kwargs)
        return jsonify({'error': 'token parameter required.'}), 403
    return inner


@app.route('/latest')
@authenticated
def task_latest():
    amount = request.args.get('amount', default=1, type=int)
    return jsonify(collect_latest_reports(amount))


@app.route('/_ah/health')
def health_check():
    return 'healthy', 200


if __name__ == '__main__':
    app.run('127.0.0.1', port=8080, debug=True)
