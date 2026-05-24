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

## Recommended Manual Cleanup

Because some of these files may contain useful historical data or uploaded images, do not delete them blindly.
Move them into a local archive outside the repository first, then verify the app still runs.

Suggested PowerShell steps:

```powershell
$repo = "C:\Users\86177\Desktop\Fullstack"
$archive = "C:\Users\86177\Desktop\Fullstack_local_archive"
New-Item -ItemType Directory -Force -Path $archive

Move-Item -LiteralPath "$repo\frontend.zip" -Destination $archive
Move-Item -LiteralPath "$repo\backend\__MACOSX" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\backup" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\venv" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\media" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\db.sqlite3" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\data.json" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\data_backup.json" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\0419_2053(更改dashboard.zip" -Destination $archive
Move-Item -LiteralPath "$repo\backend\backend_fixed\feedback.zip" -Destination $archive
```

Then recreate the backend environment from source:

```powershell
cd C:\Users\86177\Desktop\Fullstack\backend\backend_fixed
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Git Workflow

After cleanup, use:

```powershell
git status --short
git add .gitignore CLEANUP_STEPS.md frontend backend
git commit -m "chore: initialize project repository"
```

Before committing, check that no `.env`, database, zip, virtual environment, or uploaded media file appears in `git status`.
