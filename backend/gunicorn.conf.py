# gunicorn.conf.py

bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Run using:
# gunicorn backend.api.server:app -c gunicorn.conf.py