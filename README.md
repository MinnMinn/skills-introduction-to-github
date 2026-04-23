# skills-introduction-to-github

A lightweight **User Preferences & Orders API** built with [FastAPI](https://fastapi.tiangolo.com/).  
It demonstrates core GitHub collaboration workflows — branching, pull requests, and code review — while shipping a real, runnable service.

---

## Prerequisites

- Python **3.11+**
- `pip` (or a virtual-environment manager such as `venv` / `uv`)

---

## Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the development server
uvicorn src.main:app --reload
```

The API will be available at <http://127.0.0.1:8000>.  
Interactive docs (Swagger UI) are at <http://127.0.0.1:8000/docs>.

### Run the tests

```bash
pytest
```

---

## License

[MIT](LICENSE) © GitHub, Inc.
