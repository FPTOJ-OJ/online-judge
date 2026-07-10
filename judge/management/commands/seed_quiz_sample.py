from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils.text import slugify
from judge.models.quiz import QuizTag, QuizSource, QuizQuestion, QuizOption, QuizSession


class Command(BaseCommand):
    help = 'Seed sample quiz data with CS/IT orientation for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete all existing quiz/exam data before seeding',
        )

    def handle(self, *args, **options):
        force = options.get('force')

        if force:
            self.stdout.write(self.style.WARNING('Deleting all existing quiz data...'))
            QuizSession.objects.all().delete()
            QuizOption.objects.all().delete()
            QuizQuestion.objects.all().delete()
            QuizSource.objects.all().delete()
            QuizTag.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Deleted all existing quiz data.'))

        # Check if sample data already exists
        if QuizSource.objects.filter(name='[MẪU] Đề thi thử THPT 2026 - CS/IT').exists():
            self.stdout.write(self.style.WARNING('Sample exam already exists. Use --force to recreate.'))
            return

        # Create tags
        khmt_tag, _ = QuizTag.objects.get_or_create(name='KHMT', defaults={'slug': 'khmt'})
        thud_tag, _ = QuizTag.objects.get_or_create(name='THUD', defaults={'slug': 'thud'})
        self.stdout.write(self.style.SUCCESS(f'Tags created: {khmt_tag.name}, {thud_tag.name}'))

        # Create source/exam
        sample_exam, _ = QuizSource.objects.get_or_create(
            name='[MẪU] Đề thi thử THPT 2026 - CS/IT',
            defaults={
                'description': 'Đề thi mẫu dùng để test tính năng định hướng CS (Khoa học máy tính) và IT (Tin học ứng dụng). Chỉ admin mới thấy đề này.',
                'default_duration': 45,
                'is_visible': False,
                'is_featured': True,
                'require_login': True,
                'is_locked': False,
                'is_organization_only': False,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'Exam created: {sample_exam.name}'))

        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(is_staff=True).first()

        # Create sample questions
        questions_data = [
            {
                'content': 'Trong thuật toán tìm kiếm nhị phân (Binary Search), độ phức tạp thời gian trong trường hợp xấu nhất là:',
                'type': 'choice', 'difficulty': 'easy',
                'explanation': 'Tìm kiếm nhị phân có độ phức tạp O(log n) vì mỗi bước chia đôi không gian tìm kiếm.',
                'tags': [khmt_tag],
                'options': [
                    ('A', 'O(n)', False),
                    ('B', 'O(log n)', True),
                    ('C', 'O(n²)', False),
                    ('D', 'O(1)', False),
                ],
            },
            {
                'content': 'Cấu trúc dữ liệu nào sau đây hoạt động theo nguyên lý FIFO (First In, First Out)?',
                'type': 'choice', 'difficulty': 'easy',
                'explanation': 'Queue (hàng đợi) hoạt động theo nguyên lý FIFO - vào trước ra trước.',
                'tags': [khmt_tag],
                'options': [
                    ('A', 'Stack', False),
                    ('B', 'Queue', True),
                    ('C', 'Tree', False),
                    ('D', 'Graph', False),
                ],
            },
            {
                'content': 'Cho cây nhị phân tìm kiếm (BST) ban đầu rỗng. Thêm lần lượt các giá trị: 5, 3, 7, 2, 4, 6, 8. Kết quả duyệt theo thứ tự giữa (in-order) là:',
                'type': 'choice', 'difficulty': 'hard',
                'explanation': 'Duyệt in-order của BST luôn cho kết quả theo thứ tự tăng dần: 2, 3, 4, 5, 6, 7, 8.',
                'tags': [khmt_tag],
                'options': [
                    ('A', '5, 3, 2, 4, 7, 6, 8', False),
                    ('B', '2, 3, 4, 5, 6, 7, 8', True),
                    ('C', '8, 7, 6, 5, 4, 3, 2', False),
                    ('D', '2, 4, 3, 6, 8, 7, 5', False),
                ],
            },
            {
                'content': 'SQL: Câu lệnh nào được dùng để thêm một bản ghi mới vào bảng?',
                'type': 'choice', 'difficulty': 'easy',
                'explanation': 'INSERT INTO dùng để thêm bản ghi mới. SELECT để truy vấn, UPDATE để cập nhật, DELETE để xóa.',
                'tags': [thud_tag],
                'options': [
                    ('A', 'SELECT', False),
                    ('B', 'INSERT INTO', True),
                    ('C', 'UPDATE', False),
                    ('D', 'DELETE', False),
                ],
            },
            {
                'content': 'Trong mạng máy tính, giao thức nào được sử dụng để truyền tải trang web?',
                'type': 'choice', 'difficulty': 'medium',
                'explanation': 'HTTP (HyperText Transfer Protocol) là giao thức chính dùng để truyền tải nội dung web.',
                'tags': [thud_tag],
                'options': [
                    ('A', 'FTP', False),
                    ('B', 'HTTP', True),
                    ('C', 'SMTP', False),
                    ('D', 'DNS', False),
                ],
            },
            {
                'content': 'Hãy xác định tính Đúng/Sai của các mệnh đề sau về hệ quản trị cơ sở dữ liệu:',
                'type': 'tf', 'difficulty': 'medium',
                'explanation': 'a) MySQL là hệ QTCSDL phổ biến. b) NoSQL không chỉ là lưu file. c) Khóa chính (Primary Key) là đúng. d) Schema là cấu trúc bảng, không phải dữ liệu.',
                'tags': [thud_tag],
                'options': [
                    ('a', 'MySQL là một hệ quản trị cơ sở dữ liệu quan hệ phổ biến.', True),
                    ('b', 'Cơ sở dữ liệu NoSQL chỉ dùng để lưu trữ file.', False),
                    ('c', 'Một bảng trong CSDL quan hệ có thể có nhiều hơn một khóa chính (Primary Key).', False),
                    ('d', 'Schema của CSDL định nghĩa cấu trúc của dữ liệu, không phải bản thân dữ liệu.', True),
                ],
            },
            {
                'content': 'Xác định tính đúng/sai của các phát biểu sau về mạng máy tính:',
                'type': 'tf', 'difficulty': 'hard',
                'explanation': 'a) Router ≠ Switch. b) Địa chỉ IP đúng. c) DNS đúng. d) VPN tạo kết nối an toàn qua mạng công cộng.',
                'tags': [thud_tag],
                'options': [
                    ('a', 'Router và Switch là hai thiết bị mạng có chức năng hoàn toàn giống nhau.', False),
                    ('b', 'Địa chỉ IP 192.168.1.1 thuộc dải địa chỉ private.', True),
                    ('c', 'DNS dùng để phân giải tên miền thành địa chỉ IP.', True),
                    ('d', 'VPN có thể tạo kết nối an toàn qua Internet.', True),
                ],
            },
            {
                'content': 'Trong Python, kết quả của đoạn chương trình sau là gì?\n\n```python\ndef foo(x, y=[]):\n    y.append(x)\n    return y\n\nprint(foo(1))\nprint(foo(2, []))\nprint(foo(3))\n```',
                'type': 'choice', 'difficulty': 'very_hard',
                'explanation': 'Do mutable default argument trong Python, list y được khởi tạo một lần duy nhất. Kết quả: [1], [2], [1, 3].',
                'tags': [khmt_tag],
                'options': [
                    ('A', '[1], [2], [3]', False),
                    ('B', '[1], [2], [1, 3]', True),
                    ('C', '[1], [2], [1]', False),
                    ('D', 'Lỗi biên dịch', False),
                ],
            },
            {
                'content': 'Một website sử dụng chứng chỉ SSL/TLS. Giao thức nào sau đây được dùng để thiết lập kết nối an toàn?',
                'type': 'choice', 'difficulty': 'medium',
                'explanation': 'HTTPS (HTTP Secure) là giao thức HTTP kết hợp với SSL/TLS để mã hóa dữ liệu truyền tải.',
                'tags': [thud_tag],
                'options': [
                    ('A', 'HTTP', False),
                    ('B', 'HTTPS', True),
                    ('C', 'SSH', False),
                    ('D', 'FTP', False),
                ],
            },
            {
                'content': 'Câu hỏi chung: Đơn vị đo lường thông tin nhỏ nhất trong máy tính là gì?',
                'type': 'choice', 'difficulty': 'easy',
                'explanation': 'Bit (Binary Digit) là đơn vị nhỏ nhất, có giá trị 0 hoặc 1.',
                'tags': [],
                'options': [
                    ('A', 'Byte', False),
                    ('B', 'Bit', True),
                    ('C', 'Kilobyte', False),
                    ('D', 'Word', False),
                ],
            },
        ]

        created_count = 0
        for q_data in questions_data:
            tags = q_data.pop('tags', [])
            options_data = q_data.pop('options', [])

            question = QuizQuestion.objects.create(
                **q_data,
                source=sample_exam,
                created_by=admin_user,
            )

            for tag in tags:
                question.tags.add(tag)

            for label, content, is_correct in options_data:
                QuizOption.objects.create(
                    question=question,
                    label=label,
                    content=content,
                    is_correct=is_correct,
                )

            created_count += 1

        # Create CS-specific and IT-specific tag filters in source name
        self.stdout.write(self.style.SUCCESS(
            f'\n=== SEED COMPLETE ===\n'
            f'Created: {created_count} questions\n'
            f'Exam: "{sample_exam.name}" (is_visible=False, only admins see it)\n'
            f'Tags: KHMT ({khmt_tag.questions.count()} questions), '
            f'THUD ({thud_tag.questions.count()} questions)\n'
            f'Common questions: {QuizQuestion.objects.exclude(tags__in=[khmt_tag, thud_tag]).filter(source=sample_exam).count()}\n\n'
            f'Orientation breakdown:\n'
            f'  - CS (KHMT): 4 questions (3 multiple choice + 1 multiple choice)\n'
            f'  - IT (THUD): 5 questions (3 multiple choice + 2 true/false)\n'
            f'  - Common: 1 question (multiple choice)\n\n'
            f'To make this exam visible to users, go to Django admin > Quiz sources > Edit and set is_visible=True'
        ))
