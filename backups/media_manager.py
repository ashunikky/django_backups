import os
import shutil
import zipfile
from django.conf import settings


class MediaBackupManager:
    def __init__(self):
        self.media_root = settings.MEDIA_ROOT

    def backup(self, zip_path):
        try:
            shutil.make_archive(zip_path, 'zip', self.media_root)
            print(f'Media backup created successfully: {zip_path}.zip')
        except Exception as e:
            print(f'Error creating media backup: {e}')

    def restore(self, zip_file):
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(self.media_root)
            print('Media backup restored successfully!')
        except Exception as e:
            print(f'Error restoring media backup: {e}')
