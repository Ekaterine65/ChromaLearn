import os

SECRET_KEY = 'change-me-in-production'

SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:root@localhost/chromalearn'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = True
