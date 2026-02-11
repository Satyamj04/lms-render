

from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
import csv
import io
import openpyxl
import time
import logging
import json

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Team, UserProfile
from django.db import connection
import uuid
from django.utils import timezone
from .serializers import UserSerializer, TeamSerializer, UserCreateSerializer
from django.conf import settings
from .serializers import CourseSerializer, CourseDetailSerializer, CourseAssignmentSerializer
from .models import CourseAssignment
from rest_framework import viewsets as drf_viewsets
from rest_framework.decorators import action as drf_action
from .serializers import AuditLogSerializer
from rest_framework.decorators import api_view


def _get_lms_user_id_by_email(email):
    if not email:
        return None
    with connection.cursor() as cur:
        try:
            cur.execute("SELECT user_id FROM users WHERE email = %s LIMIT 1", [email])
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None


def _upsert_lms_team(team_name, description='', manager_email=None, trainer_email=None, created_by_email=None):
    team_id = uuid.uuid4()
    now = timezone.now()
    # Note: manager_id and trainer_id columns don't exist in teams table
    # They were in old design but current schema only has: team_id, team_name, description, status, created_at, updated_at
    created_by_id = _get_lms_user_id_by_email(created_by_email)
    with connection.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO teams (team_id, team_name, description, status, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (team_name) DO UPDATE SET description = EXCLUDED.description, updated_at = EXCLUDED.updated_at
                """,
                [team_id, team_name, description or '', 'active', now, now]
            )
            logging.getLogger(__name__).info('Team %s upserted successfully', team_name)
        except Exception as e:
            logging.getLogger(__name__).error('Failed to upsert team %s: %s', team_name, e)
            raise


def _add_lms_team_member(team_name, user_email, assigned_by_email=None, is_primary=True):
    with connection.cursor() as cur:
        try:
            cur.execute("SELECT team_id FROM teams WHERE team_name = %s LIMIT 1", [team_name])
            team_row = cur.fetchone()
            if not team_row:
                logging.getLogger(__name__).warning('Team not found: %s', team_name)
                return
            team_id = team_row[0]
            
            cur.execute("SELECT user_id FROM users WHERE email = %s LIMIT 1", [user_email])
            user_row = cur.fetchone()
            if not user_row:
                logging.getLogger(__name__).warning('User not found in LMS users table: %s', user_email)
                return
            user_id = user_row[0]
            
            assigned_by = None
            if assigned_by_email:
                cur.execute("SELECT user_id FROM users WHERE email = %s LIMIT 1", [assigned_by_email])
                a_row = cur.fetchone()
                assigned_by = a_row[0] if a_row else None
            
            cur.execute(
                """
                INSERT INTO team_members (team_id, user_id, is_primary_team, assigned_at, assigned_by)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (team_id, user_id) DO NOTHING
                """,
                [team_id, user_id, is_primary, timezone.now(), assigned_by]
            )
            logging.getLogger(__name__).info('Added user %s to team %s (team_id: %s)', user_email, team_name, team_id)
        except Exception as e:
            logging.getLogger(__name__).exception('Failed to add team member %s to %s: %s', user_email, team_name, e)


def _remove_lms_team_member(team_name, user_email):
    """Remove a user from LMS team_members (best-effort)."""
    with connection.cursor() as cur:
        try:
            cur.execute("SELECT team_id FROM teams WHERE team_name = %s LIMIT 1", [team_name])
            team_row = cur.fetchone()
            if not team_row:
                return
            team_id = team_row[0]
            cur.execute("SELECT user_id FROM users WHERE email = %s LIMIT 1", [user_email])
            user_row = cur.fetchone()
            if not user_row:
                return
            user_id = user_row[0]
            cur.execute("DELETE FROM team_members WHERE team_id = %s AND user_id = %s", [team_id, user_id])
        except Exception:
            pass


def _insert_lms_user(user_profile):
    """Best-effort insert/update into LMS `users` table using UserProfile object."""
    lms_id = uuid.uuid4()
    now = timezone.now()
    
    # UserProfile already has all the needed fields
    role = getattr(user_profile, 'role', 'trainee')
    
    with connection.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO users (user_id, first_name, last_name, email, password_hash, primary_role, status, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (email) DO UPDATE SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name, primary_role = EXCLUDED.primary_role, updated_at = EXCLUDED.updated_at
                """,
                [lms_id, user_profile.first_name or '', user_profile.last_name or '', user_profile.email, user_profile.password_hash or '', role or 'trainee', 'active', now, now]
            )
            logging.getLogger(__name__).info('Successfully inserted/updated LMS user: %s (role: %s)', user_profile.email, role)
        except Exception as exc:
            # Log error for debugging mirroring failures
            logging.getLogger(__name__).error('[_insert_lms_user] failed to insert user %s: %s', user_profile.email, repr(exc))
            raise


