# WSGI entrypoint used by gunicorn in production:
#   gunicorn --bind 0.0.0.0:8080 wsgi --chdir ./src/
from app import app as application

if __name__ == "__main__":
    application.run()
