from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.custom_logout, name='logout'),
    path('upload/', views.upload_zip, name='upload'),
    path('history/', views.history, name='history'),
    path('project/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('project/<int:project_id>/download-zip/', views.download_zip, name='download_zip'),
    path('view/<int:project_id>/', views.view_text_file, name='view_file'),
    path('download/<int:project_id>/', views.download_text_file, name='download_file'),
]