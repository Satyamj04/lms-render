from django.core.management.base import BaseCommand
from django.db import connection
import uuid, json
from django.utils import timezone

class Command(BaseCommand):
    help = 'Insert a test row into audit_logs'

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            try:
                # entity_id is UUID in the LMS schema; avoid inserting non-UUID into that column
                cur.execute(
                    """
                    INSERT INTO audit_logs (log_id, user_id, action_type, entity_type, entity_id, details, ip_address, user_agent, timestamp)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [str(uuid.uuid4()), None, 'test_insert', 'test_entity', None, json.dumps({'test': True, 'entity_id': 'test-123'}), '127.0.0.1', 'cli', timezone.now()]
                )
                self.stdout.write('inserted')
            except Exception as e:
                self.stderr.write('insert failed: ' + str(e))
