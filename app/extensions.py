"""Shared Flask extensions — initialised here, bound to the app in the factory."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
