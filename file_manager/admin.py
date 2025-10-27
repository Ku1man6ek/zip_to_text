from django.contrib import admin
from .models import ProjectUpload


@admin.register(ProjectUpload)
class ProjectUploadAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'uploaded_at', 'file_size', 'is_active']
    list_filter = ['uploaded_at', 'is_active', 'user']
    search_fields = ['name', 'user__username']
    readonly_fields = ['uploaded_at']

    def get_queryset(self, request):
        return ProjectUpload.objects.all()