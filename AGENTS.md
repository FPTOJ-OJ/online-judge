# DMOJ CLI Tools for AI Agents

This document describes all CLI management commands for administrators to manage problems, testcases, data files, quizzes/exams, and translations programmatically.

Note: you can see venv in dmojsite/bin/activate or use host python

---
Prefer file-based for problem if you can!
---
## 3. User Management CLI (`user_cli`)

Single unified command: `python manage.py user_cli <subcommand> [options]`

### 3.1 List Users

```bash
# List all users
python manage.py user_cli list

# Filter by role
python manage.py user_cli list --staff          # Người có quyền staff (admin)
python manage.py user_cli list --superuser       # Superuser (toàn quyền)
python manage.py user_cli list --setter          # Problem Setter (giáo viên)
python manage.py user_cli list --admin           # Profile rank Admin

# Filter active/inactive
python manage.py user_cli list --active
python manage.py user_cli list --search "kien"

# JSON output
python manage.py user_cli list --json
python manage.py user_cli list --staff --json    # Admin list dạng JSON
```

Cột hiển thị: Username, Email, Active (✓/✗), Staff, Superuser, Rank (Normal User / Problem Setter / Admin), Organizations.

### 3.2 View User Details

```bash
python manage.py user_cli detail <username>
```

Hiển thị:
- Thông tin cơ bản: username, email, active, staff, superuser, display rank
- Profile: organizations, problems solved, points, muted, unlisted, notes
- Django Groups
- **Full permissions list** (tất cả quyền của user)

### 3.3 Create User

```bash
# Tạo user thường
python manage.py user_cli create <username> --email user@example.com

# Tạo với mật khẩu chỉ định
python manage.py user_cli create <username> --password "secret123"

# Tạo giáo viên (setter + staff)
python manage.py user_cli create <username> --setter --staff
```

Nếu không có `--password`, tự động sinh mật khẩu ngẫu nhiên 12 ký tự và in ra màn hình.

### 3.4 Promote User

```bash
# Cấp quyền staff (admin Django)
python manage.py user_cli promote <username> --staff

# Cấp superuser (toàn quyền)
python manage.py user_cli promote <username> --superuser

# Đặt rank Problem Setter (giáo viên)
python manage.py user_cli promote <username> --setter

# Đặt rank Admin
python manage.py user_cli promote <username> --admin-rank

# Kết hợp nhiều quyền
python manage.py user_cli promote <username> --staff --setter
```

### 3.5 Demote User

```bash
# Thu hồi quyền staff
python manage.py user_cli demote <username> --staff

# Thu hồi superuser
python manage.py user_cli demote <username> --superuser
```

### 3.6 Activate / Deactivate User

```bash
# Kích hoạt tài khoản
python manage.py user_cli activate <username>

# Vô hiệu hóa (không thể vô hiệu hóa superuser)
python manage.py user_cli deactivate <username>
```

**Vai trò trong hệ thống:**

| Role | is_staff | is_superuser | display_rank | Ý nghĩa |
|------|----------|-------------|--------------|---------|
| **Superuser** | ✓ | ✓ | admin | Toàn quyền, thấy mọi thứ |
| **Staff** | ✓ | ✗ | admin/setter | Vào được admin, có quyền được cấp |
| **Problem Setter** | ✗ | ✗ | setter | Được coi là teacher, tạo/quản lý đề thi |
| **Normal User** | ✗ | ✗ | user | Người dùng thường |

---

## Table of Contents

