# skills-introduction-to-github

A lightweight **FastAPI** service for managing user preferences and orders.  
Use it to explore GitHub workflows: branching, pull requests, and code review.

---

## Quickstart

**Prerequisites:** Python 3.11+, Git

```bash
# 1. Clone the repository
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the development server
uvicorn src.main:app --reload
```

The API will be available at <http://localhost:8000>.  
Interactive Swagger docs are at <http://localhost:8000/docs>.

### Run the tests

```bash
pytest
```

---

## Contributing

1. Fork the repo and create a branch (`git checkout -b feature/your-feature`).
2. Make your changes and run `pytest` to verify nothing is broken.
3. Open a pull request against `main` with a clear description of what changed and why.

## License

This project is licensed under the [MIT License](LICENSE).