def _insert_lms_user_from_profile(profile):
    """Best-effort insert/update into LMS `users` table from UserProfile object."""
    now = timezone.now()
    primary_role = getattr(profile, 'role', None) or 'trainee'
    with connection.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO users (user_id, first_name, last_name, email, password_hash, primary_role, status, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (email) DO UPDATE SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name, primary_role = EXCLUDED.primary_role, updated_at = EXCLUDED.updated_at
                """,
                [str(profile.id), profile.first_name, profile.last_name, profile.email, profile.password_hash or '', primary_role, profile.status or 'active', now, now]
            )
        except Exception as exc:
            # Print error for debugging mirroring failures
            print('[_insert_lms_user_from_profile] failed to insert user', profile.email, 'error:', repr(exc))


def _insert_audit_log(action_type, entity_type, entity_id, details_obj=None, request=None, lms_user_id=None):
    """Best-effort insert into LMS `audit_logs` table.
    `details_obj` can be a dict or string; will be JSON-encoded when possible.
    Silent on failure to avoid breaking admin flows.
    """
    logger = logging.getLogger(__name__)
    try:
        log_id = uuid.uuid4()
        user_id = lms_user_id
        if user_id is None and request and getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
            try:
                user_id = _get_lms_user_id_by_email(getattr(request.user, 'email', None))
            except Exception:
                user_id = None
        details = details_obj
        if details_obj is not None and not isinstance(details_obj, str):
            try:
                details = json.dumps(details_obj)
            except Exception:
                details = str(details_obj)

        ip = None
        ua = None
        if request:
            ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')
            ua = request.META.get('HTTP_USER_AGENT')

        # Ensure we don't pass arbitrary strings into UUID columns (user_id/entity_id may be UUID type)
        entity_uuid = None
        user_uuid = None
        try:
            if entity_id is not None:
                try:
                    entity_uuid = uuid.UUID(str(entity_id))
                except Exception:
                    # keep original entity id in details if not a UUID
                    if details is None:
                        details = json.dumps({'entity_id': entity_id})
                    else:
                        try:
                            dobj = json.loads(details) if isinstance(details, str) else details
                            if isinstance(dobj, dict):
                                dobj['_entity_id'] = entity_id
                                details = json.dumps(dobj)
                            else:
                                details = json.dumps({'_details': dobj, '_entity_id': entity_id})
                        except Exception:
                            details = json.dumps({'_details': str(details), '_entity_id': entity_id})
                    entity_uuid = None
            if user_id is not None:
                try:
                    user_uuid = uuid.UUID(str(user_id))
                except Exception:
                    user_uuid = None
        except Exception:
            entity_uuid = None
            user_uuid = None

        with connection.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO audit_logs (log_id, user_id, action_type, entity_type, entity_id, details, ip_address, user_agent, timestamp)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [log_id, str(user_uuid) if user_uuid else None, action_type, entity_type, str(entity_uuid) if entity_uuid else None, details, ip, ua, timezone.now()]
                )
            except Exception as e:
                logger.exception('Failed to insert audit log: %s', e)
    except Exception as e:
        logger.exception('Audit helper failure: %s', e)


def _insert_notification(notification_type, title, message=None, link_url=None, priority='normal', status='unread', sent_via='in_app', request=None, lms_user_id=None):
    """Best-effort insert into LMS `notifications` table.
    `notification_type` should be one of the allowed types in the schema (e.g. 'system','assignment', etc.).
    """
    logger = logging.getLogger(__name__)
    try:
        nid = uuid.uuid4()
        user_id = lms_user_id
        # Ensure we have a non-null LMS user id for the notification recipient.
        # Prefer provided lms_user_id, then try to resolve/ensure the acting request.user,
        # then fall back to any existing LMS user if available. If none found, skip insert.
        if user_id is None and request and getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
            try:
                # Try to ensure the acting user exists in LMS and return its id
                try:
                    user_id = _ensure_lms_user_id_for_request(request)
                except Exception:
                    user_id = _get_lms_user_id_by_email(getattr(request.user, 'email', None))
            except Exception:
                user_id = None
        with connection.cursor() as cur:
            try:
                # Ensure sent_via is one of allowed values: 'in_app', 'email', 'both'
                sv = sent_via if str(sent_via) in ('in_app', 'email', 'both') else 'in_app'
                # If still no user_id, attempt to pick any existing LMS user as a safe fallback
                if not user_id:
                    try:
                        cur.execute("SELECT user_id FROM users LIMIT 1")
                        row = cur.fetchone()
                        if row:
                            user_id = row[0]
                    except Exception:
                        user_id = None

                if not user_id:
                    logger.warning('No LMS user_id available; skipping notification insert for title=%s', title)
                    return False

                cur.execute(
                    """
                    INSERT INTO notifications (notification_id, user_id, notification_type, title, message, link_url, priority, status, sent_via, read_at, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [str(nid), str(user_id), notification_type, title or '', message or '', link_url, priority, status, sv, None, timezone.now()]
                )
                logger.info('Inserted notification %s type=%s user=%s sent_via=%s', str(nid), notification_type, str(user_id) if user_id else None, sv)
                return True
            except Exception as e:
                logger.exception('Failed to insert notification: %s', e)
                return False
    except Exception as e:
        logger.exception('Notification helper failure: %s', e)


def _ensure_lms_user_id_for_request(request):
    """Return LMS user_id for the acting Django request.user. If not present, attempt to insert the LMS user and re-fetch the id."""
    if not request or not getattr(request, 'user', None) or not getattr(request.user, 'is_authenticated', False):
        return None
    email = getattr(request.user, 'email', None)
    if not email:
        return None
    try:
        uid = _get_lms_user_id_by_email(email)
        if uid:
            return uid
        # attempt to insert mirror of Django user into LMS users
        try:
            user_profile = UserProfile.objects.filter(email=email).first()
            if user_profile:
                _insert_lms_user(user_profile)
        except Exception:
            pass
        return _get_lms_user_id_by_email(email)
    except Exception:
        return None


def _delete_lms_user_by_email(email):
    """Remove a user and associated team_members rows from LMS by email (best-effort)."""
    if not email:
        return
    with connection.cursor() as cur:
        try:
            # delete team_members rows then users row
            cur.execute("SELECT user_id FROM users WHERE email = %s LIMIT 1", [email])
            row = cur.fetchone()
            if not row:
                return
            user_id = row[0]
            cur.execute("DELETE FROM team_members WHERE user_id = %s", [user_id])
            cur.execute("DELETE FROM users WHERE user_id = %s", [user_id])
        except Exception:
            pass


def _delete_lms_team(team_name):
    """Remove a team and its members from LMS (best-effort)."""
    if not team_name:
        return
    with connection.cursor() as cur:
        try:
            cur.execute("SELECT team_id FROM teams WHERE team_name = %s LIMIT 1", [team_name])
            row = cur.fetchone()
            if not row:
                return
            team_id = row[0]
            cur.execute("DELETE FROM team_members WHERE team_id = %s", [team_id])
            cur.execute("DELETE FROM teams WHERE team_id = %s", [team_id])
        except Exception:
            pass


class AdminUserViewSet(viewsets.ModelViewSet):
    """ViewSet to list/create/update/delete users for the admin UI."""
    queryset = UserProfile.objects.all().order_by('id')
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['id', 'email', 'first_name']

    def get_queryset(self):
        qs = UserProfile.objects.all().order_by('id')
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs

    @action(detail=False, methods=['get'])
    def me(self, request):
        if request.user and request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(email=request.user.email)
                return Response(UserSerializer(user_profile).data)
            except UserProfile.DoesNotExist:
                return Response({'detail': 'User profile not found'}, status=404)
        return Response({'detail': 'Not authenticated'}, status=401)

    def get_serializer_class(self):
        if self.action in ['create']:
            return UserCreateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        """Override destroy to mirror deletion into LMS and emit audit + notification."""
        instance = self.get_object()
        email = instance.email
        first_name = instance.first_name
        try:
            # remove from LMS tables
            try:
                _delete_lms_user_by_email(email)
            except Exception:
                pass
            # audit
            try:
                _insert_audit_log('delete_user', 'user', email, {'reason': 'deleted'}, request=request)
            except Exception:
                pass
            # notification
            try:
                lms_uid = _ensure_lms_user_id_for_request(request)
                # Tag as admin notification so it only shows to admins
                ok = _insert_notification('admin_system', 'User deleted', f'User {first_name} ({email}) deleted', link_url=None, request=request, lms_user_id=lms_uid)
                logging.getLogger(__name__).info('Notification insert for deleted(user) %s result=%s recipient_lms_id=%s', email, ok, lms_uid)
            except Exception:
                logging.getLogger(__name__).exception('Failed to insert notification for deleted user %s', email)
        except Exception:
            pass
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        """Override create to mirror new users into LMS tables (best-effort)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # attempt to mirror into LMS users table
        try:
            _insert_lms_user(user)
        except Exception:
            pass
        
        # Create Django User and Token for authentication
        try:
            from django.contrib.auth.models import User as DjangoUser
            from rest_framework.authtoken.models import Token
            
            # Get or create Django User for token auth
            django_user, created = DjangoUser.objects.get_or_create(
                username=f"user_{user.id}",
                defaults={
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            )
            
            # Generate token for immediate use
            token, _ = Token.objects.get_or_create(user=django_user)
            logging.getLogger(__name__).info('Created Django User and Token for %s', user.email)
        except Exception as e:
            logging.getLogger(__name__).exception('Failed to create Django User/Token for %s: %s', user.email, e)
        
        # Best-effort: record an audit log in LMS `audit_logs` for user creation
        try:
            _insert_audit_log('create_user', 'user', user.email or user.id, {'username': user.username, 'email': user.email}, request=request)
        except Exception:
            pass
        
        # Return the created user data
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=False, methods=['post'])
    def generate_missing_tokens(self, request):
        """Generate Django Users and Tokens for all UserProfiles that don't have them."""
        from django.contrib.auth.models import User as DjangoUser
        from rest_framework.authtoken.models import Token
        
        results = {
            'total_profiles': 0,
            'tokens_created': 0,
            'already_existed': 0,
            'failed': 0,
            'details': []
        }
        
        all_profiles = UserProfile.objects.all()
        results['total_profiles'] = all_profiles.count()
        
        for profile in all_profiles:
            try:
                # Check if Django User exists
                username = f"user_{profile.id}"
                django_user, user_created = DjangoUser.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': profile.email,
                        'first_name': profile.first_name,
                        'last_name': profile.last_name,
                    }
                )
                
                # Get or create token
                token, token_created = Token.objects.get_or_create(user=django_user)
                
                if user_created or token_created:
                    results['tokens_created'] += 1
                    results['details'].append({
                        'email': profile.email,
                        'status': 'created',
                        'user_created': user_created,
                        'token_created': token_created
                    })
                    logging.getLogger(__name__).info(
                        'Generated auth for %s (user=%s, token=%s)', 
                        profile.email, user_created, token_created
                    )
                else:
                    results['already_existed'] += 1
                    results['details'].append({
                        'email': profile.email,
                        'status': 'already_exists'
                    })
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'email': profile.email,
                    'status': 'failed',
                    'error': str(e)
                })
                logging.getLogger(__name__).exception(
                    'Failed to generate auth for %s: %s', profile.email, e
                )
        
        return Response(results, status=status.HTTP_200_OK)
        # Best-effort: insert a notification for admins
        try:
            try:
                lms_uid = _get_lms_user_id_by_email(user.email)
            except Exception:
                lms_uid = None
            if not lms_uid:
                # ensure acting admin is present in LMS users and use that id as notification recipient
                lms_uid = _ensure_lms_user_id_for_request(request) or lms_uid
            ok = _insert_notification('admin_system', 'User created', f'User {user.username} ({user.email}) created', link_url=f'/admin/users/{user.id}', request=request, lms_user_id=lms_uid)
            logging.getLogger(__name__).info('Notification insert for created user %s result=%s recipient_lms_id=%s', user.email, ok, lms_uid)
        except Exception:
            logging.getLogger(__name__).exception('Unexpected failure inserting notification for created user %s', user.email)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Handle full update of a user, with support for status changes.
        If status is 'archived', delete the user's data.
        If status is 'inactive', disable login by setting `is_active` on the User.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data

        # capture pre-update snapshot for audit diff
        try:
            pre_snapshot = {
                'username': instance.username,
                'first_name': instance.first_name,
                'last_name': instance.last_name,
                'email': instance.email,
                'role': getattr(instance.profile, 'role', None) if hasattr(instance, 'profile') else None,
                'is_active': getattr(instance, 'is_active', None),
                'teams': [t.id for t in getattr(instance.profile, 'teams').all()] if hasattr(instance, 'profile') else [],
            }
        except Exception:
            pre_snapshot = None

        # Handle archival: delete user if requested
        status_val = data.get('status') or data.get('profile', {}).get('status') if isinstance(data.get('profile', {}), dict) else data.get('status')
        if status_val and str(status_val).lower() == 'archived':
            # Best-effort: remove from LMS then delete Django user
            try:
                _delete_lms_user_by_email(instance.email)
                # log deletion
                try:
                    _insert_audit_log('delete_user', 'user', instance.email, {'reason': 'archived'}, request=request)
                except Exception:
                    pass
                try:
                    # insert notification for admins about this deletion
                    lms_uid = _ensure_lms_user_id_for_request(request)
                    ok = _insert_notification('admin_system', 'User deleted', f'User {instance.username} ({instance.email}) deleted (archived)', link_url=f'/admin/users/{instance.id}', request=request, lms_user_id=lms_uid)
                    logging.getLogger(__name__).info('Notification insert for deleted(user archived) %s result=%s recipient_lms_id=%s', instance.email, ok, lms_uid)
                except Exception:
                    logging.getLogger(__name__).exception('Failed to insert notification for archived user %s', instance.email)
            except Exception:
                pass
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # Update basic user fields
        changed = False
        for fld in ('username', 'first_name', 'last_name', 'email'):
            if fld in data:
                setattr(instance, fld, data.get(fld))
                changed = True


        # Update profile role and is_active/status
        profile = getattr(instance, 'profile', None)
        if profile:
            if 'role' in data:
                profile.role = data.get('role')
            # support either 'is_active' boolean or 'status' string in request
            if 'is_active' in data:
                is_act = bool(data.get('is_active'))
                profile.is_active = is_act
                instance.is_active = is_act
        if 'status' in data:
            st = str(data.get('status')).lower()
            if st == 'inactive':
                profile.is_active = False
                instance.is_active = False
            elif st == 'active':
                profile.is_active = True
                instance.is_active = True
        if profile:
            profile.save()

        if changed:
            instance.save()

        # Mirror change to LMS users table (best-effort)
        try:
            _insert_lms_user(instance)
        except Exception:
            pass

        # construct post-update snapshot and compute diff for audit
        try:
            post_snapshot = {
                'username': instance.username,
                'first_name': instance.first_name,
                'last_name': instance.last_name,
                'email': instance.email,
                'role': getattr(instance.profile, 'role', None) if hasattr(instance, 'profile') else None,
                'is_active': getattr(instance, 'is_active', None),
                'teams': [t.id for t in getattr(instance.profile, 'teams').all()] if hasattr(instance, 'profile') else [],
            }
            diff = {}
            if pre_snapshot:
                for k in post_snapshot.keys():
                    if pre_snapshot.get(k) != post_snapshot.get(k):
                        diff[k] = {'before': pre_snapshot.get(k), 'after': post_snapshot.get(k)}
            else:
                diff = {'after': post_snapshot}
            _insert_audit_log('update_user', 'user', instance.email or instance.id, {'changes': diff, 'request_payload': data}, request=request)
        except Exception:
            # don't break the update on audit failures
            pass
        try:
            lms_uid = _get_lms_user_id_by_email(instance.email)
            if not lms_uid:
                lms_uid = _ensure_lms_user_id_for_request(request) or lms_uid
            ok = _insert_notification('admin_system', 'User updated', f'User {instance.username} updated', link_url=f'/admin/users/{instance.id}', request=request, lms_user_id=lms_uid)
            logging.getLogger(__name__).info('Notification insert for updated user %s result=%s recipient_lms_id=%s', instance.email, ok, lms_uid)
        except Exception:
            logging.getLogger(__name__).exception('Unexpected failure inserting notification for updated user %s', instance.email)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def bulk_import(self, request):
        return _bulk_import_handler(request)


