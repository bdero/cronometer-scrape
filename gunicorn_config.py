import multiprocessing
import os


bind = f':{os.environ.get("PORT", 8080)}'
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 300  # 5 minutes
