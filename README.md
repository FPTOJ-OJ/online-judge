<h1 align="center">
  <img src="https://github.com/FPTOJ-OJ/online-judge/blob/main/logo.png?raw=true" width="120px">
  <br>
  FPTOJ: FPT Online Judge
</h1>
<p align="center">
  <a href="https://github.com/FPTOJ-OJ/online-judge/actions?query=workflow%3Abuild">
   <img alt="Build Status" src="https://img.shields.io/github/actions/workflow/status/FPTOJ-OJ/online-judge/build.yml?branch=main"/>
  </a>
  <a href="LICENSE.md">
    <img alt="License" src="https://img.shields.io/github/license/FPTOJ-OJ/online-judge"/>
  </a>
</p>

[**Bản tiếng Việt**](#bản-tiếng-việt) | [**English Version**](#english)

---

<a id="bản-tiếng-việt"></a>
# Bản tiếng Việt

Hệ thống chấm bài trực tuyến (Online Judge) và nền tảng tổ chức kỳ thi lập trình hiện đại, hiệu năng cao, dựa trên mã nguồn mở DMOJ. Hệ thống FPTOJ được phát triển và tối ưu hóa nhằm phục vụ cho hoạt động giảng dạy, học tập và kiểm tra đánh giá tin học tại Việt Nam.

Trải nghiệm trực tiếp tại [fptoj.com](https://fptoj.com/)!

## Các tính năng mở rộng đặc trưng (FPTOJ Extensions)

FPTOJ được tích hợp thêm nhiều tính năng độc quyền và tùy chỉnh sâu để phù hợp với môi trường giáo dục phổ thông và đại học:

### 1. Cấu hình Trang web Linh hoạt (Site Configuration)
Quản trị viên có thể tùy biến sâu giao diện và hoạt động của trang web trực tiếp từ trang Admin mà không cần can thiệp vào mã nguồn:
* **Tối ưu hóa ảnh Logo & Favicon**: Tự động xử lý ảnh tải lên bằng thư viện **Pillow**. Khi tải lên logo mới hoặc favicon mới, hệ thống sẽ:
  - Tự động chuyển đổi định dạng sang PNG tối ưu (trừ trường hợp tệp Vector SVG).
  - Tự động thay đổi kích thước về tỷ lệ chuẩn (Logo giới hạn kích thước tối đa `600x150`, Favicon giới hạn tối đa `128x128`) giúp tránh phình dung lượng trang và tăng tốc độ tải.
  - Tự động nén chất lượng cao và loại bỏ siêu dữ liệu ẩn (metadata) của ảnh để bảo mật.
* **Tùy biến kiểu dáng Logo (Logo Custom Style)**: Cho phép chèn mã CSS nội dòng trực tiếp áp dụng cho logo hiển thị trên thanh điều hướng (ví dụ: `width: 130px; height: auto; filter: drop-shadow(0 0 4px rgba(255,255,255,0.3));`).
* **Trình nhúng CSS & JS tùy chỉnh (Custom CSS/JS Injector)**:
  - **CSS tùy chỉnh**: Cho phép ghi đè/chèn các quy tắc CSS toàn trang để thay đổi màu sắc chủ đạo, font chữ, khoảng cách các khối theo nhận diện thương hiệu riêng.
  - **Javascript tùy chỉnh**: Hỗ trợ nhúng mã script ở cuối trang (ngay trước thẻ đóng `</body>`), phục vụ cho việc cài đặt Google Analytics, chat widget, hoặc các đoạn mã tương tác tùy ý.
* **Tùy biến chân trang (Footer Customization)**:
  - Thêm nội dung bản quyền hoặc liên kết chân trang bằng mã HTML tùy ý thông qua trường `Custom Footer HTML`.
  - Tùy chọn **Ghi đè chân trang mặc định (Override Default Footer)** để ẩn hoàn toàn thông tin mặc định của DMOJ và chỉ hiển thị thông tin bản quyền riêng của đơn vị sở hữu.

### 2. Hệ thống Luyện trắc nghiệm & Thi thử Tốt nghiệp (Quiz/Exam)
Hệ thống thi trắc nghiệm được thiết kế chuyên biệt bám sát định dạng cấu trúc đề thi tốt nghiệp THPT từ năm 2025:
* **Cấu trúc Đề thi phân hóa định hướng**:
  - **Phần I (Trắc nghiệm nhiều lựa chọn)**: Gồm 24 câu hỏi trắc nghiệm truyền thống, mỗi câu có 4 lựa chọn (A, B, C, D) và chỉ có duy nhất 1 đáp án đúng. Mỗi câu trả lời đúng được tính 0.25 điểm.
  - **Phần II (Trắc nghiệm Đúng/Sai)**: Gồm các câu hỏi chùm Đúng/Sai, mỗi câu hỏi có 4 mệnh đề nhỏ độc lập (a, b, c, d) yêu cầu thí sinh trả lời Đúng hoặc Sai.
* **Phân chia Định hướng môn học**:
  - Đề thi hỗ trợ hai định hướng: **Khoa học máy tính (KHMT)** và **Tin học ứng dụng (THUD)**.
  - Phần II được phân chia: **Câu 1 & Câu 2** là câu hỏi chung cho cả 2 định hướng. **Câu 3 & Câu 4** dành riêng cho định hướng KHMT. **Câu 5 & Câu 6** dành riêng cho định hướng THUD.
  - Tùy vào định hướng đăng ký trước khi làm bài, giao diện thi của thí sinh sẽ tự động lọc, chỉ hiển thị và cho phép làm các câu hỏi thuộc định hướng đã chọn (ví dụ: chọn THUD thì Câu 5, 6 sẽ tự động hiển thị và đánh số thứ tự thành Câu 3, 4 trên màn hình của thí sinh, các câu KHMT sẽ bị ẩn đi).
* **Thuật toán tính điểm Đúng/Sai chuẩn quy định**:
  Tính điểm lũy tiến cực kỳ chặt chẽ cho mỗi câu hỏi Đúng/Sai (tổng điểm tối đa Phần II là 4.0 điểm):
  - Trả lời đúng **1 mệnh đề** trong câu: Được **0.1 điểm**.
  - Trả lời đúng **2 mệnh đề** trong câu: Được **0.25 điểm**.
  - Trả lời đúng **3 mệnh đề** trong câu: Được **0.5 điểm**.
  - Trả lời đúng **4 mệnh đề** (toàn bộ câu): Được **1.0 điểm**.

### 3. Tích hợp Kỳ thi Themis (Themis Contests)
* Cung cấp các công cụ CLI và tính năng trên web cho phép giáo viên quản lý kỳ thi theo định dạng phần mềm chấm thi offline **Themis** quen thuộc tại Việt Nam.
* Hỗ trợ thí sinh nộp bài dưới dạng tệp nén `.zip` chứa cấu trúc thư mục bài làm, hệ thống sẽ tự giải nén và phân phối chấm điểm tự động.

### 4. Hỗ trợ Đọc Ghi File (File Input/Output)
* Cho phép cấu hình các bài tập yêu cầu đọc/ghi dữ liệu từ tệp tin chỉ định (ví dụ: `input.txt` / `output.txt`) thay vì đọc/ghi qua console tiêu chuẩn (`stdin` / `stdout`).
* Hiển thị cảnh báo rõ ràng trên trang nộp bài để hướng dẫn thí sinh đặt tên file chính xác theo yêu cầu đề bài.

### 5. Tự cấp phát tài nguyên (Zero 3rd-party CDN / Hoạt động Ngoại tuyến)
* Toàn bộ các thư viện giao diện lớn (như jQuery, FontAwesome, Select2, Ace Editor, MathJax) và phông chữ Inter đều được đóng gói và phục vụ trực tiếp từ máy chủ lưu trữ cục bộ.
* Giúp hệ thống hoạt động ổn định, mượt mà và an toàn trong môi trường mạng nội bộ (mạng LAN) hoặc nơi không có kết nối Internet bên ngoài (gần như hoàn toàn offline).

---

## Tính năng Cốt lõi của Hệ thống

* **Đa ngôn ngữ lập trình**: Hỗ trợ chấm điểm cho hơn 60 ngôn ngữ và trình biên dịch khác nhau.
* **Trình chấm (Judge Server) mạnh mẽ**:
  - Chạy tách biệt trên sandbox bảo mật cao.
  - Hỗ trợ chấm bài tương tác (Interactive) thông qua đường ống dẫn dữ liệu.
  - Hỗ trợ trình tạo testcase tự động (generator) bằng C++ trực tiếp trên server chấm và trình chấm tùy chỉnh (custom checker).
* **Quản lý kỳ thi đa dạng**:
  - Hỗ trợ thi theo format ICPC, IOI, AtCoder, ECOO.
  - Chế độ thi ảo (Virtual Participation) sau khi kỳ thi kết thúc.
  - Tích hợp phát hiện gian lận tự động qua **Stanford MOSS API**.
* **Đề bài hiển thị chuyên nghiệp**: Hỗ trợ soạn thảo Markdown trực quan, tích hợp MathJax hiển thị công thức Toán học LaTeX và sơ đồ động. Tự động xuất đề bài thành file PDF.

---

<a id="english"></a>
# English

A modern open-source online judge and contest platform system based on DMOJ. FPTOJ has been tailored to support general and higher education environments, especially in Vietnam.

See it live at [fptoj.com](https://fptoj.com/)!

## Custom & Extended Features (FPTOJ)

* **Flexible Site Configuration**:
  - Live upload for logo and favicon with automatic Pillow-based optimization (resizing logos to max `600x150`, favicons to max `128x128`, auto-converting to PNG, and stripping metadata).
  - Custom logo styling (inline CSS configurations) and global custom CSS/JS insertion directly from the Admin dashboard.
  - Customizable footer text with toggleable default footer override.
* **National Graduation Exam & Quiz System**:
  - Graduation Exam format: **Part I** (24 multiple choice questions, 4 options, 1 correct) and **Part II** (True/False question clusters with candidate orientation filtering: Common questions, Computer Science / KHMT, and Applied IT / THUD direction).
  - Dynamic score calculations matching the national standard grading guidelines.
* **Themis Contest Integration**:
  - Built-in support for uploading ZIP files for contests.
  - Fully compatible with the Themis grading framework.
* **File Input/Output Support**:
  - Explicit File I/O checking and matching based on the problem statement requirements.
* **Zero Third-Party CDN (Almost Offline)**:
  - Crucial frontend dependencies (jQuery, FontAwesome, Select2, Ace Editor, MathJax, and Inter fonts) are completely bundled locally and served from static files.
  - Allows the platform to function seamlessly in offline environments or internal LAN networks without external internet access.

## Core Features

* Highly robust judging system:
   * Supports **interactive** and **signature-graded** tasks
   * Supports **runtime data generators** and **custom output validators**
   * Specifying **per-language resource limits**
   * Capable of scaling to hundreds of judging servers
* Extremely configurable contest system:
   * Supports ICPC/IOI/AtCoder/ECOO formats out-of-the-box
   * **System testing** supported
   * **Hidden scoreboards** and **virtual participation**
   * Elo-MMR-style rating
   * Plagiarism detection via Stanford MOSS
* Rich problem statements, with support for **LaTeX math and diagrams**
   * Automatic **PDF generation** for easy distribution
   * Built-in support for **editorials**
* Fine-grained permission control for staff
* OAuth login with Google, Facebook, and Github
* Two-factor authentication support

---

## Installation / Cài đặt

Check out the install documentation at / Xem tài liệu hướng dẫn cài đặt chi tiết tại [docs.dmoj.ca](https://docs.dmoj.ca/#/site/installation).

---

## Supported Languages / Ngôn ngữ được hỗ trợ

Check out [**DMOJ/judge-server**](https://github.com/DMOJ/judge-server) for more details. / Xem chi tiết máy chấm tại [**DMOJ/judge-server**](https://github.com/DMOJ/judge-server).

* C++ 11/14/17/20 (GCC and Clang)
* C 99/11
* Java 8-22
* Python 2/3
* PyPy 2/3
* Pascal
* Mono C#/F#/VB
* Go, Rust, Swift, Kotlin, JavaScript (V8), PHP, Lua, Haskell, Dart, D, Forth, Fortran, and many others.
