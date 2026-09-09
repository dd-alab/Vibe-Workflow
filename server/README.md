# FastAPI Backend

This is the backend server built with FastAPI.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Create `.env` from `.env.example`. `PROJECTS_ROOT` controls where local
project JSON files and images are stored. Relative paths are resolved from the
`server` directory; use an absolute path if projects should live elsewhere.

```dotenv
PROJECTS_ROOT=./data/projects
```

## Running the Server

Start the development server:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

## API Endpoints

- `GET /` - Welcome message
- `GET /api/health` - Health check endpoint

## Windows PowerShell

If PowerShell blocks virtual-environment activation scripts, call the virtual
environment executables directly:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run backend checks from the `server` directory:

```powershell
venv\Scripts\python.exe -m pytest
venv\Scripts\python.exe -m ruff check .
```
