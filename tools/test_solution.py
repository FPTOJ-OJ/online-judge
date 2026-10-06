#!/usr/bin/env python3
import os
import sys
import re
import zipfile
import tempfile
import subprocess
import shutil
import yaml

# Add site directory to python path for django imports
SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SITE not in sys.path:
    sys.path.insert(0, SITE)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dmoj.settings")
import django
django.setup()

from django.conf import settings
from judge.models import Problem, Solution

def find_zip_file(problem_code):
    """Tìm tệp zip testcase của bài tập trên hệ thống"""
    search_dirs = [
        os.path.join(SITE, "uploads"),
        getattr(settings, "DMOJ_PROBLEM_DATA_ROOT", "/data/problems"),
        "/data/problems",
    ]
    for directory in search_dirs:
        for root, dirs, files in os.walk(directory):
            if f"{problem_code}.zip" in files:
                return os.path.join(root, f"{problem_code}.zip")
    return None

def extract_cpp_code(markdown_content):
    """Trích xuất khối mã nguồn C++ hoàn chỉnh đầu tiên"""
    if not markdown_content:
        return None
    matches = re.findall(r'```cpp\s*(.*?)\s*```', markdown_content, re.DOTALL)
    for code in matches:
        if "#include" in code and "main" in code:
            return code.strip()
    if matches:
        return matches[0].strip()
    return None

def run_testcase(exe_path, input_data, expected_output):
    """Chạy một testcase đơn lẻ và so khớp kết quả"""
    try:
        r = subprocess.run(
            [exe_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10
        )
        if r.returncode != 0:
            return "RTE", r.stderr.strip()
        
        # Làm sạch kết quả đầu ra (bỏ khoảng trắng thừa ở cuối dòng và cuối file)
        actual = "\n".join([line.rstrip() for line in r.stdout.strip().splitlines() if line.strip()])
        expected = "\n".join([line.rstrip() for line in expected_output.strip().splitlines() if line.strip()])
        
        if actual == expected:
            return "AC", ""
        else:
            return "WA", {
                "input": input_data[:300] + ("\n..." if len(input_data) > 300 else ""),
                "expected": expected[:300] + ("\n..." if len(expected) > 300 else ""),
                "actual": actual[:300] + ("\n..." if len(actual) > 300 else "")
            }
    except subprocess.TimeoutExpired:
        return "TLE", "Thời gian chạy vượt quá 10 giây."
    except Exception as e:
        return "RTE", str(e)

def test_problem(problem_code):
    print(f"==================================================")
    print(f"BẮT ĐẦU KIỂM THỬ BÀI GIẢI: {problem_code}")
    print(f"==================================================")
    
    # 1. Lấy đề bài và lời giải từ DB
    try:
        p = Problem.objects.get(code=problem_code)
    except Problem.DoesNotExist:
        print(f"❌ Lỗi: Bài tập '{problem_code}' không tồn tại trong cơ sở dữ liệu.")
        return False
        
    sol = Solution.objects.filter(problem=p).first()
    if not sol or not sol.content:
        print(f"❌ Lỗi: Không tìm thấy bài giải/editorial cho bài '{problem_code}'.")
        return False
        
    cpp_code = extract_cpp_code(sol.content)
    if not cpp_code:
        print(f"❌ Lỗi: Không trích xuất được mã nguồn C++ từ bài giải.")
        return False
        
    print(f"✅ Trích xuất mã nguồn C++ thành công ({len(cpp_code)} ký tự).")
    
    # 2. Tìm file ZIP testcases
    zip_path = find_zip_file(problem_code)
    if not zip_path:
        print(f"❌ Lỗi: Không tìm thấy file testcase {problem_code}.zip.")
        return False
    print(f"✅ Tìm thấy file zip testcase: {zip_path}")
    
    # 3. Tạo thư mục tạm và biên dịch
    tmp_dir = tempfile.mkdtemp()
    try:
        cpp_file = os.path.join(tmp_dir, "solution.cpp")
        exe_file = os.path.join(tmp_dir, "solution")
        
        with open(cpp_file, "w", encoding="utf-8") as f:
            f.write(cpp_code)
            
        print("🔨 Đang biên dịch mã nguồn C++ với g++ -O3...")
        r = subprocess.run(["g++", "-O3", "-std=c++17", "-o", exe_file, cpp_file], capture_output=True, text=True)
        if r.returncode != 0:
            print("❌ Lỗi biên dịch C++:")
            print(r.stderr)
            return False
        print("✅ Biên dịch thành công!")
        
        # 4. Giải nén testcases
        print("📦 Đang giải nén testcases...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)
            
        # Đọc danh sách các testcases
        in_files = []
        for file in os.listdir(tmp_dir):
            if file.endswith(".in"):
                in_files.append(file)
                
        # Sắp xếp số tự nhiên
        def get_num(s):
            m = re.search(r'\d+', s)
            return int(m.group()) if m else 0
        in_files.sort(key=get_num)
        
        if not in_files:
            print("❌ Lỗi: Không tìm thấy file .in nào trong zip.")
            return False
            
        print(f"🚀 Bắt đầu chạy thử {len(in_files)} testcases:")
        ac_count = 0
        for in_file in in_files:
            out_file = in_file[:-3] + ".out"
            in_path = os.path.join(tmp_dir, in_file)
            out_path = os.path.join(tmp_dir, out_file)
            
            if not os.path.exists(out_path):
                print(f"  - Testcase {in_file}: ⚠️ Lỗi (Thiếu file .out tương ứng)")
                continue
                
            with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
                inp_data = f.read()
            with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
                out_data = f.read()
                
            result, info = run_testcase(exe_file, inp_data, out_data)
            
            if result == "AC":
                ac_count += 1
                print(f"  - Testcase {in_file:8s}: \033[92mAC\033[0m")
            elif result == "WA":
                print(f"  - Testcase {in_file:8s}: \033[91mWA\033[0m")
                print(f"    [Chi tiết sai lệch]")
                print(f"    * Input:\n{info['input']}")
                print(f"    * Expected Output:\n{info['expected']}")
                print(f"    * Actual Output:\n{info['actual']}")
            else:
                print(f"  - Testcase {in_file:8s}: \033[93m{result}\033[0m (Error: {info})")
                
        print(f"==================================================")
        print(f"KẾT QUẢ CHUNG: Đạt {ac_count}/{len(in_files)} testcases.")
        if ac_count == len(in_files):
            print(f"\033[92m⭐ HOÀN TOÀN CHÍNH XÁC (ALL TESTS PASSED) ⭐\033[0m")
            return True
        else:
            print(f"\033[91m⚠️ CÓ TESTCASE BỊ SAI (SOME TESTS FAILED) ⚠️\033[0m")
            return False
            
    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python test_solution.py <problem_code>")
        sys.exit(1)
    
    prob_code = sys.argv[1]
    success = test_problem(prob_code)
    sys.exit(0 if success else 1)
