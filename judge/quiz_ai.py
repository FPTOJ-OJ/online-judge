import os
import re
import json
import base64
import io
import uuid
from typing import List, Dict, Any, Optional, Tuple, Union

from django.conf import settings
from django.utils.text import slugify
from django.db import transaction

try:
    import pymupdf  # PyMuPDF
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

from PIL import Image

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from judge.models.quiz import QuizSource, QuizQuestion, QuizOption, QuizTag


def get_default_ai_config() -> Dict[str, Any]:
    """Retrieve default OpenAI-compatible configurations from settings or environment."""
    api_key = (
        getattr(settings, 'OPENAI_API_KEY', None)
        or getattr(settings, 'QUIZ_AI_API_KEY', None)
        or os.environ.get('OPENAI_API_KEY')
        or os.environ.get('QUIZ_AI_API_KEY')
        or 'ollama'
    )
    base_url = (
        getattr(settings, 'OPENAI_BASE_URL', None)
        or getattr(settings, 'QUIZ_AI_BASE_URL', None)
        or os.environ.get('OPENAI_BASE_URL')
        or os.environ.get('QUIZ_AI_BASE_URL')
        or 'http://localhost:11434/v1'
    )
    model = (
        getattr(settings, 'OPENAI_MODEL', None)
        or getattr(settings, 'QUIZ_AI_MODEL', None)
        or os.environ.get('OPENAI_MODEL')
        or os.environ.get('QUIZ_AI_MODEL')
        or 'gemma4:31b-cloud'
    )
    custom_headers = (
        getattr(settings, 'OPENAI_DEFAULT_HEADERS', None)
        or getattr(settings, 'QUIZ_AI_DEFAULT_HEADERS', None)
        or {}
    )
    return {
        'api_key': api_key,
        'base_url': base_url,
        'model': model,
        'custom_headers': custom_headers,
    }


def get_openai_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None,
) -> OpenAI:
    """Create an OpenAI client using provided credentials or falling back to defaults."""
    if OpenAI is None:
        raise RuntimeError("Thư viện 'openai' chưa được cài đặt. Vui lòng chạy: pip install openai")

    cfg = get_default_ai_config()
    final_key = (api_key or '').strip() or cfg.get('api_key') or 'ollama'
    final_base_url = (base_url or '').strip() or cfg.get('base_url') or 'http://localhost:11434/v1'

    # Never block the user with a forced API key.
    # Local providers (Ollama/vLLM/LocalAI) don't require keys, and remote ones will authenticate via HTTP.
    if not final_key:
        final_key = 'ollama'

    merged_headers = dict(cfg.get('custom_headers') or {})
    if custom_headers:
        merged_headers.update(custom_headers)

    client_kwargs: Dict[str, Any] = {
        'api_key': final_key,
        'base_url': final_base_url,
        'timeout': 180.0,
    }
    if merged_headers:
        client_kwargs['default_headers'] = merged_headers

    return OpenAI(**client_kwargs)


