#!/usr/bin/env python3
"""
FPTOJ Problem Creator & Testcase Generator Helper Tool.
Tự động hóa 100% việc tạo bài, sinh testcases, nén zip, upload và cập nhật lời giải trên hệ thống.
"""

import os
import subprocess
import tempfile
import zipfile
import shutil

SITE = "/home/kien/site"
VENV_PY = os.path.join(SITE, "dmojsite/bin/python3")
MANAGE = os.path.join(SITE, "manage.py")

def manage(*args, timeout=90):
    """Gọi lệnh manage.py của Django DMOJ"""
    cmd = [VENV_PY, MANAGE] + list(args)
    r = subprocess.run(cmd, cwd=SITE, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(f"    [DMOJ CLI ERROR] Command failed: {' '.join(cmd)}")
        print(f"    Stdout: {r.stdout[-300:]}")
        print(f"    Stderr: {r.stderr[-300:]}")
        return False
    return True

def compile_cpp(code_str, work_dir):
    """Biên dịch mã nguồn C++ thành file thực thi trong thư mục làm việc tạm thời"""
    src_path = os.path.join(work_dir, "solution.cpp")
    exe_path = os.path.join(work_dir, "solution")
    
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(code_str)
        
    print(f"  [Compiler] Biên dịch mã nguồn C++ mẫu...")
    r = subprocess.run(["g++", "-O3", "-std=c++17", "-o", exe_path, src_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Biên dịch C++ thất bại:\n{r.stderr}")
    return exe_path

def run_exe(exe_path, inp_str, timeout=15):
    """Chạy file thực thi C++ với đầu vào và thu về đầu ra chuẩn stdout"""
    r = subprocess.run([exe_path], input=inp_str, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"Lỗi runtime khi chạy code mẫu:\n{r.stderr}")
    return r.stdout

def create_problem_on_system(spec, work_dir):
    """Tạo bài tập và cấu hình mô tả, lời giải trên DMOJ"""
    code = spec["code"]
    name = spec["name"]
    time_limit = str(spec.get("time_limit", 1.0))
    memory_limit = str(spec.get("memory_limit", 262144))
    points = str(spec.get("points", 100))
    
    # Lưu đề bài và lời giải ra file tạm để tránh lỗi bash escape
    desc_path = os.path.join(work_dir, f"{code}_desc.md")
    edit_path = os.path.join(work_dir, f"{code}_edit.md")
    
    with open(desc_path, "w", encoding="utf-8") as f:
        f.write(spec["description"])
    with open(edit_path, "w", encoding="utf-8") as f:
        f.write(spec["editorial"])
        
    print(f"  [DMOJ CLI] Đang xóa bài cũ nếu tồn tại...")
    manage("problem_cli", "delete", code, "--force")
    
    print(f"  [DMOJ CLI] Khởi tạo bài tập mới: {code} - {name}...")
    ok = manage("problem_cli", "create", code, name,
                "--type", "custom", "--group", "fptoj",
                "--description-file", desc_path,
                "--editorial-file", edit_path,
                "--points", points,
                "--time-limit", time_limit,
                "--memory-limit", memory_limit,
                "--public", "--author", "kienadmin")
    return ok

def upload_testcases_to_system(code, tests_list, work_dir):
    """Đóng gói zip testcase, upload và cấu hình testcase database"""
    zip_path = os.path.join(work_dir, f"{code}.zip")
    
    # Nén các file in/out
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, (inp, out, _) in enumerate(tests_list, 1):
            in_name = f"{idx}.in"
            out_name = f"{idx}.out"
            zf.writestr(in_name, inp)
            zf.writestr(out_name, out)
            
    print(f"  [DMOJ CLI] Đang tải zip dữ liệu testcase lên server...")
    if not manage("problem_cli", "data", "upload-zip", code, zip_path):
        return False
        
    print(f"  [DMOJ CLI] Cấu hình điểm số cho từng testcase...")
    for idx, (_, _, pts) in enumerate(tests_list, 1):
        in_name = f"{idx}.in"
        out_name = f"{idx}.out"
        manage("problem_cli", "testcase", "add", code,
               "--input", in_name, "--output", out_name,
               "--points", str(pts))
               
    print(f"  [DMOJ CLI] Biên dịch cấu hình init.yml...")
    manage("problem_cli", "data", "compile", code)
    return True

def build_single_problem(spec):
    """Hàm chính xử lý tự động cho một bài tập đơn lẻ"""
    code = spec["code"]
    name = spec["name"]
    print(f"\n==================================================")
    print(f"BẮT ĐẦU XỬ LÝ BÀI TẬP: {code} - {name}")
    print(f"==================================================")
    
    # Tạo thư mục làm việc tạm thời
    tmp_dir = tempfile.mkdtemp()
    try:
        # 1. Biên dịch code lời giải C++
        exe_path = compile_cpp(spec["solution_code"], tmp_dir)
        
        # 2. Sinh dữ liệu testcase
        tests_list = []
        gen_func = spec["gen_testcase_func"]
        testcases_config = spec.get("testcases", [])
        
        print(f"  [Generator] Bắt đầu sinh {len(testcases_config)} bộ testcases...")
        for idx, tc in enumerate(testcases_config, 1):
            seed = tc.get("seed", random_seed())
            pts = tc.get("points", 10)
            
            # Sinh input bằng hàm Python
            inp_str = gen_func(idx, seed)
            # Sinh expected output từ chương trình C++ mẫu
            out_str = run_exe(exe_path, inp_str)
            
            tests_list.append((inp_str, out_str, pts))
            print(f"    -> Đã sinh xong testcase {idx} (seed: {seed}, points: {pts})")
            
        # 3. Tạo bài trên hệ thống
        if not create_problem_on_system(spec, tmp_dir):
            print("  ❌ Thất bại khi khởi tạo bài tập!")
            return False
            
        # 4. Upload zip và cấu hình testcase
        if not upload_testcases_to_system(code, tests_list, tmp_dir):
            print("  ❌ Thất bại khi upload testcase!")
            return False
            
        print(f"  ✅ Thành công rực rỡ bài tập: {code}")
        return True
        
    finally:
        # Dọn dẹp thư mục tạm
        shutil.rmtree(tmp_dir)

def random_seed():
    """Hàm sinh seed ngẫu nhiên nếu không định nghĩa"""
    import random
    return random.randint(1, 1000000)

def create_problems(specs):
    """Xử lý danh sách nhiều bài tập"""
    success_cnt = 0
    for spec in specs:
        if build_single_problem(spec):
            success_cnt += 1
    print(f"\n==================================================")
    print(f"HOÀN THÀNH: Đã tạo thành công {success_cnt}/{len(specs)} bài tập.")
    print(f"==================================================")