# Admin metrics endpoint
@api_view(["GET"])
def metrics(request):
    """Return aggregated LMS metrics for admin dashboard.
    Allow access to authenticated staff or superuser accounts. Returns 403 otherwise.
    """
    # In development allow unauthenticated access when DEBUG is enabled so frontend can fetch metrics
    if not getattr(settings, 'DEBUG', False):
        if not (request.user and request.user.is_authenticated and (getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False))):
            return Response({'detail': 'Forbidden'}, status=403)

    data = {}
    logger = logging.getLogger(__name__)

    try:
        from trainer.models import Profile, Course, Enrollment, Team, Test
        from django.db.models import Avg, Count
        
        # Users
        data["total_users"] = Profile.objects.count()
        data["active_users"] = Profile.objects.filter(status='active').count()

        # Courses
        data["total_courses"] = Course.objects.count()
        data["active_courses"] = Course.objects.filter(status='published').count()

        # Average completion from enrollments
        avg_completion = Enrollment.objects.filter(
            progress_percentage__isnull=False
        ).aggregate(avg=Avg('progress_percentage'))
        data["avg_course_completion"] = float(avg_completion['avg'] or 0)

        # Teams summary
        data["total_teams"] = Team.objects.count()

        # Recent activity (get recent enrollments as activity)
        recent_enrollments = Enrollment.objects.select_related('user', 'course').order_by('-assigned_at')[:20]
        data["recent_activity"] = [
            {
                "id": str(e.id),
                "user_id": str(e.user.id),
                "action": "enrollment",
                "entity_type": "course",
                "entity_id": str(e.course.id),
                "details": f"Enrolled in {e.course.title}",
                "timestamp": e.assigned_at.isoformat() if e.assigned_at else None
            }
            for e in recent_enrollments
        ]

        # System health
        from django.utils import timezone
        import time
        t0 = time.time()
        Profile.objects.exists()  # Simple DB query to test connection
        t1 = time.time()
        data["system"] = {
            "db_ok": True,
            "query_ms": int((t1 - t0) * 1000),
            "server_time": timezone.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"Error fetching metrics: {exc}", exc_info=True)
        return Response({"detail": "Failed to gather metrics", "error": str(exc)}, status=500)

    return Response(data)


@api_view(["GET"])
def progress(request):
    """Return progress data: team aggregates and recent user_progress rows."""
    # In development allow unauthenticated access when DEBUG is enabled so frontend can fetch
    if not getattr(settings, 'DEBUG', False):
        if not (request.user and request.user.is_authenticated and (getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False))):
            return Response({'detail': 'Forbidden'}, status=403)

    limit = int(request.query_params.get('limit', 200))
    logger = logging.getLogger(__name__)
    data = {'teams': [], 'users': []}
    try:
        with connection.cursor() as cur:
            # Team aggregates: average completion across team members
            try:
                cur.execute(
                    """
                    SELECT t.team_id, t.team_name, COUNT(tm.user_id) as members, COALESCE(AVG(up.completion_percentage),0) as avg_completion
                    FROM teams t
                    LEFT JOIN team_members tm ON tm.team_id = t.team_id
                    LEFT JOIN user_progress up ON up.user_id = tm.user_id
                    GROUP BY t.team_id, t.team_name
                    ORDER BY avg_completion DESC
                    LIMIT %s
                    """,
                    [limit]
                )
                rows = cur.fetchall()
                data['teams'] = [{'id': str(r[0]), 'name': r[1], 'members': r[2], 'avg_completion': float(r[3])} for r in rows]
            except Exception as e:
                logger.exception('Error fetching team progress: %s', e)

            # Recent user progress entries
            try:
                cur.execute(
                    """
                    SELECT up.progress_id, up.user_id, u.first_name, u.last_name, up.course_id, up.completion_percentage, up.total_points_earned, up.average_score, up.modules_completed, up.total_modules, up.last_activity
                    FROM user_progress up LEFT JOIN users u ON u.user_id = up.user_id
                    ORDER BY up.last_activity DESC NULLS LAST LIMIT %s
                    """,
                    [limit]
                )
                rows = cur.fetchall()
                users = []
                for r in rows:
                    users.append({
                        'id': str(r[0]),
                        'user_id': str(r[1]) if r[1] else None,
                        'first_name': r[2] or None,
                        'last_name': r[3] or None,
                        'course_id': str(r[4]) if r[4] else None,
                        'completion_percentage': r[5],
                        'total_points_earned': r[6],
                        'average_score': r[7],
                        'modules_completed': r[8],
                        'total_modules': r[9],
                        'last_activity': r[10].isoformat() if r[10] else None,
                    })
                data['users'] = users
            except Exception as e:
                logger.exception('Error fetching user progress: %s', e)

    except Exception as exc:
        logger.error(f"Error fetching progress: {exc}")
        return Response({'detail': 'Failed to gather progress', 'error': str(exc)}, status=500)

    return Response(data)