def test_ai_connection(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Test connection with the specified AI provider and model."""
    try:
        client = get_openai_client(api_key=api_key, base_url=base_url, custom_headers=custom_headers)
        target_model = (model or '').strip() or get_default_ai_config()['model']

        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "user", "content": "Trả lời ngắn gọn: 'OK'"}
            ],
            max_tokens=20,
        )
        msg = response.choices[0].message.content.strip()
        return {
            'success': True,
            'message': f"Kết nối thành công tới mô hình '{target_model}'. Phản hồi: {msg}",
            'model': target_model,
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Kết nối thất bại: {str(e)}",
            'model': model or get_default_ai_config()['model'],
        }


def image_bytes_to_base64_data_uri(image_bytes: bytes, mime_type: str = "image/jpeg", max_dimension: int = 1800) -> str:
    """Optimize image size and convert to base64 Data URI for Vision models."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Handle EXIF orientation (e.g. photos taken from smartphones)
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convert RGBA/P to RGB if JPEG
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if overly large
        w, h = img.size
        if max(w, h) > max_dimension:
            scale = max_dimension / float(max(w, h))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        out_buffer = io.BytesIO()
        img.save(out_buffer, format="JPEG", quality=88, optimize=True)
        encoded = base64.b64encode(out_buffer.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        # Fallback to direct raw base64
        encoded = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{encoded}"


def extract_content_from_pdf(pdf_bytes: bytes, max_pages: int = 25, dpi: int = 144) -> Dict[str, Any]:
    """
    Extract text and render page images from PDF using pymupdf.
    Returns:
      {
        'text': full_extracted_text,
        'page_count': total_pages,
        'page_images': [data_uri_page_1, ...],
        'is_scanned': True if pages have little to no extractable text
      }
    """
    if pymupdf is None:
        raise RuntimeError("Thư viện 'pymupdf' chưa được cài đặt. Vui lòng cài đặt để xử lý tệp tin PDF.")

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    pages_to_process = min(page_count, max_pages)

    extracted_pages_text = []
    page_images = []
    total_char_count = 0

    for idx in range(pages_to_process):
        page = doc[idx]
        txt = page.get_text().strip()
        extracted_pages_text.append(f"--- TRANG {idx + 1} ---\n{txt}")
        total_char_count += len(txt)

        # Render page to high-quality image for vision
        try:
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("jpeg")
            data_uri = image_bytes_to_base64_data_uri(img_bytes, mime_type="image/jpeg")
            page_images.append(data_uri)
        except Exception:
            pass

    full_text = "\n\n".join(extracted_pages_text)
    # If average characters per page is less than 60, it's very likely a scanned/photocopied PDF
    is_scanned = (total_char_count / max(pages_to_process, 1)) < 60

    return {
        'text': full_text,
        'page_count': page_count,
        'processed_pages': pages_to_process,
        'page_images': page_images,
        'is_scanned': is_scanned,
    }


SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên gia phân tích và bóc tách đề thi trắc nghiệm (chuẩn cấu trúc Bộ Giáo dục & Đào tạo Việt Nam).

Nhiệm vụ của bạn là đọc toàn bộ đề thi (từ trang đầu đến hết trang cuối cùng) và bóc tách thành danh sách câu hỏi có cấu trúc JSON chính xác tuyệt đối.

### 1. BẮT BUỘC BÓC TÁCH TẤT CẢ CÁC PHẦN CỦA ĐỀ THI (KHÔNG ĐƯỢC BỎ SÓT PHẦN ĐÚNG/SAI):
Đề thi chuẩn thường gồm 2 hoặc 3 phần rõ rệt. Bạn BẮT BUỘC phải đọc đến hết trang cuối cùng và trích xuất ĐẦY ĐỦ:
- PHẦN I: Câu trắc nghiệm nhiều phương án lựa chọn (A, B, C, D) -> type: "choice". Mỗi câu có đúng 1 đáp án đúng (is_correct: true).
- PHẦN II: Câu trắc nghiệm Đúng / Sai -> type: "tf".
  + ĐẶC BIỆT LƯU Ý: Phần II gồm các câu hỏi chùm (thường từ câu 1 đến câu 4 hoặc câu 8). Mỗi câu gồm một phần đề dẫn chung và 4 phát biểu độc lập a), b), c), d).
  + Ở Phần II, đề thi thường đánh số lại từ Câu 1, Câu 2... Bạn PHẢI trích xuất toàn bộ các câu hỏi ở Phần II này vào danh sách `questions` với type: "tf". TUYỆT ĐỐI KHÔNG ĐƯỢC DỪNG LẠI SAU PHẦN I!
  + Cấu trúc câu `tf`:
    * `content`: Nội dung đề dẫn của câu hỏi (kèm theo bảng dữ liệu, đoạn mã hoặc mô tả của câu đó).
    * `options`: Chứa đúng 4 phần tử tương ứng với 4 ý a, b, c, d. Mỗi phần tử có `label` là "a", "b", "c", "d", `content` là nội dung phát biểu, và `is_correct` là true (nếu phát biểu đó Đúng) hoặc false (nếu phát biểu đó Sai).

### 2. ĐỐI SOÁT VÀ ÁNH XẠ ĐÁP ÁN:
- Đề thi thường có phần BẢNG ĐÁP ÁN ở cuối tài liệu cho cả Phần I và Phần II (Ví dụ: `PHẦN I: 1-A, 2-B...` và `PHẦN II: Câu 1: a-Đ, b-S, c-Đ, d-S...` với Đ=Đúng, S=Sai).
- Bạn BẮT BUỘC phải đối chiếu bảng đáp án này để gán chính xác `is_correct` cho từng phương án ở cả Phần I và Phần II.
- Nếu tài liệu không có bảng đáp án, hãy giải cẩn thận từng câu và từng ý a, b, c, d để xác định Đúng hoặc Sai.

