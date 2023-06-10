from django.conf import settings
from django.contrib import admin
from django.http import FileResponse
from django.utils.html import format_html

from backups.db_connectors import SqliteConnector, PostgresConnector
from backups.forms import BackupForm, RestoreForm
from backups.models import Backup, Restore


@admin.register(Backup)
class BackupBackupAdmin(admin.ModelAdmin):
    list_display = ['type', 'file_link', 'created_at', 'created_by']
    list_filter = ['created_at']
    form = BackupForm

    def file_link(self, obj):
        if obj.file:
            return format_html("<a href='%s'>download</a>" % (obj.file.url,))
        else:
            return "No attachment"

    file_link.allow_tags = True
    file_link.short_description = 'File Download'

    def save_model(self, request, obj, form, change):

        # Determine the database type
        database_engine = settings.DATABASES['default']['ENGINE']

        # Create a backup based on the database type
        if 'sqlite3' in database_engine:
            connector = SqliteConnector()
        elif 'postgresql' in database_engine:
            connector = PostgresConnector()
        else:
            print(f"Database type '{database_engine}' is not supported for backup.")
            return

        # Create the backup file
        backup_file_path = connector.create_dump()

        # Associate the backup with the saved model instance
        obj.file = backup_file_path
        obj.created_by = request.user
        obj.save()

        # Provide the backup file as a downloadable response
        backup_file = open(backup_file_path, 'rb')
        response = FileResponse(backup_file)
        response['Content-Disposition'] = f'attachment; filename="{obj.id}.dump"'
        return response

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Restore)
class RestoreBackupAdmin(admin.ModelAdmin):
    list_display = ['type', 'restored_at', 'restored_by']
    list_filter = ['restored_at']
    form = RestoreForm
