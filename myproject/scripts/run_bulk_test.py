import os
import sys
import django

# Add project root to path
proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
import json

# import the admin viewset (try both possible package names)
try:
    from admin.views import AdminUserViewSet
except Exception:
    try:
        from myproject.admin.views import AdminUserViewSet
    except Exception as e:
        print('Failed to import AdminUserViewSet:', e)
        raise

# ensure superuser exists
su, created = User.objects.get_or_create(username='auto_admin', defaults={'email': 'auto_admin@example.com'})
if created:
    su.set_password('Adminpass123!')
    su.is_superuser = True
    su.is_staff = True
    su.save()

factory = APIRequestFactory()

items = [
    {
        'username': 'bulk_test_1',
        'password': 'Testpass123!',
        'first_name': 'Bulk',
        'last_name': 'One',
        'email': 'bulk_test_1@example.com',
        'role': 'trainee',
        'teams': ''
    },
    {
        'username': 'bulk_test_2',
        'password': 'Testpass123!',
        'first_name': 'Bulk',
        'last_name': 'Two',
        'email': 'bulk_test_2@example.com',
        'role': 'trainer',
        'teams': ''
    }
]

req = factory.post('/api/admin/users/bulk_import/', items, format='json')
force_authenticate(req, user=su)
view = AdminUserViewSet.as_view({'post': 'bulk_import'})
resp = view(req)

print('bulk_import response status:', getattr(resp, 'status_code', None))
try:
    print('response data:', resp.data)
except Exception:
    print('response content not JSON-serializable, repr:', repr(resp))

# finished
print('done')
