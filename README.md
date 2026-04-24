# skills-introduction-to-github

A lightweight **FastAPI** service for managing user preferences and orders.
It exposes a JSON REST API backed by Pydantic-validated schemas and is designed
as a hands-on introduction to working with GitHub — branching, pull requests,
issues, and Actions.

---

## Quick Start

**Prerequisites:** Python 3.11 or newer.

```bash
# 1. Clone the repo
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the development server
uvicorn src.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive docs are at `http://127.0.0.1:8000/docs`.

---

## Contributing

1. Fork the repository and create a feature branch (`git checkout -b feature/my-change`).
2. Commit your changes with a clear message.
3. Open a pull request describing what you changed and why.

Please follow the existing code style and include tests for any new behaviour.

---

## License

This project is licensed under the [MIT License](LICENSE).
