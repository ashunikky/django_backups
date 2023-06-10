from django.contrib.auth.models import User
from django.db import models


class Backup(models.Model):
    BACKUP_TYPE_CHOICES = [
        ('database', 'Database Backup'),
        ('media', 'Media Backup'),
    ]

    type = models.CharField(max_length=10, choices=BACKUP_TYPE_CHOICES)
    file = models.FileField(upload_to='backups/')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.get_type_display()} Backup - {self.created_at}"


class Restore(models.Model):
    RESTORE_TYPE_CHOICES = [
        ('database', 'Database Restore'),
        ('media', 'Media Restore'),
    ]

    type = models.CharField(max_length=10, choices=RESTORE_TYPE_CHOICES)
    restored_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='backups/')
    restored_by = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.get_type_display()} Restore - {self.restored_at}"
