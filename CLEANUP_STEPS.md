# Project Cleanup Steps

This project should keep source code, configuration templates, migrations, and static app assets in version control.
Local runtime files, generated files, private credentials, and manual backups should stay outside Git.

## What Was Added

1. A root `.gitignore` was added.
2. The ignore rules cover local secrets, Python caches, virtual environments, local databases, media uploads, zip backups, OS metadata, logs, and WeChat private config.

## Files/Folders That Should Not Be Committed

- `frontend.zip`
- `backend/backend_fixed/*.zip`
- `backend/backend_fixed/backup/`
- `backend/backend_fixed/venv/`
- `backend/backend_fixed/__pycache__/` and all nested `__pycache__/`
- `backend/backend_fixed/db.sqlite3`
- `backend/backend_fixed/data.json`
- `backend/backend_fixed/data_backup.json`
- `backend/backend_fixed/media/`
- `backend/backend_fixed/.env`
- `backend/__MACOSX/`
- `.DS_Store`
- `logs/`

## Cleanup Completed

The local cleanup has been performed after confirming the project already has a manual backup elsewhere.
The removed files were ignored runtime files, generated files, local credentials, local databases, uploaded media, and zip backups.

Removed examples:

- `frontend.zip`
- `backend/__MACOSX/`
- `backend/backend_fixed/.env`
- `backend/backend_fixed/backup/`
- `backend/backend_fixed/venv/`
- `backend/backend_fixed/media/`
- `backend/backend_fixed/db.sqlite3`
- `backend/backend_fixed/data.json`
- `backend/backend_fixed/data_backup.json`
- `backend/backend_fixed/*.zip`
- `__pycache__/`
- `.DS_Store`

If these files are needed later, restore them from the separate manual backup.

## Recreate Local Files

Create a local `.env`:

```powershell
cd C:\Users\86177\Desktop\Fullstack\backend\backend_fixed
Copy-Item .env.example .env
```

Then edit `.env` and fill in the real local database password and secrets.

Recreate the backend virtual environment:

```powershell
cd C:\Users\86177\Desktop\Fullstack\backend\backend_fixed
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the backend:

```powershell
cd C:\Users\86177\Desktop\Fullstack\backend\backend_fixed
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

## Git Workflow

After cleanup, use:

```powershell
git status --short
git add .gitignore CLEANUP_STEPS.md frontend backend
git commit -m "chore: initialize project repository"
```

Before committing, check that no `.env`, database, zip, virtual environment, or uploaded media file appears in `git status`.