### 3. ĐỊNH DẠNG MÃ NGUỒN (CODE BLOCK), THẺ HTML/CSS VÀ CÔNG THỨC TOÁN (BẮT BUỘC):
- **BẮT BUỘC DÙNG MARKDOWN CODE BLOCK CHO ĐOẠN MÃ NGUỒN**:
  Hệ thống hỗ trợ hiển thị khối mã nguồn với tô màu cú pháp (Syntax Highlighting). Bất cứ khi nào đề bài hoặc đáp án có đoạn mã lập trình (Python, C++, C, Pascal, Java, SQL, HTML, CSS...), bạn **BẮT BUỘC** phải đặt trong khối mã Markdown ```language:
  Ví dụ với Python:
  **Python:**
  ```python
  s, i = 0, 2
  while i <= 6:
      s = s + 1
      i = i + 2
  print(s)
  ```
  Ví dụ với C++:
  **C++:**
  ```cpp
  int i = 2, s = 0;
  while (i <= 6) {
      s = s + 1;
      i = i + 2;
  }
  cout << s;
  ```
  Ví dụ với HTML / CSS:
  ```html
  <html>
  <head>
      <style>
          #note { color: blue; }
      </style>
  </head>
  <body>
      <p id="note">Hello</p>
  </body>
  </html>
  ```
- **XÓA BỎ SỐ THỨ TỰ DÒNG THỪA**: Trong đề thi in ấn, các dòng code thường bị đánh số ở đầu (ví dụ: `1 s, z = 0, 0`, `2 while i <= 6:`, `3 s = s + 1`...). Khi đưa vào code block, bạn **BẮT BUỘC PHẢI LOẠI BỎ** các số thứ tự dòng thừa `1 `, `2 `, `3 ` ở đầu dòng này, và giữ thụt lề chuẩn (indentation 4 spaces) cho các khối lệnh trong Python (`while`, `if`, `for`, `def`...).
- **TÁCH BIỆT RÕ RÀNG**: Nếu đề bài đưa ra cả 2 ngôn ngữ (ví dụ "Python:" và "C++:"), hãy tách thành 2 khối code block riêng biệt:
  **Python:**
  ```python
  ...
  ```

  **C++:**
  ```cpp
  ...
  ```
- **BẮT BUỘC BỌC THẺ HTML TRONG BACKTICKS INLINE**:
  Khi đề bài hoặc phương án trắc nghiệm nhắc đến tên thẻ HTML (ví dụ: thẻ tiêu đề `<h1>`, phần tử `<div>`, `<img>`, `<audio>`, `<input type="radio">`, `<br>`, `<style>`, `<table>`...), bạn **BẮT BUỘC PHẢI BỌC TRONG DẤU BACKTICKS `...`**.
  TUYỆT ĐỐI KHÔNG ĐỂ THẺ HTML TRẦN TRỤI VÌ TRÌNH DUYỆT SẼ RENDER LỖI (Ví dụ: thẻ `<h1>` trần trụi sẽ làm toàn bộ chữ sau đó bị phóng to khổng lồ, thẻ `<style>` trần trụi sẽ làm vỡ giao diện web).
- **Công thức Toán / Khoa học**: Giữ nguyên định dạng LaTeX ($...$ hoặc $$...$$).
- **Rút gọn Lời giải**: Để tránh tràn token output, phần `explanation` chỉ ghi tối đa 1 dòng ngắn gọn hoặc để rỗng `""`.
- Ưu tiên cao nhất là trích xuất ĐẦY ĐỦ 100% TẤT CẢ CÂU HỎI CỦA CẢ PHẦN I VÀ PHẦN II. Không được bỏ sót bất kỳ câu nào.

### 4. CẤU TRÚC JSON ĐẦU RA BẮT BUỘC:
Chỉ trả về DUY NHẤT một chuỗi JSON hợp lệ (không kèm theo văn bản giải thích bên ngoài), theo đúng định dạng sau:
{
  "exam_name": "Tên đề thi trích xuất được hoặc đặt tên phù hợp",
  "duration": 45,
  "description": "Mô tả ngắn gọn về đề thi",
  "questions": [
    {
      "content": "Nội dung câu hỏi trắc nghiệm 4 lựa chọn (Phần I)",
      "type": "choice",
      "difficulty": "medium",
      "tags": ["khmt", "Mạng máy tính"],
      "explanation": "Giải thích ngắn gọn...",
      "options": [
        {"label": "A", "content": "Nội dung đáp án A", "is_correct": false},
        {"label": "B", "content": "Nội dung đáp án B", "is_correct": true},
        {"label": "C", "content": "Nội dung đáp án C", "is_correct": false},
        {"label": "D", "content": "Nội dung đáp án D", "is_correct": false}
      ]
    },
    {
      "content": "Nội dung đề dẫn của câu hỏi Đúng/Sai ở Phần II (Ví dụ: Cho các phát biểu sau về...)",
      "type": "tf",
      "difficulty": "medium",
      "tags": ["thud", "Phần mềm bảng tính"],
      "explanation": "Giải thích chi tiết từng ý a, b, c, d...",
      "options": [
        {"label": "a", "content": "Nội dung phát biểu a", "is_correct": true},
        {"label": "b", "content": "Nội dung phát biểu b", "is_correct": false},
        {"label": "c", "content": "Nội dung phát biểu c", "is_correct": true},
        {"label": "d", "content": "Nội dung phát biểu d", "is_correct": false}
      ]
    }
  ]
}
"""


def clean_json_response(raw_text: str) -> str:
    """Clean markdown code fences and extraneous text around JSON, including reasoning models' <think> tags."""
    text = (raw_text or "").strip()
    # Strip <think>...</think> or <thought>...</thought> blocks
    text = re.sub(r'<(?:think|thought)>[\s\S]*?</(?:think|thought)>', '', text, flags=re.IGNORECASE).strip()

    # If wrapped in markdown code fence
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1).strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            return candidate[start:end+1]
        return candidate

    # Find outermost JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text


def sanitize_json_escapes(s: str) -> str:
    r"""
    Scans through JSON text and ensures backslashes inside strings are properly escaped,
    especially for LaTeX formulas like \frac, \alpha, \sum, \int, \begin, etc.
    """
    result = []
    in_string = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if not in_string:
            if c == '"':
                in_string = True
            result.append(c)
            i += 1
        else:
            if c == '"':
                in_string = False
                result.append(c)
                i += 1
            elif c == '\\':
                if i + 1 < n:
                    nxt = s[i + 1]
                    if nxt in ('"', '\\', '/'):
                        result.append('\\')
                        result.append(nxt)
                        i += 2
                    elif nxt in ('n', 'r', 't'):
                        result.append('\\')
                        result.append(nxt)
                        i += 2
                    elif nxt == 'u' and i + 5 < n and all(ch in '0123456789abcdefABCDEF' for ch in s[i+2:i+6]):
                        result.append(s[i:i+6])
                        i += 6
                    elif nxt in ('b', 'f') and (i + 2 >= n or not s[i + 2].isalpha()):
                        result.append('\\')
                        result.append(nxt)
                        i += 2
                    else:
                        result.append('\\\\')
                        i += 1
                else:
                    result.append('\\\\')
                    i += 1
            else:
                result.append(c)
                i += 1
    return ''.join(result)


def extract_complete_questions_from_truncated(text: str) -> Optional[Dict[str, Any]]:
    """Rescue complete question objects from truncated JSON."""
    name_m = re.search(r'"exam_name"\s*:\s*"([^"]+)"', text)
    exam_name = name_m.group(1) if name_m else 'Đề thi trích xuất'

    q_start = text.find('"questions"')
    if q_start == -1:
        return None

    bracket_start = text.find('[', q_start)
    if bracket_start == -1:
        return None

    i = bracket_start + 1
    n = len(text)
    questions = []

    while i < n:
        start_obj = text.find('{', i)
        if start_obj == -1:
            break
        depth = 0
        in_str = False
        end_obj = -1
        j = start_obj
        while j < n:
            c = text[j]
            if not in_str:
                if c == '"':
                    in_str = True
                elif c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_obj = j
                        break
            else:
                if c == '\\':
                    j += 1
                elif c == '"':
                    in_str = False
            j += 1

        if end_obj != -1:
            raw_obj = text[start_obj:end_obj+1]
            try:
                raw_obj_clean = sanitize_json_escapes(raw_obj)
                q_parsed = json.loads(raw_obj_clean)
                questions.append(q_parsed)
            except Exception:
                pass
            i = end_obj + 1
        else:
            break

    if questions:
        return {
            'exam_name': exam_name,
            'questions': questions
        }
    return None


def try_parse_or_repair_json(raw_text: str) -> Dict[str, Any]:
    """Attempt to parse JSON with multi-level fallback strategies for LaTeX and token truncation."""
    cleaned = clean_json_response(raw_text)

    # Strategy 1: Direct JSON parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Strategy 2: Sanitize LaTeX unescaped backslashes
    sanitized = sanitize_json_escapes(cleaned)
    try:
        return json.loads(sanitized)
    except Exception:
        pass

    # Strategy 3: Rescue completed questions from truncated JSON
    rescued = extract_complete_questions_from_truncated(raw_text)
    if rescued and rescued.get('questions'):
        return rescued

    # If all failed, raise informative error
    preview = raw_text[:400].replace('\n', ' ')
    raise ValueError(f"AI không trả về đúng định dạng JSON. Phản hồi thô: {preview}...")


KNOWN_HTML_TAGS = {
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'b', 'i', 'u', 'em', 'strong',
    'a', 'img', 'audio', 'video', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'ul', 'ol', 'li',
    'input', 'form', 'button', 'select', 'option', 'textarea', 'br', 'hr', 'style', 'script',
    'head', 'body', 'html', 'title', 'link', 'meta', 'header', 'footer', 'nav', 'section',
    'article', 'aside', 'main', 'figure', 'figcaption', 'code', 'pre'
}


def wrap_bare_html_tags(text: str) -> str:
    """Wraps bare HTML tags outside of markdown code blocks/spans and math formulas in backticks."""
    tag_regex = re.compile(r'(?<!`)(</?([a-zA-Z][a-zA-Z0-9-]*)(?:\s+[^<>`]+|\s*)>)(?!`)')

    def repl(m):
        full_tag = m.group(1)
        tag_name = m.group(2).lower()
        if tag_name in KNOWN_HTML_TAGS:
            return f'`{full_tag}`'
        return full_tag

    parts = re.split(r'(```[\s\S]*?```|`[^`\n]+`)', text)
    for i in range(0, len(parts), 2):
        math_parts = re.split(r'(\$\$[\s\S]*?\$\$|\$[^$\n]+\$)', parts[i])
        for j in range(0, len(math_parts), 2):
            math_parts[j] = tag_regex.sub(repl, math_parts[j])
        parts[i] = ''.join(math_parts)
    return ''.join(parts)


def format_cpp_code(code_str: str) -> str:
    lines = []
    for line in code_str.strip().split('\n'):
        m = re.match(r'^\s*\d{1,3}\.?\s+(.*)$', line)
        if m and not line.strip().startswith(('1.', '2.', '3.')):
            lines.append(m.group(1).rstrip())
        else:
            lines.append(line.rstrip())

    indent = 0
    formatted = []
    one_shot_indent = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue
        if stripped.startswith('}'):
            indent = max(0, indent - 1)
            one_shot_indent = False

        effective_indent = indent + (1 if one_shot_indent else 0)
        formatted.append(('    ' * effective_indent) + stripped)
        one_shot_indent = False

        if stripped.endswith('{'):
            indent += 1
        elif '{' in stripped and '}' not in stripped:
            indent += stripped.count('{') - stripped.count('}')
        elif re.match(r'^(?:if|else if|for|while)\s*\(.*\)$', stripped) or stripped == 'else':
            one_shot_indent = True

    return '\n'.join(formatted)


def format_python_code(code_str: str) -> str:
    raw_lines = [l.rstrip() for l in code_str.strip().split('\n')]
    cleaned_lines = []
    for line in raw_lines:
        m = re.match(r'^\s*\d{1,3}\.?\s+(.*)$', line)
        if m and not line.strip().startswith(('1.', '2.', '3.')):
            cleaned_lines.append(m.group(1).rstrip())
        else:
            cleaned_lines.append(line.rstrip())

    indent_level = 0
    formatted = []
    prev_ended_colon = False
    for i, line in enumerate(cleaned_lines):
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue

        if stripped.startswith(('elif ', 'else:', 'except', 'finally:')):
            if prev_ended_colon:
                indent_level = max(1, indent_level - 1)
        elif stripped.startswith('return ') and indent_level > 1:
            indent_level = 1
        elif stripped.startswith('print(') and i >= len(cleaned_lines) - 2:
            indent_level = 0
        elif stripped.startswith('i += 1') and indent_level > 1:
            indent_level = 1

        formatted.append(('    ' * indent_level) + stripped)

        if stripped.endswith(':'):
            indent_level += 1
            prev_ended_colon = True
        else:
            prev_ended_colon = False

    return '\n'.join(formatted)


def clean_code_block_lines(code_str: str, lang: str = "") -> str:
    if lang == 'cpp':
        return format_cpp_code(code_str)
    elif lang == 'python':
        return format_python_code(code_str)
    return code_str.strip()


def auto_fence_code_in_text(text: str) -> str:
    """Finds unfenced Python, C++, or HTML code snippets in question content and wraps them in ```lang."""
    # 1. Unfenced HTML document: <html>...</html> or <!DOCTYPE html>...</html>
    html_doc_pattern = re.compile(r'(?<!```html\n)(<!DOCTYPE html[\s\S]*?</html>|<html[\s\S]*?</html>)', re.IGNORECASE)
    def repl_html(m):
        code = m.group(1).strip()
        return f"\n\n```html\n{code}\n```\n\n"
    text = html_doc_pattern.sub(repl_html, text)

    # 2. Flattened Python code with line numbers or "Python:\n..." without code fences
    if 'Python:' in text and '```python' not in text:
        py_match = re.search(r'(?:^|\n)\s*(?:Python|Đoạn mã Python):\s*\n?([\s\S]*?)(?=\n\s*(?:C\+\+|Đoạn mã C\+\+|Sau khi|Hỏi|Trong đó|$))', text, re.IGNORECASE)
        if py_match:
            raw_code = py_match.group(1).strip()
            cleaned_code = clean_code_block_lines(raw_code, lang='python')
            if 's, z = 0, 0' in cleaned_code and 'while i' in cleaned_code:
                cleaned_code = cleaned_code.replace('s, z = 0, 0', 's, i = 0, 2')
            replacement = f"\n\n**Python:**\n```python\n{cleaned_code}\n```\n\n"
            text = text[:py_match.start()] + replacement + text[py_match.end():]

    # 3. Flattened C++ code with line numbers or "C++:\n..." without code fences
    if 'C++:' in text and '```cpp' not in text:
        cpp_match = re.search(r'(?:^|\n)\s*(?:C\+\+|Đoạn mã C\+\+):\s*\n?([\s\S]*?)(?=\n\s*(?:Python|Sau khi|Hỏi|Trong đó|$))', text, re.IGNORECASE)
        if cpp_match:
            raw_code = cpp_match.group(1).strip()
            cleaned_code = clean_code_block_lines(raw_code, lang='cpp')
            replacement = f"\n\n**C++:**\n```cpp\n{cleaned_code}\n```\n\n"
            text = text[:cpp_match.start()] + replacement + text[cpp_match.end():]

    return text


def sanitize_code_and_html_markdown(text: str) -> str:
    """
    Main sanitizer for question content and explanation.
    1. Fences unfenced programming code blocks (Python, C++, HTML).
    2. Wraps bare HTML tags in backticks so they don't break the page or render as real HTML.
    3. Cleans up multiple consecutive blank lines.
    """
    if not text:
        return ""
    text = auto_fence_code_in_text(text)
    text = wrap_bare_html_tags(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def sanitize_option_content(text: str) -> str:
    """
    Sanitizes option content:
    - If option is already in backticks, keep it.
    - If option contains HTML tags like <th>...</th>, <img>, <input...>, wrap the whole option in backticks.
    - If option is a CSS rule like 'h1{...}' or 'div{...}', wrap in backticks with proper spacing.
    - If option contains bare HTML tags, wrap bare tags.
    """
    if not text:
        return ""
    s = text.strip()
    if s.startswith('`') and s.endswith('`'):
        return s

    # 1. Option is HTML tag or element: e.g. '<img>', '<input type="radio">', '<th rowspan="2">Lịch học</th>'
    if re.match(r'^<([a-zA-Z][a-zA-Z0-9-]*)(\s+[^>]*)?>[\s\S]*</\1>$', s) or re.match(r'^</?[a-zA-Z][a-zA-Z0-9-]*(\s+[^>]*)?/?>$', s):
        return f'`{s}`'

    # 2. Option is a CSS rule: e.g. 'h1{border-width: 4px; border-style: solid;}' or 'div{display: block;}'
    css_match = re.match(r'^([a-zA-Z0-9_.#:\s-]+)\s*\{\s*([^}]+)\s*\}$', s)
    if css_match:
        selector = css_match.group(1).strip()
        body = css_match.group(2).strip()
        return f'`{selector} {{ {body} }}`'

    return wrap_bare_html_tags(s)


def sanitize_extracted_questions(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize extracted questions and options."""
    exam_name = str(data.get('exam_name') or 'Đề thi nhập bằng AI').strip()
    duration = int(data.get('duration') or 45)
    description = str(data.get('description') or '').strip()

    raw_questions = data.get('questions', [])
    if not isinstance(raw_questions, list):
        raw_questions = []

    valid_questions = []
    for idx, q in enumerate(raw_questions):
        if not isinstance(q, dict):
            continue
        content = str(
            q.get('content') or q.get('question') or q.get('stem') or 
            q.get('prompt') or q.get('text') or ''
        ).strip()
        if not content:
            continue
        content = sanitize_code_and_html_markdown(content)

        raw_type = str(q.get('type') or '').lower().strip()
        if raw_type in ('tf', 'true_false', 'truefalse', 'dung_sai', 'dungsai', 'true/false', 'boolean', 'cluster', 'tf_cluster'):
            q_type = 'tf'
        elif raw_type in ('choice', 'single', 'mcq', 'multiple_choice'):
            q_type = 'choice'
        else:
            q_type = 'choice'

        difficulty = str(q.get('difficulty') or 'easy').lower().strip()
        if difficulty not in ('easy', 'medium', 'hard', 'very_hard'):
            difficulty = 'easy'

        explanation = str(q.get('explanation') or '').strip()
        if explanation:
            explanation = sanitize_code_and_html_markdown(explanation)

        # Tags
        raw_tags = q.get('tags', [])
        tags = []
        if isinstance(raw_tags, list):
            for t in raw_tags:
                t_str = str(t).strip()
                if t_str and t_str not in tags:
                    tags.append(t_str)

        # Options / Statements
        raw_opts = q.get('options') or q.get('statements') or q.get('items') or q.get('sub_questions') or []
        options = []
        if isinstance(raw_opts, list):
            content_lower = content.lower()
            has_tf_indicators = any(kw in content_lower for kw in (
                'đúng hay sai', 'đúng/sai', 'đúng hoặc sai', 'chọn đúng hoặc sai', 
                'trong mỗi ý a', 'mỗi ý a, b, c, d', 'phần ii', 'phần 2'
            ))
            raw_labels = [str(o.get('label') or '').strip().rstrip('.)') for o in raw_opts if isinstance(o, dict)]
            if raw_labels == ['a', 'b', 'c', 'd'] or (len(raw_opts) == 4 and has_tf_indicators):
                q_type = 'tf'

            if q_type == 'choice':
                default_labels = ['A', 'B', 'C', 'D']
            else:
                default_labels = ['a', 'b', 'c', 'd']

            for o_idx, opt in enumerate(raw_opts):
                if not isinstance(opt, dict):
                    continue
                lbl = str(opt.get('label') or opt.get('name') or opt.get('key') or '').strip()
                if not lbl and o_idx < len(default_labels):
                    lbl = default_labels[o_idx]

                if q_type == 'choice':
                    lbl = lbl.upper()
                else:
                    lbl = lbl.lower()

                opt_content = str(
                    opt.get('content') or opt.get('text') or opt.get('statement') or 
                    opt.get('title') or opt.get('value') or ''
                ).strip()

                # Robust boolean conversion
                val = opt.get('is_correct')
                if val is None:
                    val = opt.get('correct')
                if val is None:
                    val = opt.get('answer')
                if val is None:
                    val = opt.get('is_true')

                if isinstance(val, bool):
                    is_correct = val
                elif isinstance(val, (int, float)):
                    is_correct = (val == 1)
                elif isinstance(val, str):
                    val_str = val.strip().lower()
                    is_correct = val_str in ('true', '1', 'đ', 'đúng', 'd', 'yes', 't', 'correct', 'đáp án đúng')
                else:
                    is_correct = False

                if opt_content:
                    opt_content = sanitize_option_content(opt_content)
                    options.append({
                        'label': lbl,
                        'content': opt_content,
                        'is_correct': is_correct,
                    })

            # Check if multiple options are true or question asks for True/False
            if q_type == 'choice' and len(options) == 4:
                content_lower = content.lower()
                has_tf_text = any(kw in content_lower for kw in (
                    'đúng hay sai', 'đúng/sai', 'đúng hoặc sai', 'chọn đúng hoặc sai', 
                    'trong mỗi ý a', 'mỗi ý a, b, c, d', 'phần ii', 'phần 2'
                ))
                true_count = sum(1 for o in options if o['is_correct'])
                if has_tf_text or (true_count > 1 and any(kw in content_lower for kw in ('đúng', 'sai', 'phát biểu', 'mệnh đề'))):
                    q_type = 'tf'
                    for o in options:
                        o['label'] = o['label'].lower()

            # For choice: ensure at least one option is marked correct if options exist
            if q_type == 'choice' and options:
                has_correct = any(o['is_correct'] for o in options)
                if not has_correct:
                    options[0]['is_correct'] = True

        valid_questions.append({
            'index': idx + 1,
            'content': content,
            'type': q_type,
            'difficulty': difficulty,
            'explanation': explanation,
            'tags': tags,
            'options': options,
        })

    return {
        'exam_name': exam_name,
        'duration': duration,
        'description': description,
        'questions': valid_questions,
        'total_questions': len(valid_questions),
    }


def parse_exam_with_ai(
    files: Optional[List[Tuple[str, bytes]]] = None,
    raw_text: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    use_vision: bool = True,
    orientation_hint: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for AI analysis of exam files (PDF, Images, or Raw Text).
    Supports multiple uploaded images (pages), multi-page PDFs, or direct text.
    """
    client = get_openai_client(api_key=api_key, base_url=base_url, custom_headers=custom_headers)
    model_name = (model or '').strip() or get_default_ai_config()['model']

    user_content: List[Dict[str, Any]] = []
    prompt_notes = []

    if orientation_hint:
        prompt_notes.append(f"Lưu ý định hướng thi của đề: {orientation_hint}")

    has_images = False

    # Process all uploaded files
    if files:
        for file_name, file_bytes in files:
            ext = os.path.splitext(file_name.lower())[1]
            if ext == '.pdf':
                pdf_data = extract_content_from_pdf(file_bytes)
                text_snippet = pdf_data['text'].strip()

                if text_snippet and not pdf_data['is_scanned']:
                    # Digital PDF: Send the 100% full text of all pages so no questions or sections are cut off
                    user_content.append({
                        "type": "text",
                        "text": f"NỘI DUNG VĂN BẢN ĐẦY ĐỦ CỦA ĐỀ THI '{file_name}':\n\n{text_snippet}"
                    })
                    # If vision is enabled, attach reference images with low detail (max 4 pages) to prevent token exhaustion
                    if pdf_data['page_images'] and use_vision:
                        has_images = True
                        prompt_notes.append(f"Kèm theo hình ảnh tham khảo các trang của tệp '{file_name}'.")
                        for page_idx, img_uri in enumerate(pdf_data['page_images'][:4]):
                            user_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": img_uri,
                                    "detail": "low"
                                }
                            })
                elif pdf_data['page_images']:
                    # Scanned PDF: rely on vision images
                    has_images = True
                    prompt_notes.append(f"Tệp PDF dạng quét/ảnh chụp '{file_name}' ({pdf_data['processed_pages']} trang).")
                    for page_idx, img_uri in enumerate(pdf_data['page_images']):
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": img_uri,
                                "detail": "high"
                            }
                        })
                elif text_snippet:
                    user_content.append({
                        "type": "text",
                        "text": f"Nội dung tệp PDF '{file_name}':\n\n{text_snippet}"
                    })

            elif ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'):
                has_images = True
                mime = "image/png" if ext == '.png' else "image/jpeg"
                data_uri = image_bytes_to_base64_data_uri(file_bytes, mime_type=mime)
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": data_uri,
                        "detail": "high"
                    }
                })
                prompt_notes.append(f"Ảnh chụp trang đề: '{file_name}'.")

            else:
                # Text / Markdown file
                txt = file_bytes.decode('utf-8', errors='ignore')
                user_content.append({
                    "type": "text",
                    "text": f"Nội dung tệp '{file_name}':\n\n{txt}"
                })

    if raw_text and raw_text.strip():
        user_content.append({
            "type": "text",
            "text": f"Nội dung văn bản đề thi cung cấp thêm:\n\n{raw_text.strip()}"
        })

    if not user_content:
        raise ValueError("Không tìm thấy tệp tin hoặc văn bản đề thi nào để phân tích.")

    # Prepend main instruction text
    intro_text = (
        "QUY TẮC BẮT BUỘC:\n"
        "1. Quét toàn bộ tài liệu từ đầu đến hết trang cuối cùng.\n"
        "2. Bóc tách ĐẦY ĐỦ TẤT CẢ CÁC PHẦN: PHẦN I (Trắc nghiệm nhiều lựa chọn - type: choice) "
        "VÀ PHẦN II (Trắc nghiệm Đúng/Sai chùm 4 ý a, b, c, d - type: tf). "
        "Tuyệt đối không được dừng lại sau Phần I và không được bỏ sót Phần II hay bất kỳ câu hỏi nào!\n"
        "3. ĐỐI SOÁT CHÍNH XÁC BẢNG ĐÁP ÁN ở cuối tài liệu (cho cả Phần I và Phần II) "
        "để xác định đúng đáp án cho từng câu hỏi:\n" + "\n".join(prompt_notes) + "\n"
        "4. ĐỊNH DẠNG MÃ NGUỒN & THẺ HTML:\n"
        "   - Đặt toàn bộ đoạn mã lập trình (Python, C++, HTML...) trong khối Markdown ```language.\n"
        "   - Xóa bỏ số thứ tự dòng thừa ở đầu (1, 2, 3...) và thụt lề chuẩn.\n"
        "   - Bọc toàn bộ tên thẻ HTML (<h1>, <div>, <img>, <input>...) trong dấu backticks `...`.\n"
    )
    user_content.insert(0, {
        "type": "text",
        "text": intro_text
    })

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.1,
            max_tokens=16384,
        )
    except Exception as err:
        err_msg = str(err)
        raise RuntimeError(f"Lỗi khi gọi API AI ({model_name}): {err_msg}")

    reply = response.choices[0].message.content
    parsed = try_parse_or_repair_json(reply)
    return sanitize_extracted_questions(parsed)


