from django.core.management.base import BaseCommand
from django.db import connection
import json

class Command(BaseCommand):
    help = 'Print CourseAssignment rows from local DB'

    def add_arguments(self, parser):
        parser.add_argument('limit', nargs='?', type=int, default=100)

    def handle(self, *args, **options):
        limit = options.get('limit', 100)
        with connection.cursor() as cur:
            try:
                # app label for this app is 'myproject_admin' so table is myproject_admin_courseassignment
                cur.execute(
                    """
                    SELECT id, course_id, team_id, assigned_at FROM myproject_admin_courseassignment ORDER BY assigned_at DESC LIMIT %s
                    """,
                    [limit]
                )
                rows = cur.fetchall()
            except Exception as e:
                self.stderr.write(f"Failed to query myproject_admin_courseassignment: {e}")
                return

        for r in rows:
            out = {'id': r[0], 'course_id': r[1], 'team_id': r[2], 'assigned_at': r[3].isoformat() if hasattr(r[3], 'isoformat') else str(r[3])}
            self.stdout.write(json.dumps(out, ensure_ascii=False))
