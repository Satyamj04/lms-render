from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Create myproject_admin_courseassignment table if missing'

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            try:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS myproject_admin_courseassignment (
                    id bigserial PRIMARY KEY,
                    course_id varchar(128) NOT NULL,
                    team_id bigint NOT NULL REFERENCES myproject_admin_team(id) ON DELETE CASCADE,
                    assigned_at timestamp with time zone DEFAULT now()
                );
                CREATE UNIQUE INDEX IF NOT EXISTS myproject_admin_courseassignment_course_team_uniq ON myproject_admin_courseassignment(course_id, team_id);
                """)
                self.stdout.write('table ensured')
            except Exception as e:
                self.stderr.write('failed: ' + str(e))
