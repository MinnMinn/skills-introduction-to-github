from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/hello", methods=["GET"])
def hello():
    """Hello endpoint — returns a friendly greeting."""
    return jsonify({"message": "Hello, World!"}), 200


if __name__ == "__main__":
    app.run(debug=True)
