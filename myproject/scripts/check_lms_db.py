import os
import django

import sys
# Ensure project root is on sys.path so `myproject` package is importable when running from scripts/
proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.db import connection

print('Django settings loaded')
with connection.cursor() as cur:
    try:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = cur.fetchall()
        print('public tables:', tables)
    except Exception as e:
        print('error listing tables:', e)

    try:
        cur.execute("SELECT count(*) FROM users")
        print('users count:', cur.fetchone())
    except Exception as e:
        print('users count query error:', e)

    try:
        cur.execute("SELECT user_id, email, first_name, last_name FROM users LIMIT 5")
        print('sample users:', cur.fetchall())
    except Exception as e:
        print('sample users query error:', e)