@api_view(["GET"])
def lms_teams(request):
    """Return teams from the LMS `teams` table with member details (best-effort).
    Supports optional `limit` query param.
    """
    limit = int(request.query_params.get('limit', 1000))
    logger = logging.getLogger(__name__)
    teams = []
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT team_id, team_name, description, status, created_at, updated_at FROM teams ORDER BY team_name LIMIT %s", [limit])
            rows = cur.fetchall()
            for r in rows:
                team_id = r[0]

                # fetch members
                members = []
                try:
                    cur.execute("SELECT tm.user_id, u.first_name, u.last_name, u.email, tm.is_primary_team, tm.assigned_at FROM team_members tm LEFT JOIN users u ON u.user_id = tm.user_id WHERE tm.team_id = %s", [team_id])
                    mrows = cur.fetchall()
                    for m in mrows:
                        members.append({
                            'user_id': str(m[0]) if m[0] else None,
                            'first_name': m[1] or None,
                            'last_name': m[2] or None,
                            'email': m[3] or None,
                            'is_primary_team': bool(m[4]) if m[4] is not None else None,
                            'assigned_at': m[5].isoformat() if m[5] else None,
                        })
                except Exception:
                    members = []

                teams.append({
                    'team_id': str(team_id),
                    'team_name': r[1],
                    'description': r[2],
                    'status': r[3],
                    'manager': None,  # manager_id column doesn't exist in current schema
                    'created_by': None,  # created_by column doesn't exist in current schema
                    'created_at': r[4].isoformat() if r[4] else None,
                    'updated_at': r[5].isoformat() if r[5] else None,
                    'members': members,
                })
    except Exception as e:
        logger.exception('Failed to fetch LMS teams: %s', e)
        return Response({'detail': 'Failed to fetch teams', 'error': str(e)}, status=500)

    return Response(teams)

