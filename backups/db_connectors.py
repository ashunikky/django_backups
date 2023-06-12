import subprocess
import warnings

from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS, OperationalError, IntegrityError, transaction
from django.utils.timezone import now
import re

DUMP_TABLES = """
SELECT "name", "type", "sql"
FROM "sqlite_master"
WHERE "sql" NOT NULL AND "type" == 'table'
ORDER BY "name"
"""


def get_db_connector():
    # Determine the database type
    database_engine = settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']

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
        self.backup_path = self.get_backup_path()

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

    def get_backup_path(self):
        timestamp = now().strftime('%d-%m-%Y-%H::%M')
        backup_filename = f'backup_{timestamp}.sql'
        return self.backup_root / backup_filename


class PostgresConnector(BaseDBConnector):
    def __init__(self):
        db = settings.DATABASES[DEFAULT_DB_ALIAS]
        self.db_host = db['HOST']
        self.db_port = db['PORT'] or '5432'
        self.db_name = db['NAME']
        self.db_user = db['USER']
        self.db_password = db['PASSWORD']
        super().__init__()

    def create_backup(self):
        extra_args = '--no-comments --data-only --inserts --no-owner'
        exclude_table_string = ' '.join([f'--exclude-table={table}' for table in self.exclude_tables])

        command = f'PGPASSWORD={self.db_password} pg_dump {extra_args} {exclude_table_string} -U {self.db_user} -h' \
                  f' {self.db_host} -p {self.db_port} -F p {self.db_name} > {self.backup_path}'

        # Execute the pg_dump command using subprocess
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            # Handle any errors that occurred during the restore process
            raise Exception(f'Error occurred during database restore:\n{stderr.decode()}')
        return self.get_relative_media_file_path(self.backup_path)

    def restore_backup(self, backup_file):
        if not self.connection.is_usable():
            self.connection.connect()
        cursor = self.connection.cursor()

        self.clean_sql(backup_file.path)

        for line in backup_file.readlines():
            try:
                with transaction.atomic():
                    cursor.execute(line.strip().decode("UTF-8"))
            except (OperationalError, IntegrityError) as err:
                warnings.warn(f"Error in db restore: {err}")

    @staticmethod
    def clean_sql(file_path):
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()

        # Remove SQL comments starting with "--"
        pattern = r'^\s*--.*?$'
        modified_content = re.sub(pattern, '', file_content, flags=re.MULTILINE)

        # Remove lines containing SET statements
        pattern_set = r'^\s*SET\b.*?$'
        modified_content = re.sub(pattern_set, '', modified_content, flags=re.MULTILINE)

        # Remove empty lines
        pattern_empty_lines = r'^\s*\n'
        modified_content = re.sub(pattern_empty_lines, '', modified_content, flags=re.MULTILINE)

        # Write the modified content back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(modified_content)


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
        if not self.connection.is_usable():
            self.connection.connect()
        with open(self.backup_path, "wb") as f:
            self._write_dump(f)
        return self.get_relative_media_file_path(self.backup_path)

    def restore_backup(self, backup_file):
        if not self.connection.is_usable():
            self.connection.connect()
        cursor = self.connection.cursor()
        for line in backup_file.readlines():
            try:
                with transaction.atomic():
                    cursor.execute(line.strip().decode("UTF-8"))
            except (OperationalError, IntegrityError) as err:
                warnings.warn(f"Error in db restore: {err}")
