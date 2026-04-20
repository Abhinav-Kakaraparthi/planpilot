# ScreenMind Todo

`ScreenMind Todo` is a local-first MVP that watches your screen, extracts visible text, infers likely next actions, and builds a todo list automatically.

This version is designed to be free to run on your own machine:

- Screen capture is local
- OCR is local via Tesseract
- Task inference is local via heuristic rules
- Optional Ollama integration is supported for better summaries later

## What It Does

Every few seconds, the app:

1. Captures the primary display
2. Reads text from the screenshot with OCR
3. Detects the active window title on Windows
4. Infers likely tasks from repeated activity patterns
5. Stores activity history and suggested tasks in SQLite
6. Shows everything in a browser UI

## Tech Stack

- Backend: FastAPI
- Storage: SQLite + SQLAlchemy
- OCR: Tesseract
- Screen capture: MSS
- Frontend: Plain HTML/CSS/JS
- Optional local LLM: Ollama

## Prerequisites

- Windows 10/11
- Python 3.11+
- Git
- Tesseract OCR installed

Install Tesseract on Windows:

1. Download from: <https://github.com/UB-Mannheim/tesseract/wiki>
2. Install it
3. Confirm `tesseract --version` works in PowerShell

## Local Setup

```powershell
git clone <YOUR_REPO_URL>
cd screenmind-todo
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
Copy-Item .env.example .env
```

Run the app:

```powershell
uvicorn screenmind_todo.main:app --reload
```

Open:

- App UI: <http://127.0.0.1:8000>
- API docs: <http://127.0.0.1:8000/docs>

## Project Structure

```text
screenmind-todo/
├── .github/workflows/ci.yml
├── src/screenmind_todo/
│   ├── api/
│   ├── services/
│   ├── static/
│   ├── config.py
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

## How The Free AI Logic Works

This MVP uses local rule-based inference, which is the most realistic zero-cost path.

Examples:

- Repeated presence of `leetcode`, `traceback`, `error`, `exception` -> suggest fixing a bug
- Repeated presence of `gmail`, `inbox`, `draft`, `follow up` -> suggest sending a reply
- Repeated presence of `resume`, `job description`, `linkedin` -> suggest tailoring resume or applying
- Repeated presence of `assignment`, `rubric`, `deadline`, `submit` -> suggest completing an assignment

This is enough to validate the product before spending money on a multimodal API.

## Optional Ollama Upgrade

If you install Ollama locally, you can set:

```env
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.2:3b
```

The app will then ask the local model to produce a short activity summary, while task creation still stays guarded by deterministic rules.

## GitHub Setup

Create the repo:

```powershell
mkdir screenmind-todo
cd screenmind-todo
git init
git branch -M main
```

Copy this project into that folder, then:

```powershell
git add .
git commit -m "Initial commit: local AI todo watcher MVP"
gh repo create screenmind-todo --public --source=. --remote=origin --push
```

If you do not use GitHub CLI:

1. Create an empty repo on GitHub named `screenmind-todo`
2. Then run:

```powershell
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## Notes

- This app watches your screen, so be deliberate about privacy.
- The current version stores only OCR text snippets and metadata, not screenshots.
- Task inference is conservative to reduce noise.
