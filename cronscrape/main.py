from flask import Flask, jsonify, request
from google.appengine.api.taskqueue import taskqueue

from cronscrape.scrape import collect_latest_reports


app = Flask(__name__)


@app.route('/task_latest')
def task_latest():
    amount = request.args.get('amount', default=1, type=int)
    return jsonify(collect_latest_reports(amount))


@app.route('/latest')
def latest():
    amount = request.args.get('amount', default=1, type=int)
    task = taskqueue.add(
        url='/task_latest',
        target='worker',
        params={'amount': amount},
    )
    return jsonify({'task_name': task.name})


@app.route('/_ah/health')
def health_check():
    return 'healthy', 200


if __name__ == '__main__':
    app.run('127.0.0.1', port=8080, debug=True)
