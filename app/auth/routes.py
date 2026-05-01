"""HTTP layer for authentication endpoints."""
from flask import Blueprint, current_app, jsonify, request

from .service import attempt_login

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT.

    Request body (JSON):
        username (str): The user's account name.
        password (str): The user's plaintext password.

    Returns:
        200 + ``{"token": "<jwt>"}`` on success.
        400 + ``{"error": "..."}`` when required fields are missing.
        401 + ``{"error": "Invalid credentials"}`` on auth failure.
    """
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    ip_address = request.remote_addr

    token = attempt_login(
        username=username,
        password=password,
        ip_address=ip_address,
        secret_key=current_app.config["SECRET_KEY"],
        algorithm=current_app.config.get("JWT_ALGORITHM", "HS256"),
        expiry_seconds=current_app.config.get("JWT_EXPIRY_SECONDS", 3600),
    )

    if token is None:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"token": token}), 200
