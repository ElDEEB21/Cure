# Cure API

FastAPI backend for a healthcare application.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your settings
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

## Tests

```bash
pytest tests/ --asyncio-mode=auto -v
```
