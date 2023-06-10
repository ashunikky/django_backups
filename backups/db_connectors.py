import subprocess
import warnings

import psycopg2
from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS, OperationalError, IntegrityError
from django.utils.timezone import now

DUMP_TABLES = """
SELECT "name", "type", "sql"
FROM "sqlite_master"
WHERE "sql" NOT NULL AND "type" == 'table'
ORDER BY "name"
"""


def get_db_connector():
    # Determine the database type
    database_engine = settings.DATABASES['default']['ENGINE']

    # Create a backup based on the database type
    if 'sqlite3' in database_engine:
        return SqliteConnector()
    elif 'postgresql' in database_engine:
        return PostgresConnector()
    else:
        raise Exception(f"Database type '{database_engine}' is not supported for backup.")


class BaseDBConnector:
    def __init__(self):
        self.backup_root = settings.BACKUP_ROOT
        self.media_root = settings.MEDIA_ROOT
        self.connection = connections[DEFAULT_DB_ALIAS]
        self.exclude_tables = ['django_migrations', 'django_session']

    @staticmethod
    def get_relative_media_file_path(absolute_file_path):
        # Get the relative file path by removing the MEDIA_ROOT prefix
        relative_file_path = str(absolute_file_path.relative_to(settings.MEDIA_ROOT))
        # Normalize the path separators
        relative_file_path = relative_file_path.replace('\\', '/')
        return relative_file_path

    def create_backup(self):
        raise NotImplementedError

    def restore_backup(self, backup_file):
        raise NotImplementedError


class PostgresConnector:
    def __init__(self):
        self.host = settings.DATABASES['default']['HOST']
        self.port = settings.DATABASES['default']['PORT']
        self.database = settings.DATABASES['default']['NAME']
        self.user = settings.DATABASES['default']['USER']
        self.password = settings.DATABASES['default']['PASSWORD']

    def create_dump(self, dump_path):
        try:
            subprocess.check_output([
                'pg_dump',
                '-Fc',
                f'-h{self.host}',
                f'-p{self.port}',
                f'-U{self.user}',
                f'-f{dump_path}',
                self.database
            ])
            print('Backup created successfully!')
        except subprocess.CalledProcessError as e:
            print(f'Error creating backup: {e}')

    def restore_dump(self, dump_path):
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            cur = conn.cursor()
            cur.execute(f"DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            cur.close()
            conn.commit()
            subprocess.check_output([
                'pg_restore',
                '-Fc',
                f'-h{self.host}',
                f'-p{self.port}',
                f'-U{self.user}',
                '-d',
                self.database,
                dump_path
            ])
            print('Backup restored successfully!')
        except (subprocess.CalledProcessError, psycopg2.Error) as e:
            print(f'Error restoring backup: {e}')
        finally:
            if conn is not None:
                conn.close()


class SqliteConnector(BaseDBConnector):
    def _write_dump(self, file_obj):
        cursor = self.connection.connection.cursor()
        cursor.execute(DUMP_TABLES)
        for table_name, _, sql in cursor.fetchall():
            if table_name.startswith("sqlite_") or table_name in self.exclude_tables:
                continue
            if sql.startswith("CREATE TABLE"):
                sql = sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
                # Make SQL commands in 1 line
                sql = sql.replace("\n    ", "")
                sql = sql.replace("\n)", ")")
            file_obj.write(f"{sql};\n".encode())

            table_name_ident = table_name.replace('"', '""')
            res = cursor.execute(f'PRAGMA table_info("{table_name_ident}")')
            column_names = [str(table_info[1]) for table_info in res.fetchall()]
            q = """SELECT 'INSERT INTO "{0}" VALUES({1})' FROM "{0}";\n""".format(
                table_name_ident,
                ",".join(
                    """'||quote("{}")||'""".format(col.replace('"', '""'))
                    for col in column_names
                ),
            )
            query_res = cursor.execute(q)
            for row in query_res:
                file_obj.write(f"{row[0]};\n".encode())
        cursor.close()

    def create_backup(self):
        timestamp = now().strftime('%d-%m-%Y %H:%M')
        backup_filename = f'backup_{timestamp}.sql'
        backup_path = self.backup_root / backup_filename

        if not self.connection.is_usable():
            self.connection.connect()
        with open(backup_path, "wb") as f:
            self._write_dump(f)
        return self.get_relative_media_file_path(backup_path)

    def restore_backup(self, backup_file):
        if not self.connection.is_usable():
            self.connection.connect()
        cursor = self.connection.cursor()
        for line in backup_file.readlines():
            try:
                cursor.execute(line.decode("UTF-8"))
            except (OperationalError, IntegrityError) as err:
                warnings.warn(f"Error in db restore: {err}")
