from django.db import models
import os

class ProjectUpload(models.Model):
    name = models.CharField(max_length=255, blank=True)
    original_zip = models.FileField(upload_to='zips/', blank=True, null=True)
    text_file = models.FileField(upload_to='text_files/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name or f"Project {self.id}"

    def soft_delete(self):
        """Мягкое удаление - скрывает из истории пользователя, но сохраняет файлы"""
        self.is_active = False
        self.save()

    def hard_delete(self):
        """Полное удаление с удалением файлов"""
        if self.original_zip and os.path.isfile(self.original_zip.path):
            try:
                os.remove(self.original_zip.path)
            except:
                pass
        if self.text_file and os.path.isfile(self.text_file.path):
            try:
                os.remove(self.text_file.path)
            except:
                pass
        self.delete()