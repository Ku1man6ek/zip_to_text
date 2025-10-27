import os
import zipfile
import tempfile
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse
from django.core.files import File
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from .models import ProjectUpload


def get_file_icon(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.py', '.js', '.html', '.css', '.txt', '.md', '.json', '.xml']:
        return '📄'
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.bmp']:
        return '🖼️'
    elif ext in ['.zip', '.rar', '.tar', '.gz', '.7z']:
        return '📦'
    elif ext in ['.pdf', '.doc', '.docx']:
        return '📎'
    else:
        return '📄'


def should_ignore_folder(folder_name):
    """Проверяет, нужно ли игнорировать папку"""
    ignore_folders = {
        '__pycache__', '.git', 'node_modules', '.idea', '.vscode',
        'venv', 'env', '.env', 'dist', 'build', 'target', 'out',
        'tmp', 'temp', 'cache', 'logs', '__MACOSX', '.pytest_cache',
        '.coverage', 'htmlcov', '.tox', '.mypy_cache', '.DS_Store',
        'thumbs.db', '.Spotlight-V100', '.Trashes'
    }
    return folder_name in ignore_folders


def is_important_file(filename):
    """Проверяет, является ли файл важным для отображения в структуре"""
    important_extensions = {
        '.py', '.js', '.html', '.css', '.php', '.java', '.cpp', '.c', '.h',
        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.clj', '.hs',
        '.json', '.xml', '.yml', '.yaml', '.ini', '.cfg', '.conf', '.toml',
        '.txt', '.md', '.rst', '.tex', '.jsx', '.tsx', '.vue', '.svelte', '.ts',
        '.sh', '.bat', '.ps1', '.cmd'
    }
    ext = os.path.splitext(filename)[1].lower()
    return ext in important_extensions


def is_text_file_for_content(filename):
    """Проверяет, является ли файл текстовым для отображения содержимого"""
    text_extensions = {
        '.py', '.js', '.html', '.css', '.txt', '.md', '.json', '.xml',
        '.php', '.rb', '.java', '.c', '.cpp', '.h', '.cs', '.sql',
        '.yml', '.yaml', '.ini', '.cfg', '.conf', '.bat', '.sh',
        '.ts', '.jsx', '.tsx', '.vue', '.svelte'
    }
    ext = os.path.splitext(filename)[1].lower()
    return ext in text_extensions


def process_directory(directory_path, output_path):
    """Обрабатывает директорию и создает текстовую структуру только с важными файлов"""
    with open(output_path, 'w', encoding='utf-8') as output:
        output.write("📁 СТРУКТУРА ПРОЕКТА (ТОЛЬКО ВАЖНЫЕ ФАЙЛЫ):\n\n")

        tree = {}
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if not should_ignore_folder(d)]
            rel_path = os.path.relpath(root, directory_path)
            if rel_path == '.':
                rel_path = ''

            current = tree
            if rel_path:
                parts = rel_path.split(os.sep)
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            important_files = [f for f in files if is_important_file(f)]
            for file in important_files:
                current[file] = {}

        def print_tree(tree, level=0, prefix='', is_last=True):
            keys = list(tree.keys())
            keys.sort()
            for i, key in enumerate(keys):
                is_last_item = i == len(keys) - 1
                connector = '└── ' if is_last_item else '├── '
                if tree[key]:
                    output.write(f"{prefix}{connector}📁 {key}/\n")
                    new_prefix = prefix + ('    ' if is_last_item else '│   ')
                    print_tree(tree[key], level + 1, new_prefix, is_last_item)
                else:
                    icon = get_file_icon(key)
                    output.write(f"{prefix}{connector}{icon} {key}\n")

        print_tree(tree)

        output.write("\n\n" + "=" * 80 + "\n")
        output.write("СОДЕРЖИМОЕ ФАЙЛОВ:\n")
        output.write("=" * 80 + "\n\n")

        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if not should_ignore_folder(d)]
            for file in files:
                if not is_text_file_for_content(file):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, directory_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    output.write(f"--- {rel_path} ---\n")
                    output.write(content)
                    output.write("\n" + "-" * 40 + "\n\n")
                except (UnicodeDecodeError, UnicodeError):
                    continue
                except Exception as e:
                    output.write(f"--- {rel_path} ---\n")
                    output.write(f"[ОШИБКА ЧТЕНИЯ: {str(e)}]\n\n")