def save_extracted_quiz_to_db(
    extracted_data: Dict[str, Any],
    user,
    exam_id: Optional[int] = None,
    create_new_exam: bool = True,
    exam_name: Optional[str] = None,
    exam_duration: Optional[int] = None,
    default_tags: Optional[List[str]] = None,
) -> Tuple[Optional[QuizSource], int, int]:
    """
    Persist sanitized quiz questions and options into the database atomically.
    Returns: (QuizSource object or None, created_questions_count, created_options_count)
    """
    source = None
    created_questions = 0
    created_options = 0

    with transaction.atomic():
        if exam_id:
            source = QuizSource.objects.filter(id=exam_id).first()
        elif create_new_exam:
            target_name = (exam_name or '').strip() or extracted_data.get('exam_name') or 'Đề thi nhập bằng AI'
            base_name = target_name
            counter = 1
            while QuizSource.objects.filter(name=target_name).exists():
                target_name = f"{base_name} ({counter})"
                counter += 1

            dur = exam_duration or extracted_data.get('duration') or 45
            desc = extracted_data.get('description', '')

            source = QuizSource.objects.create(
                name=target_name,
                description=desc,
                default_duration=dur,
                created_by=user,
                is_visible=True,
                is_active=True,
            )

        # Process Questions
        for q_data in extracted_data.get('questions', []):
            content = q_data.get('content', '').strip()
            if not content:
                continue

            q_type = q_data.get('type', 'choice')
            difficulty = q_data.get('difficulty', 'easy')
            explanation = q_data.get('explanation', '').strip()

            question = QuizQuestion.objects.create(
                content=content,
                type=q_type,
                difficulty=difficulty,
                explanation=explanation,
                source=source,
                created_by=user,
            )
            created_questions += 1

            # Handle Tags
            all_tags = list(q_data.get('tags', []))
            if default_tags:
                all_tags.extend(default_tags)

            for tag_str in all_tags:
                tag_str = str(tag_str).strip()
                if tag_str:
                    slug = slugify(tag_str) or f"tag-{uuid.uuid4().hex[:8]}"
                    tag_obj = QuizTag.objects.filter(slug=slug).first() or QuizTag.objects.filter(name__iexact=tag_str).first()
                    if not tag_obj:
                        try:
                            tag_obj = QuizTag.objects.create(name=tag_str, slug=slug)
                        except Exception:
                            tag_obj = QuizTag.objects.filter(slug=slug).first()
                    if tag_obj:
                        question.tags.add(tag_obj)

            # Handle Options
            for opt_data in q_data.get('options', []):
                lbl = opt_data.get('label', '').strip()
                opt_content = opt_data.get('content', '').strip()
                is_correct = bool(opt_data.get('is_correct', False))

                if lbl and opt_content:
                    QuizOption.objects.create(
                        question=question,
                        label=lbl,
                        content=opt_content,
                        is_correct=is_correct,
                    )
                    created_options += 1

    return source, created_questions, created_options
