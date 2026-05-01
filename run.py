"""Development entry-point. Do not use in production."""
from app import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
