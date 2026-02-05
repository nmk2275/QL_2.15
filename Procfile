web: ROOT_DIR=$(pwd) && cd backend && PYTHONPATH=$ROOT_DIR:$PYTHONPATH gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120
