import os


SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

SQLALCHEMY_DATABASE_URI = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://root:change-me@localhost:3306/chromalearn",
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