def _bulk_import_handler(request):
        """Accepts a CSV/Excel file upload or JSON list to create multiple users.

        Supports JSON body, CSV, and Excel (.xls/.xlsx). Positional order: username,password,first_name,last_name,email,role,teams
        """

        # Support JSON array body
        if request.content_type and 'application/json' in request.content_type:
            items = request.data if isinstance(request.data, list) else []
        else:
            file_obj = request.FILES.get('file')
            if not file_obj:
                return Response({'detail': 'No file provided', 'uploaded_files': list(request.FILES.keys())}, status=status.HTTP_400_BAD_REQUEST)

            fname = getattr(file_obj, 'name', '') or ''
            ext = fname.lower().split('.')[-1] if '.' in fname else ''
            items = []

            if ext in ('xls', 'xlsx'):
                try:
                    wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
                    ws = wb.active
                    rows = list(ws.iter_rows(values_only=True))
                    if not rows:
                        return Response({'detail': 'Excel file is empty'}, status=status.HTTP_400_BAD_REQUEST)

                    first = [str(c).strip().lower() if c is not None else '' for c in rows[0]]
                    if any(h in ('username', 'password') for h in first):
                        headers = [str(h).strip().lower() if h is not None else '' for h in rows[0]]
                        for r in rows[1:]:
                            rowdict = {}
                            for i, h in enumerate(headers):
                                key = h
                                rowdict[key] = (r[i] if i < len(r) else '')
                            items.append({k: (str(v) if v is not None else '') for k, v in rowdict.items()})
                    else:
                        for r in rows:
                            if not r or all((c is None or str(c).strip() == '') for c in r):
                                continue
                            items.append({
                                'username': str(r[0]).strip() if len(r) > 0 and r[0] is not None else '',
                                'password': str(r[1]).strip() if len(r) > 1 and r[1] is not None else '',
                                'first_name': str(r[2]).strip() if len(r) > 2 and r[2] is not None else '',
                                'last_name': str(r[3]).strip() if len(r) > 3 and r[3] is not None else '',
                                'email': str(r[4]).strip() if len(r) > 4 and r[4] is not None else '',
                                'role': str(r[5]).strip() if len(r) > 5 and r[5] is not None else 'trainee',
                                'teams': str(r[6]).strip() if len(r) > 6 and r[6] is not None else '',
                            })
                except Exception as exc:
                    return Response({'detail': 'Failed to parse Excel file', 'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            else:
                try:
                    raw = file_obj.read()
                except Exception as exc:
                    return Response({'detail': 'Unable to read uploaded file bytes', 'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    decoded = raw.decode('utf-8')
                except Exception as exc_utf:
                    try:
                        decoded = raw.decode('latin-1')
                    except Exception as exc_latin:
                        return Response({'detail': 'Unable to decode file. Tried utf-8 and latin-1.', 'errors': {'utf8': str(exc_utf), 'latin1': str(exc_latin)}, 'uploaded_filename': getattr(file_obj, 'name', None), 'uploaded_size': len(raw)}, status=status.HTTP_400_BAD_REQUEST)

                sample = decoded[:4096]
                has_header = csv.Sniffer().has_header(sample)
                if has_header:
                    reader = csv.DictReader(io.StringIO(decoded))
                    items = [row for row in reader]
                else:
                    reader = csv.reader(io.StringIO(decoded))
                    for row in reader:
                        if not row or all(not cell.strip() for cell in row):
                            continue
                        items.append({
                            'username': row[0].strip() if len(row) > 0 else '',
                            'password': row[1].strip() if len(row) > 1 else '',
                            'first_name': row[2].strip() if len(row) > 2 else '',
                            'last_name': row[3].strip() if len(row) > 3 else '',
                            'email': row[4].strip() if len(row) > 4 else '',
                            'role': row[5].strip() if len(row) > 5 else 'trainee',
                            'teams': row[6].strip() if len(row) > 6 else '',
                        })

        created = []
        errors = []
        with transaction.atomic():
            for idx, item in enumerate(items):
                try:
                    # normalize keys
                    username = item.get('username') or item.get('user')
                    password = item.get('password') or item.get('pass') or item.get('pwd')
                    if not username or not password:
                        raise ValueError('username and password are required')

                    profile_teams = []
                    teams_field = item.get('teams') or ''
                    if teams_field:
                        # teams can be ids or names, comma separated
                        for t in [t.strip() for t in teams_field.split(',') if t.strip()]:
                            if t.isdigit():
                                team = Team.objects.filter(id=int(t)).first()
                                if team:
                                    profile_teams.append(team)
                            else:
                                team, team_created = Team.objects.get_or_create(name=t)
                                profile_teams.append(team)
                                if team_created:
                                    # Mirror new team into LMS and emit audit + notification (best-effort)
                                    try:
                                        _upsert_lms_team(
                                            team.name,
                                            description=team.description if getattr(team, 'description', None) else '',
                                            manager_email=None,
                                            created_by_email=(request.user.email if request.user and request.user.is_authenticated else None)
                                        )
                                    except Exception:
                                        pass
                                    try:
                                        _insert_audit_log('create_team', 'team', team.name or str(team.team_id), {'description': team.description, 'members': []}, request=request)
                                    except Exception:
                                        pass
                                    try:
                                        lms_uid = _ensure_lms_user_id_for_request(request)
                                        ok = _insert_notification('admin_system', 'Team created', f'Team {team.name} created', link_url=f'/admin/teams/{team.team_id}', request=request, lms_user_id=lms_uid)
                                        logging.getLogger(__name__).info('Notification insert for created team (bulk) %s result=%s recipient_lms_id=%s', team.name, ok, lms_uid)
                                    except Exception:
                                        logging.getLogger(__name__).exception('Failed inserting notification for bulk-created team %s', team.name)

                    user_payload = {
                        'username': username,
                        'password': password,
                        'first_name': item.get('first_name') or '',
                        'last_name': item.get('last_name') or '',
                        'email': item.get('email') or '',
                        'role': item.get('role') or 'trainee',
                        'teams': [t.id for t in profile_teams],
                    }
                    serializer = UserCreateSerializer(data=user_payload)
                    serializer.is_valid(raise_exception=True)
                    user = serializer.save()
                    # Mirror to LMS schema tables if available (best-effort)
                    try:
                        lms_id = uuid.uuid4()
                        now = timezone.now()
                        with connection.cursor() as cur:
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO users (user_id, first_name, last_name, email, password_hash, primary_role, status, created_at, updated_at)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                    ON CONFLICT (email) DO UPDATE SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name, primary_role = EXCLUDED.primary_role, updated_at = EXCLUDED.updated_at
                                    """,
                                    [lms_id, user.first_name, user.last_name, user.email, user.password, user.profile.role, 'active', now, now]
                                )
                            except Exception:
                                pass
                    except Exception:
                        # non-fatal mirroring errors should not stop import
                        pass
                    # Best-effort: insert audit log for created user
                    try:
                        try:
                            lms_user_id = _get_lms_user_id_by_email(user.email)
                        except Exception:
                            lms_user_id = None
                        log_id = uuid.uuid4()
                        details = json.dumps({'username': user.username, 'email': user.email, 'created_by': getattr(request.user, 'email', None)})
                        ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')
                        ua = request.META.get('HTTP_USER_AGENT')
                        with connection.cursor() as cur:
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO audit_logs (log_id, user_id, action_type, entity_type, entity_id, details, ip_address, user_agent, timestamp)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                    """,
                                    [log_id, lms_user_id, 'create_user', 'user', lms_user_id or user.email, details, ip, ua, timezone.now()]
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
                    created.append({'id': user.id, 'username': user.username})
                except Exception as exc:
                    errors.append({'row': idx + 1, 'error': str(exc)})

        # After creating users, emit per-user notifications and a summary notification for the acting admin
        try:
            for urow in created:
                try:
                    user_obj = User.objects.get(id=urow['id'])
                    try:
                        lms_uid = _get_lms_user_id_by_email(user_obj.email)
                    except Exception:
                        lms_uid = None
                    if not lms_uid:
                        lms_uid = _ensure_lms_user_id_for_request(request) or lms_uid
                    ok = _insert_notification('admin_system', 'User created', f'User {user_obj.username} ({user_obj.email}) created', link_url=f'/admin/users/{user_obj.id}', request=request, lms_user_id=lms_uid)
                    logging.getLogger(__name__).info('Notification insert for bulk created user %s result=%s recipient_lms_id=%s', user_obj.email, ok, lms_uid)
                except Exception:
                    logging.getLogger(__name__).exception('Failed to insert notification for bulk created user id=%s', urow.get('id'))
        except Exception:
            logging.getLogger(__name__).exception('Bulk import per-user notification loop failed')

        try:
            lms_uid = _ensure_lms_user_id_for_request(request)
            ok = _insert_notification('admin_system', 'Bulk import completed', f'Bulk import finished: {len(created)} created, {len(errors)} errors', link_url=None, request=request, lms_user_id=lms_uid)
            logging.getLogger(__name__).info('Notification insert for bulk import summary result=%s recipient_lms_id=%s', ok, lms_uid)
        except Exception:
            logging.getLogger(__name__).exception('Failed to insert notification for bulk import summary')

        return Response({'created': created, 'errors': errors}, status=status.HTTP_200_OK)


# class TeamViewSet(viewsets.ModelViewSet):
#     queryset = Team.objects.prefetch_related('members').all().order_by('name')
#     serializer_class = TeamSerializer
#     filter_backends = [filters.SearchFilter, filters.OrderingFilter]
#     search_fields = ['name']
#     ordering_fields = ['name', 'created_at']

#     def create(self, request, *args, **kwargs):        
#         name = request.data.get('name')
#         description = request.data.get('description', '')
#         members = request.data.get('members', []) or []
#         manager = request.data.get('manager')
#         trainer = request.data.get('trainer')

#         with transaction.atomic():
#             team = Team.objects.create(name=name, description=description)

#             # assign members (expects list of UserProfile ids)
#             for uid in members:
#                 try:
#                     profile = UserProfile.objects.get(id=uid)
#                     profile.teams.add(team)
#                 except UserProfile.DoesNotExist:
#                     continue

#             # assign manager (UserProfile id)
#             mprofile = None
#             if manager:
#                 try:
#                     mprofile = UserProfile.objects.get(id=manager)
#                     mprofile.role = 'manager'
#                     mprofile.teams.add(team)
#                     mprofile.save()
#                 except UserProfile.DoesNotExist:
#                     mprofile = None

#             # assign trainer (UserProfile id)
#             tr_profile = None
#             if trainer:
#                 try:
#                     tr_profile = UserProfile.objects.get(id=trainer)
#                     tr_profile.role = 'trainer'
#                     tr_profile.teams.add(team)
#                     tr_profile.save()
#                 except UserProfile.DoesNotExist:
#                     tr_profile = None

#             # attempt to mirror team into LMS
#             try:
#                 _upsert_lms_team(
#                     team.name,
#                     description=team.description,
#                     manager_email=(mprofile.email if mprofile else None),
#                     created_by_email=(request.user.email if request.user and request.user.is_authenticated else None)
#                 )
#             except Exception:
#                 pass

#             # add members to LMS team_members
#             for uid in members:
#                 try:
#                     profile = UserProfile.objects.get(id=uid)
#                     _add_lms_team_member(
#                         team.name,
#                         profile.email,
#                         assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                     )
#                 except Exception:
#                     continue

#             # ensure manager is in LMS team_members and LMS users
#             if mprofile:
#                 try:
#                     _insert_lms_user(mprofile)
#                     _add_lms_team_member(
#                         team.name,
#                         mprofile.email,
#                         assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                     )
#                 except Exception:
#                     pass

#             # ensure trainer is in LMS team_members and LMS users
#             if tr_profile:
#                 try:
#                     _insert_lms_user(tr_profile)
#                     _add_lms_team_member(
#                         team.name,
#                         tr_profile.email,
#                         assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                     )
#                 except Exception:
#                     pass

#         serializer = self.get_serializer(team)
#         headers = self.get_success_headers(serializer.data)
#         # audit: team created
#         try:
#             _insert_audit_log('create_team', 'team', team.name or str(team.team_id), {'description': team.description}, request=request)
#         except Exception:
#             pass
#         try:
#             lms_uid = _ensure_lms_user_id_for_request(request)
#             ok = _insert_notification('admin_system', 'Team created', f'Team {team.name} created', link_url=f'/admin/teams/{team.team_id}', request=request, lms_user_id=lms_uid)
#             logging.getLogger(__name__).info('Notification insert for created team %s result=%s recipient_lms_id=%s', team.name, ok, lms_uid)
#         except Exception:
#             logging.getLogger(__name__).exception('Unexpected failure inserting notification for created team %s', team.name)
#         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

#     def destroy(self, request, *args, **kwargs):
#         """Delete a team and remove all associated members and LMS records."""
#         instance = self.get_object()
#         # remove team association from profiles and mirror removals
#         members = list(instance.members.all())
#         for prof in members:
#             try:
#                 prof.teams.remove(instance)
#                 if hasattr(prof, 'user') and prof.user.email:
#                     _remove_lms_team_member(instance.name, prof.user.email)
#             except Exception:
#                 pass

#         # Mirror deletion to LMS: remove team_members rows and the team
#         try:
#             _delete_lms_team(instance.name)
#         except Exception:
#             pass

#         # audit: team deleted
#         try:
#             _insert_audit_log('delete_team', 'team', instance.name or instance.id, {'members': [p.user.id for p in members if hasattr(p, 'user')]}, request=request)
#         except Exception:
#             pass
#         try:
#             lms_uid = _ensure_lms_user_id_for_request(request)
#             ok = _insert_notification('admin_system', 'Team deleted', f'Team {instance.name} deleted', link_url=None, request=request, lms_user_id=lms_uid)
#             logging.getLogger(__name__).info('Notification insert for deleted team %s result=%s recipient_lms_id=%s', instance.name, ok, lms_uid)
#         except Exception:
#             logging.getLogger(__name__).exception('Unexpected failure inserting notification for deleted team %s', instance.name)

#         instance.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)

#     def update(self, request, *args, **kwargs):
#         partial = kwargs.pop('partial', False)
#         instance = self.get_object()
#         name = request.data.get('name')
#         description = request.data.get('description')
#         members = request.data.get('members', None)
#         manager = request.data.get('manager', None)
#         trainer = request.data.get('trainer', None)

#         with transaction.atomic():
#             if name is not None:
#                 instance.name = name
#             if description is not None:
#                 instance.description = description
#             instance.save()

#             # Update members: if provided, sync membership list
#             if members is not None:
#                 # current profiles (UserProfile instances)
#                 current_profiles = list(instance.members.all())
#                 current_profile_ids = {str(p.id) for p in current_profiles}
#                 new_profile_ids = {str(m) for m in members}

#                 # remove team from users not in new list
#                 removed_profiles = []
#                 for profile in current_profiles:
#                     if str(profile.id) not in new_profile_ids:
#                         profile.teams.remove(instance)
#                         removed_profiles.append(profile)

#                 # add team to new members
#                 for uid in new_profile_ids:
#                     try:
#                         profile = UserProfile.objects.get(id=uid)
#                         profile.teams.add(instance)
#                         TeamMember.objects.get_or_create(team=instance, user=profile)
#                         added_profile_ids.add(str(profile.id))
#                     except UserProfile.DoesNotExist:
#                         continue

#             # assign manager: demote previous managers in this team and set new manager
#             if manager is not None:
#                 # demote any existing manager profiles for this team
#                 for prof in instance.members.filter(role='manager'):
#                     prof.role = 'trainee'
#                     prof.save()
#                 if manager:
#                     try:
#                         mprofile = UserProfile.objects.get(id=manager)
#                         mprofile.role = 'manager'
#                         mprofile.teams.add(instance)
#                         mprofile.save()
#                         # update LMS users primary_role and ensure team_members row
#                         try:
#                             _insert_lms_user_from_profile(mprofile)
#                             _add_lms_team_member(
#                                 instance.name,
#                                 mprofile.email,
#                                 assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                             )
#                         except Exception:
#                             pass
#                     except UserProfile.DoesNotExist:
#                         pass

#             # assign trainer: demote previous trainers in this team and set new trainer
#             if trainer is not None:
#                 # demote any existing trainer profiles for this team
#                 for prof in instance.members.filter(role='trainer'):
#                     prof.role = 'trainee'
#                     prof.save()
#                 if trainer:
#                     try:
#                         tr_profile = UserProfile.objects.get(id=trainer)
#                         tr_profile.role = 'trainer'
#                         tr_profile.teams.add(instance)
#                         tr_profile.save()
#                         # update LMS users primary_role and ensure team_members row
#                         try:
#                             _insert_lms_user_from_profile(tr_profile)
#                             _add_lms_team_member(
#                                 instance.name,
#                                 tr_profile.email,
#                                 assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                             )
#                         except Exception:
#                             pass
#                     except UserProfile.DoesNotExist:
#                         pass

#             # Mirror team changes to LMS tables: update team and members
#             try:
#                 manager_email = None
#                 if manager:
#                     try:
#                         mprofile = UserProfile.objects.get(id=manager)
#                         manager_email = mprofile.email
#                     except UserProfile.DoesNotExist:
#                         pass
#                 _upsert_lms_team(
#                     instance.name,
#                     description=instance.description,
#                     manager_email=manager_email,
#                     created_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                 )
#             except Exception:
#                 pass

#             # remove members from LMS
#             try:
#                 for profile_id in removed_profile_ids:
#                     try:
#                         p = UserProfile.objects.get(id=profile_id)
#                         _remove_lms_team_member(instance.name, p.email)
#                     except Exception:
#                         continue
#             except UnboundLocalError:
#                 # no members were provided
#                 pass

#             # add new members to LMS
#             try:
#                 for profile_id in added_profile_ids:
#                     try:
#                         p = UserProfile.objects.get(id=profile_id)
#                         _add_lms_team_member(
#                             instance.name,
#                             p.email,
#                             assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                         )
#                     except Exception:
#                         continue
#             except UnboundLocalError:
#                 # no newly added members
#                 pass

#         # assign trainer: demote previous trainers in this team and set new trainer
#         trainer = request.data.get('trainer', None)
#         if trainer is not None:
#             for prof in instance.members.filter(role='trainer'):
#                 prof.role = 'trainee'
#                 prof.save()
#             if trainer:
#                 try:
#                     tr_profile = UserProfile.objects.get(id=trainer)
#                     tr_profile.role = 'trainer'
#                     # Use TeamMember directly to add (avoid .add() with explicit through)
#                     from .models import TeamMember
#                     TeamMember.objects.get_or_create(team=instance, user=tr_profile)
#                     tr_profile.save()
#                     # update LMS users primary_role and ensure team_members row
#                     try:
#                         _insert_lms_user_from_profile(tr_profile)
#                         _add_lms_team_member(
#                             instance.name,
#                             tr_profile.email,
#                             assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
#                         )
#                     except Exception:
#                         pass
#                 except UserProfile.DoesNotExist:
#                     pass

#         serializer = self.get_serializer(instance)
#         # audit: team updated
#         try:
#             _insert_audit_log('update_team', 'team', instance.name or instance.id, {'name': instance.name, 'description': instance.description, 'manager': manager, 'members_added': list(added_user_ids) if 'added_user_ids' in locals() else [], 'members_removed': list(removed_user_ids) if 'removed_user_ids' in locals() else []}, request=request)
#         except Exception:
#             pass
#         try:
#             lms_uid = _ensure_lms_user_id_for_request(request)
#             ok = _insert_notification('admin_system', 'Team updated', f'Team {instance.name} updated', link_url=f'/admin/teams/{instance.id}', request=request, lms_user_id=lms_uid)
#             logging.getLogger(__name__).info('Notification insert for updated team %s result=%s recipient_lms_id=%s', instance.name, ok, lms_uid)
#         except Exception:
#             logging.getLogger(__name__).exception('Unexpected failure inserting notification for updated team %s', instance.name)
#         return Response(serializer.data)
class TeamViewSet(viewsets.ModelViewSet):
    """ViewSet for managing teams (backed by LMS PostgreSQL tables).
    Note: No Django Team model exists; all data comes from LMS `teams` table.
    """
    serializer_class = TeamSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
 
    def get_queryset(self):
        """Return empty queryset since we don't use Django ORM."""
        return []
 
    def list(self, request):
        """Fetch teams from LMS PostgreSQL with member details."""
        try:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT
                      t.team_id,
                      t.team_name,
                      t.description,
                      t.created_at,
                      COUNT(DISTINCT tm.user_id) as members_count,
                      json_agg(json_build_object(
                        'user_id', u2.user_id::text,
                        'first_name', u2.first_name,
                        'last_name', u2.last_name,
                        'email', u2.email
                      ) ORDER BY u2.first_name, u2.last_name) FILTER (WHERE u2.user_id IS NOT NULL) as members
                    FROM teams t
                    LEFT JOIN team_members tm ON t.team_id = tm.team_id
                    LEFT JOIN users u2 ON tm.user_id = u2.user_id
                    GROUP BY t.team_id, t.team_name, t.description, t.created_at
                    ORDER BY t.team_name
                """)
                rows = cur.fetchall()
                teams = [{
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2] or '',
                    'created_at': row[3],
                    'members_count': row[4] or 0,
                    'manager_id': None,
                    'manager_name': None,
                    'trainer_id': None,
                    'trainer_name': None,
                    'members': row[5] or [],
                } for row in rows]
            return Response(teams)
        except Exception as e:
            logging.getLogger(__name__).exception('Error listing teams: %s', e)
            return Response({'error': str(e)}, status=500)
 
    def create(self, request, *args, **kwargs):
        """Create a team in LMS tables (no Django Team model)."""
        from django.db import transaction
        
        name = request.data.get('name')
        description = request.data.get('description', '')
        members = request.data.get('members', []) or []
        manager = request.data.get('manager')  # User ID or email
        trainer = request.data.get('trainer')  # User ID or email
 
        if not name:
            return Response({'error': 'name is required'}, status=400)
 
        try:
            # Use atomic transaction for team creation
            with transaction.atomic():
                # Create team in LMS
                manager_email = None
                if manager:
                    try:
                        # Try to get UserProfile by ID (handles both int and UUID string)
                        user_profile = UserProfile.objects.get(id=manager)
                        manager_email = user_profile.email
                        # Ensure manager exists in LMS users table
                        try:
                            _insert_lms_user(user_profile)
                            logging.getLogger(__name__).info('Manager %s inserted into LMS users', manager_email)
                        except Exception as e:
                            logging.getLogger(__name__).error('Failed to insert manager into LMS users: %s', e)
                    except (ValueError, UserProfile.DoesNotExist) as e:
                        logging.getLogger(__name__).warning('Manager lookup failed for %s: %s', manager, e)
                        # If not a valid ID, treat as email directly
                        manager_email = manager if isinstance(manager, str) and '@' in manager else None
                
                # Handle trainer
                trainer_email = None
                if trainer:
                    try:
                        # Try to get UserProfile by ID (handles both int and UUID string)
                        user_profile = UserProfile.objects.get(id=trainer)
                        trainer_email = user_profile.email
                        # Ensure trainer exists in LMS users table
                        try:
                            _insert_lms_user(user_profile)
                            logging.getLogger(__name__).info('Trainer %s inserted into LMS users', trainer_email)
                        except Exception as e:
                            logging.getLogger(__name__).error('Failed to insert trainer into LMS users: %s', e)
                    except (ValueError, UserProfile.DoesNotExist) as e:
                        logging.getLogger(__name__).warning('Trainer lookup failed for %s: %s', trainer, e)
                        # If not a valid ID, treat as email directly
                        trainer_email = trainer if isinstance(trainer, str) and '@' in trainer else None
 
                _upsert_lms_team(
                    name,
                    description=description,
                    manager_email=manager_email,
                    trainer_email=trainer_email,
                    created_by_email=request.user.email if request.user and request.user.is_authenticated else None
                )
 
                # Add members to team_members in LMS
                for member_id in members:
                    try:
                        # Try to get UserProfile by ID (handles both int and UUID string)
                        user_profile = UserProfile.objects.get(id=member_id)
                        member_email = user_profile.email
                        # Ensure user exists in LMS users table before adding to team
                        try:
                            _insert_lms_user(user_profile)
                            logging.getLogger(__name__).info('Member %s inserted into LMS users', member_email)
                        except Exception as e:
                            logging.getLogger(__name__).error('Failed to insert member %s into LMS users: %s', member_email, e)
                        
                        # Add member to team
                        _add_lms_team_member(
                            name,
                            member_email,
                            assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
                        )
                        logging.getLogger(__name__).info('Added member %s to team %s', member_email, name)
                    except (ValueError, UserProfile.DoesNotExist) as e:
                        logging.getLogger(__name__).error('Member lookup failed for %s: %s', member_id, e)
                        continue
                    except Exception as e:
                        logging.getLogger(__name__).exception('Error adding member %s to team: %s', member_id, e)
                        continue
 
                # Fetch and return the created team (within transaction)
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT t.team_id, t.team_name, t.description, t.created_at, COUNT(DISTINCT tm.user_id) as members_count
                        FROM teams t
                        LEFT JOIN team_members tm ON t.team_id = tm.team_id
                        WHERE t.team_name = %s
                        GROUP BY t.team_id, t.team_name, t.description, t.created_at
                        LIMIT 1
                    """, [name])
                    row = cur.fetchone()
                    if row:
                        team_data = {
                            'id': str(row[0]),
                            'name': row[1],
                            'description': row[2] or '',
                            'created_at': row[3],
                            'members_count': row[4] or 0,
                            'manager_id': None,
                            'manager_name': None,
                            'trainer_id': None,
                            'trainer_name': None,
                        }
                    else:
                        return Response({'error': 'Team created but could not retrieve'}, status=201)
            
            # Audit and notifications AFTER transaction completes successfully
            try:
                _insert_audit_log('create_team', 'team', name, {'description': description, 'members': members}, request=request)
            except Exception:
                pass
            try:
                lms_uid = _ensure_lms_user_id_for_request(request)
                _insert_notification('system', 'Team created', f'Team {name} created', link_url=f'/admin/teams', request=request, lms_user_id=lms_uid)
            except Exception:
                pass
            
            return Response(team_data, status=201)
        except Exception as e:
            logging.getLogger(__name__).exception('Error creating team: %s', e)
            return Response({'error': str(e)}, status=500)
 
    def destroy(self, request, team_pk=None, pk=None, *args, **kwargs):
        """Delete a team from LMS tables."""
        team_id = team_pk or pk or kwargs.get('pk')
        if not team_id:
            return Response({'error': 'Team ID required'}, status=400)
 
        try:
            # Get team name from LMS
            team_name = None
            with connection.cursor() as cur:
                cur.execute("SELECT team_name FROM teams WHERE team_id = %s LIMIT 1", [team_id])
                row = cur.fetchone()
                if row:
                    team_name = row[0]
 
            if not team_name:
                return Response({'error': 'Team not found'}, status=404)
 
            # Delete from LMS
            _delete_lms_team(team_name)
 
            # Audit and notifications
            try:
                _insert_audit_log('delete_team', 'team', team_name, {}, request=request)
            except Exception:
                pass
            try:
                lms_uid = _ensure_lms_user_id_for_request(request)
                _insert_notification('system', 'Team deleted', f'Team {team_name} deleted', link_url=None, request=request, lms_user_id=lms_uid)
            except Exception:
                pass
 
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logging.getLogger(__name__).exception('Error deleting team: %s', e)
            return Response({'error': str(e)}, status=500)
 
    def update(self, request, team_pk=None, pk=None, *args, **kwargs):
        """Update a team in LMS tables."""
        team_id = team_pk or pk or kwargs.get('pk')
        if not team_id:
            return Response({'error': 'Team ID required'}, status=400)
 
        try:
            name = request.data.get('name')
            description = request.data.get('description')
            members = request.data.get('members', None)
            manager = request.data.get('manager', None)
            trainer = request.data.get('trainer', None)
 
            if not name:
                return Response({'error': 'name is required'}, status=400)
 
            # Get current team name from LMS
            current_name = None
            with connection.cursor() as cur:
                cur.execute("SELECT team_name FROM teams WHERE team_id = %s LIMIT 1", [team_id])
                row = cur.fetchone()
                if row:
                    current_name = row[0]
 
            if not current_name:
                return Response({'error': 'Team not found'}, status=404)
 
            # Update team in LMS
            manager_email = None
            if manager:
                try:
                    # Try to get UserProfile by ID (handles both int and UUID string)
                    user_profile = UserProfile.objects.get(id=manager)
                    manager_email = user_profile.email
                    # Ensure manager exists in LMS users table
                    try:
                        _insert_lms_user(user_profile)
                    except Exception as e:
                        logging.getLogger(__name__).error('Failed to insert manager into LMS users: %s', e)
                except (ValueError, UserProfile.DoesNotExist) as e:
                    logging.getLogger(__name__).warning('Manager lookup failed for %s: %s', manager, e)
                    # If not a valid ID, treat as email directly
                    manager_email = manager if isinstance(manager, str) and '@' in manager else None
            
            # Handle trainer
            trainer_email = None
            if trainer:
                try:
                    # Try to get UserProfile by ID (handles both int and UUID string)
                    user_profile = UserProfile.objects.get(id=trainer)
                    trainer_email = user_profile.email
                    # Ensure trainer exists in LMS users table
                    try:
                        _insert_lms_user(user_profile)
                    except Exception as e:
                        logging.getLogger(__name__).error('Failed to insert trainer into LMS users: %s', e)
                except (ValueError, UserProfile.DoesNotExist) as e:
                    logging.getLogger(__name__).warning('Trainer lookup failed for %s: %s', trainer, e)
                    # If not a valid ID, treat as email directly
                    trainer_email = trainer if isinstance(trainer, str) and '@' in trainer else None
 
            _upsert_lms_team(
                name,
                description=description or '',
                manager_email=manager_email,
                trainer_email=trainer_email,
                created_by_email=request.user.email if request.user and request.user.is_authenticated else None
            )
 
            # Update team members if provided
            if members is not None:
                # Clear current members
                with connection.cursor() as cur:
                    cur.execute("DELETE FROM team_members WHERE team_id = %s", [team_id])
 
                # Add new members
                for member_id in members:
                    member_email = None
                    try:
                        # Try to get UserProfile by ID (handles both int and UUID string)
                        user_profile = UserProfile.objects.get(id=member_id)
                        member_email = user_profile.email
                        # Ensure user exists in LMS users table before adding to team
                        try:
                            _insert_lms_user(user_profile)
                        except Exception as e:
                            logging.getLogger(__name__).error('Failed to insert member %s: %s', member_email, e)
                    except (ValueError, UserProfile.DoesNotExist):
                        logging.getLogger(__name__).warning('Member lookup failed for %s', member_id)
                        continue
                    
                    if member_email:
                        try:
                            _add_lms_team_member(
                                name,
                                member_email,
                                assigned_by_email=request.user.email if request.user and request.user.is_authenticated else None
                            )
                        except Exception as e:
                            logging.getLogger(__name__).exception('Failed to add member %s to team: %s', member_email, e)
 
            # Audit and notifications
            try:
                _insert_audit_log('update_team', 'team', name, {'description': description}, request=request)
            except Exception:
                pass
            try:
                lms_uid = _ensure_lms_user_id_for_request(request)
                _insert_notification('system', 'Team updated', f'Team {name} updated', link_url=f'/admin/teams', request=request, lms_user_id=lms_uid)
            except Exception:
                pass
 
            # Fetch and return the updated team
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT t.team_id, t.team_name, t.description, t.created_at, COUNT(DISTINCT tm.user_id) as members_count
                    FROM teams t
                    LEFT JOIN team_members tm ON t.team_id = tm.team_id
                    WHERE t.team_id = %s
                    GROUP BY t.team_id, t.team_name, t.description, t.created_at
                    LIMIT 1
                """, [team_id])
                row = cur.fetchone()
                if row:
                    team_data = {
                        'id': str(row[0]),
                        'name': row[1],
                        'description': row[2] or '',
                        'created_at': row[3],
                        'members_count': row[4] or 0,
                        'manager_id': None,
                        'manager_name': None,
                        'trainer_id': None,
                        'trainer_name': None,
                    }
                    return Response(team_data)
            return Response({'error': 'Team updated but could not retrieve'}, status=200)
        except Exception as e:
            logging.getLogger(__name__).exception('Error updating team: %s', e)
            return Response({'error': str(e)}, status=500)

class CourseViewSet(drf_viewsets.ViewSet):
    """ViewSet that exposes read-only access to external LMS `courses` and assignment actions.

    This uses raw SQL to query the existing `courses`, `course_modules`, and `quizzes` tables that exist
    in the shared LMS schema. It also stores local assignments in `CourseAssignment`.
    """

    def list(self, request):
        q = request.query_params.get('search')
        params = []
        sql = "SELECT course_id, title, COALESCE(description, '') as short_description FROM courses"
        if q:
            sql += " WHERE title ILIKE %s OR COALESCE(description, '') ILIKE %s"
            like = f"%{q}%"
            params.extend([like, like])
        sql += " ORDER BY title LIMIT 200"
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        data = [{'id': str(r[0]), 'title': r[1], 'short_description': r[2]} for r in rows]
        return Response(data)

    def retrieve(self, request, pk=None):
        # basic detail plus counts
        with connection.cursor() as cur:
            cur.execute("SELECT course_id, title, COALESCE(description, '') FROM courses WHERE course_id = %s LIMIT 1", [pk])
            row = cur.fetchone()
            if not row:
                return Response({'detail': 'Not found'}, status=404)
            course_id, title, description = row[0], row[1], row[2]

            # modules count
            try:
                cur.execute("SELECT COUNT(*) FROM modules WHERE course_id = %s", [course_id])
                modules_count = cur.fetchone()[0] or 0
            except Exception:
                modules_count = 0

            # quizzes count
            try:
                cur.execute("SELECT COUNT(*) FROM tests WHERE course_id = %s", [course_id])
                quizzes_count = cur.fetchone()[0] or 0
            except Exception:
                quizzes_count = 0

        data = {
            'id': str(course_id),
            'title': title,
            'description': description,
            'modules_count': modules_count,
            'quizzes_count': quizzes_count,
            'metadata': {},
        }
        return Response(data)

    @drf_action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        # payload: { team_ids: [1,2,3] }
        logger = logging.getLogger(__name__)
        try:
            team_ids = request.data.get('team_ids') or []
        except Exception:
            team_ids = []

        if not isinstance(team_ids, (list, tuple)):
            # try to coerce comma-separated string
            if isinstance(team_ids, str):
                team_ids = [s.strip() for s in team_ids.split(',') if s.strip()]
            else:
                return Response({'detail': 'team_ids must be an array of ids'}, status=400)

        created = []
        errors = []
        for tid in team_ids:
            try:
                # allow numeric or string ids
                t = Team.objects.get(id=int(tid)) if str(tid).isdigit() else Team.objects.get(id=tid)
                ca, created_flag = CourseAssignment.objects.get_or_create(course_id=str(pk), team=t)
                created.append({'id': ca.id, 'team': t.id, 'created': created_flag})
            except Team.DoesNotExist:
                errors.append({'team_id': tid, 'error': 'not found'})
            except Exception as exc:
                logger.exception('Error assigning course %s to team %s: %s', pk, tid, exc)
                errors.append({'team_id': tid, 'error': str(exc)})

        # audit: course assignment
        try:
            _insert_audit_log('assign_course', 'course', pk, {'team_ids': team_ids, 'assigned': [c['team'] for c in created]}, request=request)
        except Exception:
            pass

        result = {'assigned': created}
        if errors:
            result['errors'] = errors
        return Response(result)

    @drf_action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """Return list of teams assigned to this course (from local CourseAssignment)."""
        teams = []
        try:
            cas = CourseAssignment.objects.filter(course_id=str(pk)).select_related('team')
            for ca in cas:
                t = ca.team
                # lightweight representation
                teams.append({'id': t.id, 'name': t.name, 'description': t.description, 'members_count': t.members.count()})
        except Exception:
            teams = []
        return Response(teams)


class AuditViewSet(drf_viewsets.ViewSet):
    """Expose recent audit logs from the LMS `audit_logs` table."""

    def list(self, request):
        limit = int(request.query_params.get('limit', 100))
        q = request.query_params.get('search')
        params = [limit]
        base_sql = (
            "SELECT al.log_id, al.user_id, u.first_name, u.last_name, al.action_type, al.entity_type, al.entity_id, "
            "COALESCE(al.details::text, '') as details, al.ip_address, al.user_agent, al.timestamp "
            "FROM audit_logs al LEFT JOIN users u ON u.user_id = al.user_id"
        )
        where_clause = ''
        if q:
            where_clause = " WHERE al.action_type ILIKE %s OR al.details::text ILIKE %s OR al.entity_type ILIKE %s"
            like = f"%{q}%"
            params = [like, like, like, limit]
        sql = base_sql + where_clause + " ORDER BY al.timestamp DESC LIMIT %s"
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        data = []
        for r in rows:
            log_id = str(r[0])
            user_id = r[1]
            first = r[2] or ''
            last = r[3] or ''
            user_name = (first + ' ' + last).strip() if (first or last) else None
            action = r[4]
            entity = r[5]
            entity_id = str(r[6]) if r[6] is not None else None
            details = r[7] or ''
            timestamp = r[10]
            data.append({
                'id': log_id,
                'action': action,
                'resource': entity,
                'resource_id': entity_id,
                'user_id': str(user_id) if user_id is not None else None,
                'user_name': user_name,
                'timestamp': timestamp,
                'details': details,
            })

        serializer = AuditLogSerializer(data, many=True)
        return Response(serializer.data)


@api_view(["GET"])
def notifications(request):
    """Return recent notifications from the `notifications` table, filtered by user role/module.
    Admins see all; manager/trainer/trainee see only notifications relevant to their module.
    """
    if not getattr(settings, 'DEBUG', False):
        if not (request.user and request.user.is_authenticated and (getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False))):
            return Response({'detail': 'Forbidden'}, status=403)

    # Determine the user's role (for filtering notifications by module)
    user_role = 'admin'  # default
    try:
        if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'role'):
            user_role = request.user.profile.role.lower() if request.user.profile.role else 'admin'
    except Exception:
        pass
    
    # Also allow role override via query parameter (for testing or explicit filtering)
    if 'role' in request.query_params:
        user_role = str(request.query_params.get('role')).lower()

    limit = int(request.query_params.get('limit', 50))
    data = []
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT notification_id, user_id, notification_type, title, message, link_url, priority, status, sent_via, read_at, created_at FROM notifications ORDER BY created_at DESC LIMIT %s", [limit])
            rows = cur.fetchall()
            for r in rows:
                notification_type = r[2] or ''
                # Filter notifications by user role:
                # - 'admin' role sees all notifications
                # - 'manager' role sees 'manager', 'admin', 'system', and 'global' notifications
                # - 'trainer' role sees 'trainer', 'admin', 'system', 'course', 'assignment' notifications
                # - 'trainee' role sees 'trainee', 'assignment', 'test', 'course', 'badge', 'system' notifications
                if user_role == 'admin':
                    # admins see all
                    pass
                elif user_role == 'manager':
                    if not any(t in notification_type.lower() for t in ['manager', 'system', 'global', 'admin']):
                        continue  # skip this notification
                elif user_role == 'trainer':
                    if not any(t in notification_type.lower() for t in ['trainer', 'system', 'global', 'course', 'assignment']):
                        continue  # skip this notification
                elif user_role == 'trainee':
                    if not any(t in notification_type.lower() for t in ['trainee', 'assignment', 'test', 'course', 'badge', 'system']):
                        continue  # skip this notification
                else:
                    # unknown role, default to system/global
                    if not any(t in notification_type.lower() for t in ['system', 'global']):
                        continue

                data.append({
                    'id': str(r[0]),
                    'user_id': str(r[1]) if r[1] is not None else None,
                    'type': r[2],
                    'title': r[3],
                    'message': r[4],
                    'link_url': r[5],
                    'priority': r[6],
                    'status': r[7],
                    'sent_via': r[8],
                    'read_at': r[9].isoformat() if r[9] else None,
                    'created_at': r[10].isoformat() if r[10] else None,
                })
    except Exception as e:
        logging.getLogger(__name__).exception('Failed to fetch notifications: %s', e)
        return Response({'detail': 'Failed to fetch notifications', 'error': str(e)}, status=500)

    return Response(data)
