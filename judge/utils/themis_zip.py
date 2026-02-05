import os
import shutil
import zipfile
from django.conf import settings
from judge.models import Language, ThemisExtensionMapping

def get_temp_dir(name):
    base_tmp = getattr(settings, 'DMOJ_TMP_DIR', None)
    if not base_tmp or not os.access(base_tmp, os.W_OK):
        base_tmp = os.path.join(settings.BASE_DIR, 'tmp')
    
    path = os.path.join(base_tmp, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    return path

def process_themis_zip(zip_file, contest, problems_map, admin_profile):
    """
    EXTRACT ONLY. 
    Returns metadata for the frontend to perform sequential submissions.
    """
    temp_dir = get_temp_dir('themis_bulk_prepare_' + contest.key)
    
    results = {} # {display_username: {problem_code: {source: "...", lang: "..."}}}
    errors = []

    valid_extensions = {m.extension.lower(): m.language.key for m in ThemisExtensionMapping.objects.all().select_related('language')}
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            z.extractall(temp_dir)

        all_solution_files = []
        for root, _, files in os.walk(temp_dir):
            for f in files:
                if f.startswith('.'): continue
                file_base, file_ext = os.path.splitext(f)
                if file_base.upper() in problems_map and file_ext.lower() in valid_extensions:
                    all_solution_files.append(os.path.join(root, f))
        
        student_files = {} 
        generic_folders = {'thisinh', 'solutions', 'submissions', 'test', 'tests', 'data', 'tmp', '__macosx'}
        
        for fpath in all_solution_files:
            rel_path = os.path.relpath(fpath, temp_dir)
            parts = rel_path.split(os.sep)
            
            username = None
            for i in range(len(parts)-2, -1, -1):
                name = parts[i]
                if name.upper() not in problems_map and name.lower() not in generic_folders:
                    username = name
                    break
            if not username: username = parts[0]
            
            username = username.strip()
            if username not in student_files: student_files[username] = []
            student_files[username].append(fpath)

        for display_name, fpaths in student_files.items():
            results[display_name] = {}
            for fpath in fpaths:
                filename = os.path.basename(fpath)
                file_base = os.path.splitext(filename)[0].upper()
                file_ext = os.path.splitext(filename)[1].lower()
                
                problem_code = problems_map.get(file_base)
                lang_key = valid_extensions.get(file_ext)

                with open(fpath, 'rb') as f:
                    try:
                        content = f.read().decode('utf-8')
                    except UnicodeDecodeError:
                        content = f.read().decode('latin-1')

                results[display_name][problem_code] = {
                    'source': content,
                    'lang': lang_key
                }

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
    return {'results': results, 'errors': errors}