from django.core.management.base import BaseCommand
from django.db import connection
import json

class Command(BaseCommand):
    help = 'Print recent rows from audit_logs table'

    def add_arguments(self, parser):
        parser.add_argument('limit', nargs='?', type=int, default=50)

    def handle(self, *args, **options):
        limit = options.get('limit', 50)
        with connection.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT log_id, user_id, action_type, entity_type, entity_id, details, ip_address, user_agent, timestamp
                    FROM audit_logs
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    [limit]
                )
                rows = cur.fetchall()
            except Exception as e:
                self.stderr.write(f"Failed to query audit_logs: {e}")
                return

        for r in rows:
            log = {
                'log_id': str(r[0]),
                'user_id': str(r[1]) if r[1] is not None else None,
                'action_type': r[2],
                'entity_type': r[3],
                'entity_id': str(r[4]) if r[4] is not None else None,
                'details': r[5],
                'ip_address': r[6],
                'user_agent': r[7],
                'timestamp': r[8].isoformat() if hasattr(r[8], 'isoformat') else str(r[8]),
            }
            self.stdout.write(json.dumps(log, ensure_ascii=False))
