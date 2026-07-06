import os
import math
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.conf import settings

# Path to the userdata folder
USERDATA_DIR = os.path.join(settings.BASE_DIR, 'userdata')

@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_manage_images(request):
    if request.method == "POST":
        # Handle file deletion
        filename = request.POST.get("filename")
        if not filename:
            return JsonResponse({"status": "error", "message": "Missing filename"}, status=400)
        
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        file_path = os.path.join(USERDATA_DIR, filename)
        
        if not os.path.exists(file_path):
            return JsonResponse({"status": "error", "message": "File not found"}, status=404)
        
        try:
            os.remove(file_path)
            # Double check the file is deleted
            if os.path.exists(file_path):
                return JsonResponse({"status": "error", "message": "File deletion verification failed. File still exists."}, status=500)
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    # GET request - List files
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')
    pdf_extensions = ('.pdf',)
    
    files_list = []
    unique_extensions = set()
    
    if os.path.exists(USERDATA_DIR):
        for name in os.listdir(USERDATA_DIR):
            if name.startswith('.'):
                continue
            
            file_path = os.path.join(USERDATA_DIR, name)
            if not os.path.isfile(file_path):
                continue
                
            ext = os.path.splitext(name)[1].lower()
            if ext:
                unique_extensions.add(ext)
                
            if ext in image_extensions:
                file_type = 'image'
            elif ext in pdf_extensions:
                file_type = 'pdf'
            else:
                file_type = 'other'
                
            stat = os.stat(file_path)
            files_list.append({
                'name': name,
                'size_bytes': stat.st_size,
                'size': f"{stat.st_size / 1024:.1f} KB",
                'url': f"/userdata/{name}",
                'mtime': stat.st_mtime,
                'type': file_type,
                'ext': ext[1:].upper() if ext else 'FILE'
            })
            
    # Sorted unique extensions list
    extensions_list = sorted(list(unique_extensions))
    
    # Get parameters
    search_query = request.GET.get("search", "").strip().lower()
    filter_ext = request.GET.get("ext", "").strip().lower()
    sort_by = request.GET.get("sort", "mtime_desc")
    
    # Apply filtering
    if search_query:
        files_list = [f for f in files_list if search_query in f['name'].lower()]
        
    if filter_ext:
        files_list = [f for f in files_list if os.path.splitext(f['name'])[1].lower() == filter_ext]
        
    # Apply sorting
    if sort_by == "mtime_desc":
        files_list.sort(key=lambda x: x['mtime'], reverse=True)
    elif sort_by == "mtime_asc":
        files_list.sort(key=lambda x: x['mtime'])
    elif sort_by == "size_desc":
        files_list.sort(key=lambda x: x['size_bytes'], reverse=True)
    elif sort_by == "size_asc":
        files_list.sort(key=lambda x: x['size_bytes'])
    elif sort_by == "name_asc":
        files_list.sort(key=lambda x: x['name'].lower())
        
    # Simple pagination
    page = int(request.GET.get("page", 1))
    per_page = 40
    total_files = len(files_list)
    total_pages = math.ceil(total_files / per_page)
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_files = files_list[start_idx:end_idx]
    
    context = {
        'files': paginated_files,
        'page': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1,
        'total_files': total_files,
        'title': 'Manage Uploaded Images',
        'extensions': extensions_list,
        'selected_ext': filter_ext,
        'selected_sort': sort_by,
        'search_query': request.GET.get("search", "")
    }
    
    return render(request, 'admin/manage_images.html', context)