1. [Problem Management CLI (`problem_cli`)](#1-problem-management-cli-problem_cli)
2. [Quiz/Exam Management CLI (`quiz_cli`)](#2-quizexam-management-cli-quiz_cli)
3. [User Management CLI (`user_cli`)](#3-user-management-cli-user_cli)
4. [Bulk JSON Import](#4-bulk-json-import)
5. [Seed Sample Quiz Data](#5-seed-sample-quiz-data)
6. [Translations](#6-translations)
7. [Quick Reference](#7-quick-reference)

---

## 1. Problem Management CLI (`problem_cli`)

Single unified command: `python manage.py problem_cli <subcommand> [options]`

### 1.1 List Problems

```bash
python manage.py problem_cli list
python manage.py problem_cli list --public
python manage.py problem_cli list --private
python manage.py problem_cli list --type dp
python manage.py problem_cli list --group usaco
python manage.py problem_cli list --org my-school
python manage.py problem_cli list --search "hello"
python manage.py problem_cli list --json
```

### 1.2 View Problem Details

```bash
python manage.py problem_cli detail <problem_code>
```

### 1.3 Create a Problem

```bash
python manage.py problem_cli create <code> <name> \
    --type <type_id> --group <group_id> \
    --description "Problem statement" \
    --points 10 --time-limit 1.0 --memory-limit 65536 \
    --public --author "admin"
    --org-private                               # Restrict to org members

# Dùng file cho description để tránh lỗi bash escaping (khuyên dùng)
python manage.py problem_cli create <code> <name> \
    --type bitwise --group fptoj \
    --description-file path/to/description.md \
    --editorial-file path/to/editorial.md \
    --points 10 --public --author kienadmin
```

### 1.4 Update a Problem

```bash
python manage.py problem_cli update <code> \
    --name "New Title" --description "New" \
    --type dp --group usaco \
    --points 20 --time-limit 2.0 \
    --public

# Dùng file cho description/editorial
python manage.py problem_cli update <code> \
    --description-file path/to/description.md \
    --editorial-file path/to/editorial.md
```

### 1.5 Delete a Problem

```bash
python manage.py problem_cli delete <code>
python manage.py problem_cli delete <code> --force
```

### 1.6 Manage Testcases

```bash
# List testcases
python manage.py problem_cli testcase list <code>
python manage.py problem_cli testcase list <code> --json

# Add a generator-based testcase (ƯU TIÊN DÙNG)
python manage.py problem_cli testcase add <code> \
    --generator-args "5 10" --points 2

# Add a file-based testcase
python manage.py problem_cli testcase add <code> \
    --input test.in --output test.out --points 1

# Add a pretest
python manage.py problem_cli testcase add <code> \
    --input pretest.in --output pretest.out --points 1 --pretest

# Add with custom checker
python manage.py problem_cli testcase add <code> \
    --input test.in --output test.out --points 1 \
    --checker "custom_checker" --checker-args "arg1 arg2"

# Add batch start/end
python manage.py problem_cli testcase add <code> --type S --points 10
python manage.py problem_cli testcase add <code> --type E

# Batch with dependencies
python manage.py problem_cli testcase add <code> --type S --points 10 \
    --batch-dependencies "1,2"

# Delete a testcase
python manage.py problem_cli testcase delete <code> <testcase_id>
```

### 1.7 Manage Problem Data Files

```bash
python manage.py problem_cli data show <code>
python manage.py problem_cli data upload-zip <code> /path/to/data.zip
python manage.py problem_cli data upload-generator <code> /path/to/gen.py
python manage.py problem_cli data compile <code>
```

### 1.8 Manage Problem Types & Groups

```bash
python manage.py problem_cli type list
python manage.py problem_cli type list --json
python manage.py problem_cli type add dp "Dynamic Programming"

python manage.py problem_cli group list
python manage.py problem_cli group list --json
python manage.py problem_cli group add usaco "USACO"
python manage.py problem_cli group delete cses    # Xóa group (chỉ khi không còn problem nào)
```

### 1.9 Manage Authors

```bash
python manage.py problem_cli author add <code> <username>
python manage.py problem_cli author remove <code> <username>
```

### 1.10 Manage Editorial (Lời giải)

*Editorial là phần lời giải của bài toán, hiển thị sau khi học sinh nộp bài.*

```bash
# Tạo problem kèm editorial
python manage.py problem_cli create <code> <name> \
    --editorial "# Lời giải\nDùng XOR: $a \oplus a = 0$"

# Tạo problem với file editorial
python manage.py problem_cli create <code> <name> \
    --editorial-file path/to/editorial.md

# Cập nhật editorial
python manage.py problem_cli update <code> \
    --editorial "# Lời giải mới\n..."

# Cập nhật editorial từ file
python manage.py problem_cli update <code> \
    --editorial-file path/to/editorial.md

# Xem editorial
python manage.py shell -c "
from judge.models import Problem, Solution
sol = Solution.objects.filter(problem=Problem.objects.get(code='<code>')).first()
print(sol.content if sol else '(none)')
"
```

---

## 2. Quiz/Exam Management CLI (`quiz_cli`)

Single unified command: `python manage.py quiz_cli <subcommand> [options]`

### 2.1 Manage Exams

```bash
python manage.py quiz_cli exam list
python manage.py quiz_cli exam list --visible
python manage.py quiz_cli exam list --featured --locked
python manage.py quiz_cli exam list --search "exam name"
python manage.py quiz_cli exam list --json

python manage.py quiz_cli exam detail <exam_id>

python manage.py quiz_cli exam create "Exam Name" \
    --description "Description" \
    --duration 60 --visible --featured --login --locked --org-only \
    --author admin

python manage.py quiz_cli exam update <id> \
    --name "New Name" --duration 90 \
    --visible yes --featured no --login yes --locked no --org-only no

python manage.py quiz_cli exam delete <id>
python manage.py quiz_cli exam delete <id> --force
```

### 2.2 Manage Exam Questions

```bash
# List questions
python manage.py quiz_cli exam question list <exam_id>
python manage.py quiz_cli exam question list <exam_id> --json

# Add multiple-choice question (mỗi --option là 1 lựa chọn)
python manage.py quiz_cli exam question add <exam_id> \
    --content "What is 2+2?" \
    --type choice --difficulty easy \
    --option 'A:"3":false' \
    --option 'B:"4":true' \
    --option 'C:"5":false' \
    --option 'D:"6":false' \
    --tag khmt

# Add True/False cluster question
python manage.py quiz_cli exam question add <exam_id> \
    --content "Which statements are correct?" \
    --type tf --difficulty medium \
    --option 'a:"Statement 1":true' \
    --option 'b:"Statement 2":false' \
    --option 'c:"Statement 3":true' \
    --option 'd:"Statement 4":false' \
    --explanation "Explanation text" \
    --tag thud

# Update question
python manage.py quiz_cli exam question update <qid> \
    --content "New text" --type choice --difficulty hard \
    --tag khmt --tag thud \
    --option 'A:"New A":false' --option 'B:"New B":true'

# Remove from exam (keeps question in DB)
python manage.py quiz_cli exam question remove <exam_id> <qid>

# Permanently delete question
python manage.py quiz_cli exam question delete <qid>
python manage.py quiz_cli exam question delete <qid> --force
```

### 2.3 Manage Tags

```bash
python manage.py quiz_cli tag list
python manage.py quiz_cli tag list --json
python manage.py quiz_cli tag add "KHMT" khmt
python manage.py quiz_cli tag delete <slug>
```

### 2.4 Full Workflow: Create Exam

```bash
# 1. Tags
python manage.py quiz_cli tag add "KHMT" khmt
python manage.py quiz_cli tag add "THUD" thud

# 2. Exam
python manage.py quiz_cli exam create "Kiểm Tra 1 Tiết" \
    --description "Nội dung: Lập trình C++" \
    --duration 45 --visible --login

# 3. Questions (có thể lấy exam_id từ output step 2, hoặc dùng exam list)
python manage.py quiz_cli exam question add 5 \
    --content "Câu hỏi 1: Biến là gì?" \
    --type choice --difficulty easy \
    --option 'A:"Hằng số":false' --option 'B:"Vùng nhớ":true' \
    --option 'C:"Hàm":false' --option 'D:"Lớp":false'

python manage.py quiz_cli exam question add 5 \
    --content "Xác định đúng/sai các phát biểu về C++:" \
    --type tf --difficulty medium \
    --option 'a:"int* p = new int[10]; // Cấp phát động":true' \
    --option 'b:"cout << &x; // In địa chỉ của x":true' \
    --option 'c:"string là kiểu nguyên thủy của C++":false' \
    --explanation "string là class trong thư viện chuẩn, không phải kiểu nguyên thủy."

# 4. Verify
python manage.py quiz_cli exam detail 5
python manage.py quiz_cli exam question list 5 --json
```

---

## 3. Bulk JSON Import

### 3.1 Bulk Import Problems

```bash
python manage.py problem_cli bulk <json_file>
python manage.py problem_cli bulk <json_file> --dry-run  # Validate without creating
python manage.py problem_cli bulk <json_file> --json      # JSON output
```

**Cấu trúc JSON (Generator-Based — ƯU TIÊN):**

```json
{
  "problems": [
    {
      "code": "bai-tap-1",
      "name": "Tính Tổng Hai Số",
      "description": "Cho a, b. In ra a + b.",
      "type": "custom",
      "group": "contest",
      "points": 5,
      "public": true,
      "time_limit": 1.0,
      "memory_limit": 65536,
      "author": "admin",
      "generator": "/path/to/gen_sum.cpp",
      "testcases": [
        {"generator_args": "1 10", "points": 1},
        {"generator_args": "100 200", "points": 2},
        {"generator_args": "1000000 2000000", "points": 2}
      ]
    },
    {
      "code": "bai-tap-2",
      "name": "Tìm Số Lớn Nhất",
      "description": "In ra số lớn nhất trong dãy.",
      "type": "custom",
      "group": "contest",
      "points": 7,
      "public": true,
      "generator": "/path/to/gen_max.cpp",
      "testcases": [
        {"generator_args": "10 100", "points": 2},
        {"generator_args": "100 1000", "points": 2},
        {"generator_args": "1000 100000", "points": 3}
      ]
    }
  ]
}
```

**Cấu trúc JSON (File-Based — khi cần dữ liệu cố định):**

```json
{
  "problems": [
    {
      "code": "bai-tap-3",
      "name": "Đọc Ghi File",
      "type": "custom",
      "group": "contest",
      "points": 10,
      "zip": "/path/to/data.zip",
      "testcases": [
        {"input": "test1.in", "output": "test1.out", "points": 5},
        {"input": "test2.in", "output": "test2.out", "points": 5}
      ]
    }
  ]
}
```

**Cấu trúc JSON (Batch Testcases):**

```json
{
  "problems": [
    {
      "code": "batch-demo",
      "name": "Batch Demo",
      "type": "custom",
      "group": "contest",
      "generator": "/path/to/gen.cpp",
      "testcases": [
        {"type": "S", "generator_args": "10", "points": 5},
        {"type": "C", "generator_args": "100"},
        {"type": "C", "generator_args": "1000"},
        {"type": "E"},
        {"type": "S", "generator_args": "10000", "points": 10, "batch_dependencies": "1"},
        {"type": "C", "generator_args": "100000"},
        {"type": "E"}
      ]
    }
  ]
}
```

### 3.2 Bulk Import Exams

```bash
python manage.py quiz_cli bulk <json_file>
python manage.py quiz_cli bulk <json_file> --dry-run
python manage.py quiz_cli bulk <json_file> --json
```

**Cấu trúc JSON:**

```json
{
  "exams": [
    {
      "name": "Bài Kiểm Tra Giữa Kỳ",
      "description": "Kiến thức cơ bản.",
      "duration": 60,
      "visible": false,
      "featured": false,
      "login": true,
      "locked": false,
      "org_only": false,
      "author": "admin",
      "tags": [
        {"name": "KHMT", "slug": "khmt"},
        {"name": "THUD", "slug": "thud"}
      ],
      "questions": [
        {
          "content": "Câu hỏi 1: 2+2=?",
          "type": "choice",
          "difficulty": "easy",
          "tags": ["khmt"],
          "explanation": "Giải thích...",
          "options": [
            {"label": "A", "content": "3", "is_correct": false},
            {"label": "B", "content": "4", "is_correct": true},
            {"label": "C", "content": "5", "is_correct": false},
            {"label": "D", "content": "6", "is_correct": false}
          ]
        },
        {
          "content": "Xác định đúng/sai:",
          "type": "tf",
          "difficulty": "medium",
          "tags": ["thud"],
          "options": [
            {"label": "a", "content": "Phát biểu 1", "is_correct": true},
            {"label": "b", "content": "Phát biểu 2", "is_correct": false}
          ]
        }
      ]
    }
  ]
}
```

**Tags tự động được tạo** nếu chưa tồn tại (dựa vào `slug`). Không cần tạo tag trước.

### Ví dụ thực tế: Bulk — Generator C++

```bash
# 1. Tạo generator C++: gen_sum.cpp
cat > gen_sum.cpp << 'EOF'
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char* argv[]) {
    int min_n = atoi(argv[1]);
    int max_n = atoi(argv[2]);
    srand(time(0) + clock());
    int a = rand() % (max_n - min_n + 1) + min_n;
    int b = rand() % (max_n - min_n + 1) + min_n;
    cout << a << " " << b << endl;
    return 0;
}
EOF

# 2. Tạo JSON: problems.json (xem cấu trúc ở trên)
# 3. Import 10 problem trong 1 lệnh:
python manage.py problem_cli bulk problems.json

# 4. Kiểm tra
python manage.py problem_cli list --search "bai-tap"
```

---

## 4. Seed Sample Quiz Data

```bash
python manage.py seed_quiz_sample
python manage.py seed_quiz_sample --force
```

---

## 5. Translations

```bash
python manage.py compilemessages -l vi
python manage.py makemessages -l vi
```

---

## 6. Quick Reference

### Problem Management

| Task | Command |
|------|---------|
| List problems | `python manage.py problem_cli list` |
| View details | `python manage.py problem_cli detail <code>` |
| Create problem | `python manage.py problem_cli create <code> <name> --type X --group Y` |
| Create problem (file desc) | `python manage.py problem_cli create <code> <name> --type X --group Y --description-file path.md --editorial-file path.md` |
| Update problem | `python manage.py problem_cli update <code> --name "..."` |
| Update description file | `python manage.py problem_cli update <code> --description-file path.md` |
| Update editorial file | `python manage.py problem_cli update <code> --editorial-file path.md` |
| Delete problem | `python manage.py problem_cli delete <code> --force` |
| List testcases | `python manage.py problem_cli testcase list <code>` |
| Add testcase (generator) | `python manage.py problem_cli testcase add <code> --generator-args "..." --points N` |
| Add testcase (file) | `python manage.py problem_cli testcase add <code> --input X --output Y --points N` |
| Add batch start | `python manage.py problem_cli testcase add <code> --type S --points N` |
| Add batch end | `python manage.py problem_cli testcase add <code> --type E` |
| Delete testcase | `python manage.py problem_cli testcase delete <code> <id>` |
| Upload zip | `python manage.py problem_cli data upload-zip <code> <path>` |
| Upload generator | `python manage.py problem_cli data upload-generator <code> <path>` |
| Compile init.yml | `python manage.py problem_cli data compile <code>` |
| Bulk import problems | `python manage.py problem_cli bulk <json_file>` |
| Bulk import (dry-run) | `python manage.py problem_cli bulk <json_file> --dry-run` |
| List types | `python manage.py problem_cli type list` |
| Add type | `python manage.py problem_cli type add <id> "Name"` |
| List groups | `python manage.py problem_cli group list` |
| Add group | `python manage.py problem_cli group add <id> "Name"` |
| Delete group | `python manage.py problem_cli group delete <id>` |
| Add author | `python manage.py problem_cli author add <code> <username>` |
| Remove author | `python manage.py problem_cli author remove <code> <username>` |

### User Management

| Task | Command |
|------|---------|
| List users | `python manage.py user_cli list` |
| List staff/admins | `python manage.py user_cli list --staff` |
| List superusers | `python manage.py user_cli list --superuser` |
| List setters | `python manage.py user_cli list --setter` |
| View user details | `python manage.py user_cli detail <username>` |
| Promote (staff) | `python manage.py user_cli promote <username> --staff` |
| Promote (superuser) | `python manage.py user_cli promote <username> --superuser` |
| Promote (setter) | `python manage.py user_cli promote <username> --setter` |
| Promote (admin rank) | `python manage.py user_cli promote <username> --admin-rank` |
| Demote (staff) | `python manage.py user_cli demote <username> --staff` |
| Demote (superuser) | `python manage.py user_cli demote <username> --superuser` |
| Create user | `python manage.py user_cli create <username> --email ...` |
| Activate user | `python manage.py user_cli activate <username>` |
| Deactivate user | `python manage.py user_cli deactivate <username>` |

### Quiz/Exam Management

| Task | Command |
|------|---------|
| List exams | `python manage.py quiz_cli exam list` |
| View exam | `python manage.py quiz_cli exam detail <id>` |
| Create exam | `python manage.py quiz_cli exam create "Name" --duration 60` |
| Update exam | `python manage.py quiz_cli exam update <id> --name "..."` |
| Delete exam | `python manage.py quiz_cli exam delete <id> --force` |
| List questions | `python manage.py quiz_cli exam question list <exam_id>` |
| Add question (MC) | `python manage.py quiz_cli exam question add <id> --type choice --option 'A:"A":true'` |
| Add question (TF) | `python manage.py quiz_cli exam question add <id> --type tf --option 'a:"S":true'` |
| Update question | `python manage.py quiz_cli exam question update <qid> --content "..."` |
| Remove question | `python manage.py quiz_cli exam question remove <exam_id> <qid>` |
| Delete question | `python manage.py quiz_cli exam question delete <qid> --force` |
| List tags | `python manage.py quiz_cli tag list` |
| Add tag | `python manage.py quiz_cli tag add "Name" slug` |
| Delete tag | `python manage.py quiz_cli tag delete <slug>` |
| Bulk import exams | `python manage.py quiz_cli bulk <json_file>` |
| Bulk import (dry-run) | `python manage.py quiz_cli bulk <json_file> --dry-run` |

### Other

| Task | Command |
|------|---------|
| Seed sample exam | `python manage.py seed_quiz_sample` |
| Compile translations | `python manage.py compilemessages -l vi` |
| Extract translations | `python manage.py makemessages -l vi` |

# Hướng Dẫn Viết C++ Generator Cho FPTOJ/DMOJ

Khi tạo các bài toán trên hệ thống FPTOJ, việc sử dụng các kịch bản sinh dữ liệu mẫu (**Generator-based testcases**) bằng C++ là giải pháp tối ưu giúp hệ thống tự sinh dữ liệu kiểm thử trực tiếp trên judge server.

Tài liệu này hướng dẫn chi tiết cách thiết kế và triển khai mã nguồn bộ sinh kiểm thử bằng C++ đúng quy chuẩn của DMOJ, giúp tránh các lỗi biên dịch hoặc lỗi hệ thống chấm bài.

---

## 1. Cơ Chế Chạy Generator Của DMOJ

DMOJ Judge Server thực hiện quy trình sau đối với mỗi testcase dùng generator:
1.  **Biên dịch:** Judge biên dịch mã nguồn C++ generator (`.cpp`) thành mã máy.
2.  **Sinh Input:** Chạy tệp tin thực thi của generator, truyền các tham số cấu hình trong `init.yml` (`generator_args`). 
    *   **Dữ liệu Input** được sinh ra bằng cách ghi vào **Standard Output (`stdout`)**.
3.  **Sinh Expected Output (Đáp án chuẩn):** 
    *   **Dữ liệu Đáp án chuẩn** được thu thập từ **Standard Error (`stderr`)** của generator.
    *   *Chú ý:* DMOJ không tự chạy code mẫu của bạn để so khớp kết quả mà lấy trực tiếp kết quả chạy từ `stderr` của generator làm đáp án chuẩn để chấm bài của thí sinh.

---

## 2. Cạm Bẫy 1: Cách DMOJ Truyền Tham Số (`argv`)

Khi bạn thiết lập tham số sinh testcase qua CLI:
`python manage.py problem_cli testcase add <code> --generator-args "10 100 1" --points 2`

DMOJ sẽ ghi nhận chuỗi `"10 100 1"` như là một dòng văn bản duy nhất trong cấu hình `init.yml`. Khi gọi file thực thi của generator, judge server **không tự động tách các tham số bằng khoảng trắng**, mà truyền toàn bộ dòng văn bản này thành **một tham số duy nhất**.

Do đó:
*   Mã máy thực thi nhận: `argc = 2` (bao gồm tên chương trình và chuỗi tham số).
*   `argv[1]` sẽ bằng `"10 100 1"`.
*   Nếu code C++ của bạn kiểm tra tham số kiểu truyền thống `if (argc < 4) return 1;`, chương trình sẽ lập tức kết thúc với mã lỗi `1`, dẫn đến lỗi hệ thống chấm bài (**Internal Error**).

### Giải pháp xử lý tham số chuẩn hóa:
Sử dụng hàm tiện ích sau để tự động phân tách khoảng trắng trong trường hợp tham số bị gom cụm trong `argv[1]`:

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <sstream>

using namespace std;

vector<string> parse_args(int argc, char* argv[]) {
    vector<string> args;
    if (argc < 2) return args;
    
    string first_arg = argv[1];
    // Nếu chỉ có 1 tham số lớn chứa khoảng cách, thực hiện chia nhỏ bằng stringstream
    if (argc == 2 && first_arg.find(' ') != string::npos) {
        stringstream ss(first_arg);
        string temp;
        while (ss >> temp) {
            args.push_back(temp);
        }
    } else {
        for (int i = 1; i < argc; ++i) {
            args.push_back(argv[i]);
        }
    }
    return args;
}
```

---

## 3. Cạm Bẫy 2: Phân Biệt Luồng Output (`cout` vs `cerr`)

Bộ generator của bạn bắt buộc phải có 2 nhiệm vụ chạy đồng thời:
1.  In dữ liệu đề bài (Input) ra màn hình bằng `cout` (`stdout`).
2.  Tự giải bài toán đó với dữ liệu vừa sinh ra, và in đáp án đúng ra bằng `cerr` (`stderr`).

Nếu bạn quên không ghi đáp án ra `cerr`, DMOJ sẽ coi đáp án chuẩn của testcase đó là chuỗi rỗng (`""`), dẫn đến việc mọi bài nộp của học sinh (dù code đúng) đều bị báo sai kết quả (**Wrong Answer**).

---

## 4. Bộ Khung Generator C++ Chuẩn (Template)

Dưới đây là mã nguồn mẫu hoàn chỉnh cho một bài toán sinh ngẫu nhiên hai số $A, B$ và yêu cầu tính tổng $A + B$:

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <random>

using namespace std;

// Hàm phân tích tham số an toàn
vector<string> parse_args(int argc, char* argv[]) {
    vector<string> args;
    if (argc < 2) return args;
    string first_arg = argv[1];
    if (argc == 2 && first_arg.find(' ') != string::npos) {
        stringstream ss(first_arg);
        string temp;
        while (ss >> temp) args.push_back(temp);
    } else {
        for (int i = 1; i < argc; ++i) args.push_back(argv[i]);
    }
    return args;
}

int main(int argc, char* argv[]) {
    // 1. Phân tích tham số đầu vào
    vector<string> args = parse_args(argc, argv);
    if (args.size() < 2) {
        cerr << "Error: Thieu tham so sinh testcase!\n";
        return 1;
    }
    
    long long max_val = stoll(args[0]); // Giới hạn giá trị của A và B
    long long seed = stoll(args[1]);    // Seed ngẫu nhiên
    
    // 2. Khởi tạo bộ sinh số ngẫu nhiên
    mt19937_64 rng(seed);
    
    long long a = rng() % max_val + 1;
    long long b = rng() % max_val + 1;
    
    // 3. Ghi INPUT ra stdout (cout)
    cout << a << " " << b << "\n";
    
    // 4. Ghi OUTPUT (Đáp án chuẩn) ra stderr (cerr)
    long long answer = a + b;
    cerr << answer << "\n";
    
    return 0;
}
```

---

## 5. Quy Trình Cấu Hình Bài Toán Qua CLI

Khi đã viết xong tệp tin generator (ví dụ: `tong_gen.cpp`), bạn thực hiện nạp vào hệ thống theo các bước sau:

1.  **Tải generator lên hệ thống:**
    ```bash
    python manage.py problem_cli data upload-generator <mã_bài> /đường_dẫn/tong_gen.cpp
    ```
2.  **Đăng ký các testcase với tham số sinh (`generator_args`):**
    ```bash
    # Testcase 1 (10 điểm, sinh số <= 100, seed 1)
    python manage.py problem_cli testcase add <mã_bài> --generator-args "100 1" --points 10
    
    # Testcase 2 (20 điểm, sinh số <= 10^9, seed 2)
    python manage.py problem_cli testcase add <mã_bài> --generator-args "1000000000 2" --points 20
    ```
3.  **Yêu cầu hệ thống biên dịch và chuẩn bị dữ liệu:**
    ```bash
    python manage.py problem_cli data compile <mã_bài>
    ```

*Chú ý:* Luôn kiểm tra log biên dịch ở bước 3, nếu hệ thống báo `init.yml compiled for "<mã_bài>"` thành công tức là bộ generator của bạn đã hoạt động chuẩn xác!
