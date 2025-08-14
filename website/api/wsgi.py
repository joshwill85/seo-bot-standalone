"""WSGI entry point for production deployment with Gunicorn."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import app

application = app

if __name__ == "__main__":
    application.run()