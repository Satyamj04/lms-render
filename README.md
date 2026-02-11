Admin backend module (development)

Quick start (Windows PowerShell):

1. Create virtualenv and install requirements

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Apply migrations and create superuser

```powershell
cd myproject
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Available admin API endpoints (development):
- GET/POST/PUT/DELETE /api/admin/users/
- GET/POST/PUT/DELETE /api/admin/teams/
- GET /api/admin/users/me/  -> current logged-in user

Notes:
- The project registers `myproject.admin` app and uses Django's built-in `User` with a `UserProfile` extension.
- CORS is allowed for development; tighten settings before production.
