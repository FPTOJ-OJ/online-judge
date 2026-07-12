#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

SITE = "/home/kien/site"
VENV_PY = os.path.join(SITE, "dmojsite/bin/python3")

# Automatically configure environment variables
ENV = os.environ.copy()
ENV["LD_PRELOAD"] = "/usr/lib/x86_64-linux-gnu/libstdc++.so.6"

def run_script(script_path):
    """Chạy một script python tạo bài tập hoặc đồng bộ với môi trường DMOJ chuẩn"""
    if not os.path.exists(script_path):
        print(f"❌ Lỗi: Không tìm thấy file script '{script_path}'")
        return False
        
    print(f"🚀 Đang chạy script: {script_path}...")
    r = subprocess.run([VENV_PY, script_path], env=ENV)
    if r.returncode == 0:
        print(f"✅ Chạy script '{script_path}' thành công!")
        return True
    else:
        print(f"❌ Lỗi: Script '{script_path}' thất bại với mã thoát: {r.returncode}")
        return False

def test_problem(problem_code):
    """Chạy công cụ kiểm thử test_solution.py trên bài tập chỉ định"""
    test_script = os.path.join(SITE, "tmp_problems/test_solution.py")
    if not os.path.exists(test_script):
        print(f"❌ Lỗi: Không tìm thấy công cụ kiểm thử '{test_script}'")
        return False
        
    print(f"🔎 Đang chạy kiểm thử lời giải bài: {problem_code}...")
    r = subprocess.run([VENV_PY, test_script, problem_code], env=ENV)
    return r.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="FPTOJ Problem Manager - Công cụ quản lý bài tập tích hợp cho AI Agent")
    subparsers = parser.add_subparsers(dest="command", help="Các lệnh hỗ trợ")
    
    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Chạy một script python tạo bài tập")
    run_parser.add_argument("script", help="Đường dẫn tới script python (ví dụ: tmp_problems/sl-min-max.py)")
    
    # Subcommand: test
    test_parser = subparsers.add_parser("test", help="Kiểm thử bài giải mẫu của bài tập bằng testcase hệ thống")
    test_parser.add_argument("code", help="Mã bài tập cần kiểm thử (ví dụ: sl-min-max)")
    
    # Subcommand: sync
    sync_parser = subparsers.add_parser("sync", help="Đồng bộ lời giải từ script cập nhật editorial")
    sync_parser.add_argument("script", help="Đường dẫn tới script update editorial (ví dụ: tmp_problems/update_sl_editorials.py)")
    
    # Subcommand: batch
    batch_parser = subparsers.add_parser("batch", help="Chạy và kiểm thử hàng loạt các bài tập")
    batch_parser.add_argument("scripts", nargs="+", help="Danh sách các file script bài tập cần chạy")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    if args.command == "run":
        success = run_script(args.script)
        sys.exit(0 if success else 1)
        
    elif args.command == "test":
        success = test_problem(args.code)
        sys.exit(0 if success else 1)
        
    elif args.command == "sync":
        success = run_script(args.script)
        sys.exit(0 if success else 1)
        
    elif args.command == "batch":
        print(f"📦 Bắt đầu xử lý hàng loạt {len(args.scripts)} bài tập...")
        failed_runs = []
        failed_tests = []
        
        for s in args.scripts:
            # Chạy script tạo bài
            if not run_script(s):
                failed_runs.append(s)
                continue
                
            # Đọc mã bài từ tên file hoặc chạy kiểm thử nếu xác định được
            # Ví dụ tên file là tmp_problems/sl-min-max.py -> mã bài là sl-min-max
            base = os.path.basename(s)
            if base.endswith(".py"):
                code = base[:-3]
                if not test_problem(code):
                    failed_tests.append(code)
                    
        print("\n==================================================")
        print("TỔNG KẾT BATCH RUN:")
        print(f"- Thành công: {len(args.scripts) - len(failed_runs) - len(failed_tests)}/{len(args.scripts)}")
        if failed_runs:
            print(f"- Thất bại khi chạy tạo bài: {failed_runs}")
        if failed_tests:
            print(f"- Thất bại khi chạy kiểm thử: {failed_tests}")
        print("==================================================")
        
        sys.exit(1 if (failed_runs or failed_tests) else 0)

if __name__ == "__main__":
    main()