def process_zip_file(zip_path, output_path):
    """Обрабатывает ZIP файл и создает текстовую структуру"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        process_directory(temp_dir, output_path)


def login_view(request):
    """Страница входа"""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'login.html')


def custom_logout(request):
    """Кастомный выход"""
    auth_logout(request)
    return redirect('login_view')


@login_required
def home(request):
    """Главная страница"""
    return render(request, 'home.html')


@login_required
def upload_zip(request):
    """Обработка загрузки ZIP файла"""
    if request.method == 'POST':
        zip_file = request.FILES.get('zip_file')
        if not zip_file:
            return render(request, 'upload.html', {'error': 'Пожалуйста, выберите ZIP файл'})

        project = ProjectUpload()
        original_filename = zip_file.name
        project_name = os.path.splitext(original_filename)[0]
        project.name = project_name
        project.file_size = f"{(zip_file.size / (1024 * 1024)):.2f} MB"
        project.user = request.user
        project.save()

        temp_zip_path = None
        temp_txt_path = None

        try:
            project.original_zip.save(original_filename, zip_file)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                for chunk in zip_file.chunks():
                    temp_zip.write(chunk)
                temp_zip_path = temp_zip.name

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_txt:
                temp_txt_path = temp_txt.name

            process_zip_file(temp_zip_path, temp_txt_path)
            txt_filename = f"{project_name}.txt"
            with open(temp_txt_path, 'rb') as f:
                project.text_file.save(txt_filename, File(f))

            project.save()
            return redirect('history')

        except Exception as e:
            if project.id:
                project.delete()
            return render(request, 'upload.html', {'error': f'Ошибка обработки ZIP: {str(e)}'})

        finally:
            if temp_zip_path and os.path.exists(temp_zip_path):
                try: os.unlink(temp_zip_path)
                except: pass
            if temp_txt_path and os.path.exists(temp_txt_path):
                try: os.unlink(temp_txt_path)
                except: pass

    return render(request, 'upload.html')


@login_required
def history(request):
    """Страница истории загрузок"""
    projects = ProjectUpload.objects.filter(user=request.user, is_active=True).order_by('-uploaded_at')
    return render(request, 'history.html', {'projects': projects})


@login_required
def delete_project(request, project_id):
    """Мягкое удаление проекта"""
    project = get_object_or_404(ProjectUpload, id=project_id, user=request.user)
    if request.method == 'POST':
        project.soft_delete()
        return redirect('history')
    return redirect('history')


@login_required
def download_zip(request, project_id):
    """Скачивание оригинального ZIP файла"""
    project = get_object_or_404(ProjectUpload, id=project_id, user=request.user)
    if project.original_zip:
        try:
            response = FileResponse(project.original_zip.open('rb'),
                                    content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{project.original_zip.name}"'
            return response
        except Exception as e:
            return HttpResponse(f"Ошибка скачивания ZIP: {str(e)}")
    return HttpResponse("ZIP файл не найден")


@login_required
def view_text_file(request, project_id):
    """Просмотр текстового файла"""
    project = get_object_or_404(ProjectUpload, id=project_id, user=request.user)
    if project.text_file:
        try:
            with open(project.text_file.path, 'r', encoding='utf-8') as f:
                content = f.read()
            return render(request, 'view_file.html', {
                'content': content,
                'project': project
            })
        except Exception as e:
            return HttpResponse(f"Ошибка чтения файла: {str(e)}")
    return HttpResponse("Файл не найден")


@login_required
def download_text_file(request, project_id):
    """Скачивание текстового файла"""
    project = get_object_or_404(ProjectUpload, id=project_id, user=request.user)
    if project.text_file:
        try:
            response = FileResponse(project.text_file.open('rb'),
                                    content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{project.text_file.name}"'
            return response
        except Exception as e:
            return HttpResponse(f"Ошибка скачивания файла: {str(e)}")
    return HttpResponse("Файл не найден")


# file_manager/views.py - добавьте эту функцию
from django.contrib import messages


def login_view(request):
    """Страница входа"""
    if request.user.is_authenticated:
        return redirect('home')

    # Очистка сообщений об ошибках
    storage = messages.get_messages(request)
    for message in storage:
        pass

    return render(request, 'login.html')