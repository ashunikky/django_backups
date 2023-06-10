import os
import subprocess
from datetime import datetime

import psycopg2
import shutil
import sqlite3
from django.conf import settings


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


# # Usage example
# connector = PostgresConnector()
#
# # Create a backup
# connector.create_dump('/path/to/backup.dump')
#
# # Restore the backup
# connector.restore_dump('/path/to/backup.dump')
#

class SqliteConnector:
    def __init__(self):
        self.db_path = settings.DATABASES['default']['NAME']
        self.media_root = settings.MEDIA_ROOT

    def create_dump(self):
        try:
            timestamp = datetime.now().strftime('%d-%m-%Y')
            # backup_folder = os.path.join(self.media_root, 'backups')
            # os.makedirs(backup_folder, exist_ok=True)
            backup_file_path = f'backups/{timestamp}-dbbackup.sqlite3'

            shutil.copy2(self.db_path, backup_file_path)

            print('Backup created successfully!')
            return backup_file_path
        except Exception as e:
            raise Exception(f'Error creating backup: {e}')

    def restore_dump(self, dump_path):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Retrieve all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            # Drop existing tables
            for table in tables:
                cursor.execute(f"DROP TABLE {table[0]}")

            # Restore the dump
            with open(dump_path, 'r') as f:
                sql_script = f.read()
                cursor.executescript(sql_script)

            conn.commit()
            print('Backup restored successfully!')
        except sqlite3.Error as e:
            print(f'Error restoring backup: {e}')
        finally:
            if conn is not None:
                conn.close()

# # Usage example
# connector = SqliteConnector()
#
# # Create a backup
# connector.create_dump('/path/to/backup.db')
#
# # Restore the backup
# connector.restore_dump('/path/to/backup.db')
