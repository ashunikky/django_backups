from django import forms

from django.db import connection

from backups.models import Backup, Restore


def get_db_name_tuple():
    db_name = connection.settings_dict['NAME']


class BackupForm(forms.ModelForm):
    class Meta:
        model = Backup
        fields = ('type',)


class RestoreForm(forms.ModelForm):
    class Meta:
        model = Restore
        fields = ('type',)

