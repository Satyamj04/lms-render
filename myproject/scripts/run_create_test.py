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

try:
    from admin.views import AdminUserViewSet
except Exception:
    from myproject.admin.views import AdminUserViewSet

# ensure a superuser exists
su, created = User.objects.get_or_create(username='auto_admin2', defaults={'email': 'auto_admin2@example.com'})
if created:
    su.set_password('Adminpass123!')
    su.is_superuser = True
    su.is_staff = True
    su.save()

factory = APIRequestFactory()

payload = {
    'username': 'frontend_user_1',
    'password': 'FrontPass123!',
    'first_name': 'Front',
    'last_name': 'User',
    'email': 'frontend_user_1@example.com',
    'role': 'trainee',
    'teams': []
}

req = factory.post('/api/admin/users/', payload, format='json')
force_authenticate(req, user=su)
view = AdminUserViewSet.as_view({'post': 'create'})
resp = view(req)

print('create response status:', getattr(resp, 'status_code', None))
try:
    print('response data:', resp.data)
except Exception:
    print('response repr:', resp)

print('done')
