"""Flask application factory."""
from flask import Flask
from .extensions import db
from .auth.routes import auth_bp


def create_app(config=None):
    """Create and configure the Flask application.

    Args:
        config: Optional dict of config overrides (useful for testing).

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Default configuration
    app.config.setdefault("SECRET_KEY", "change-me-in-production")
    app.config.setdefault("JWT_ALGORITHM", "HS256")
    app.config.setdefault("JWT_EXPIRY_SECONDS", 3600)
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    if config:
        app.config.update(config)

    # Initialise extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app
