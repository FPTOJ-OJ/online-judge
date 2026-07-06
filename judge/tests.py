from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json
from judge.models.quiz import QuizTag, QuizSource, QuizQuestion, QuizOption, QuizSession

class QuizTestCase(TestCase):
    def setUp(self):
        from judge.models.profile import Profile
        
        # Create user
        self.user = User.objects.create_user(username='testteacher', password='password123')
        self.user_profile = Profile.objects.create(user=self.user, display_rank='setter')

        # Create student user
        self.student = User.objects.create_user(username='student', password='password123')
        self.student_profile = Profile.objects.create(user=self.student)

        # Create tags
        self.tag_networking = QuizTag.objects.create(name='Mạng máy tính và Internet', slug='mang-may-tinh-va-internet')
        self.tag_html = QuizTag.objects.create(name='HTML/CSS', slug='html-css')

        # Create source
        self.source = QuizSource.objects.create(name='Đề mẫu 2026')

        # Create standard multiple choice question
        self.q_choice = QuizQuestion.objects.create(
            content='Giao thức TCP không có vai trò nào sau đây?',
            type='choice',
            difficulty='easy',
            source=self.source,
            created_by=self.user
        )
        self.q_choice.tags.add(self.tag_networking)

        # Options for choice
        self.opt_a = QuizOption.objects.create(question=self.q_choice, label='A', content='Định tuyến đường đi', is_correct=True)
        self.opt_b = QuizOption.objects.create(question=self.q_choice, label='B', content='Kiểm soát lỗi', is_correct=False)
        self.opt_c = QuizOption.objects.create(question=self.q_choice, label='C', content='Kiểm soát lưu lượng', is_correct=False)
        self.opt_d = QuizOption.objects.create(question=self.q_choice, label='D', content='Phân mảnh dữ liệu', is_correct=False)

        # Create True/False question
        self.q_tf = QuizQuestion.objects.create(
            content='Có một số nhận xét sau về HTML:',
            type='tf',
            difficulty='medium',
            source=self.source,
            created_by=self.user
        )
        self.q_tf.tags.add(self.tag_html)

        # Options for True/False
        self.opt_tf_a = QuizOption.objects.create(question=self.q_tf, label='a', content='Thẻ html bắt buộc phải có.', is_correct=True)
        self.opt_tf_b = QuizOption.objects.create(question=self.q_tf, label='b', content='Thẻ head nằm ngoài thẻ html.', is_correct=False)
        self.opt_tf_c = QuizOption.objects.create(question=self.q_tf, label='c', content='CSS chỉ được nhúng ở thẻ head.', is_correct=False)
        self.opt_tf_d = QuizOption.objects.create(question=self.q_tf, label='d', content='Trình duyệt biên dịch HTML.', is_correct=True)

    def test_question_creation(self):
        self.assertEqual(QuizQuestion.objects.count(), 2)
        self.assertEqual(self.q_choice.options.count(), 4)
        self.assertEqual(self.q_tf.options.count(), 4)

    def test_quiz_filters(self):
        client = Client()
        
        # Test tag filter
        response = client.get(reverse('quiz_home') + '?tag=mang-may-tinh-va-internet')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Giao thức TCP không có vai trò nào sau đây?')
        self.assertNotContains(response, 'Có một số nhận xét sau về HTML:')

    def test_quiz_session_multiple_choice_correct(self):
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id],
            answers={},
            current_index=0,
            completed=False
        )

        client = Client()
        client.force_login(self.student)

        # Submit correct answer A
        action_url = reverse('quiz_session_action', kwargs={'session_id': session.id})
        response = client.post(action_url, {
            'action': 'submit',
            'answer': 'A'
        })
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data['correct'])
        self.assertEqual(res_data['correct_answers'], ['A'])

        session.refresh_from_db()
        self.assertEqual(session.score, 1.0)

    def test_quiz_session_multiple_choice_incorrect(self):
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id],
            answers={},
            current_index=0,
            completed=False
        )

        client = Client()
        client.force_login(self.student)

        # Submit incorrect answer B
        action_url = reverse('quiz_session_action', kwargs={'session_id': session.id})
        response = client.post(action_url, {
            'action': 'submit',
            'answer': 'B'
        })
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertFalse(res_data['correct'])
        self.assertEqual(res_data['correct_answers'], ['A'])

        session.refresh_from_db()
        self.assertEqual(session.score, 0.0)

    def test_quiz_session_true_false_grading_schemes(self):
        # We test scoring for True/False questions (Chùm Đúng/Sai)
        # Correct pattern: a=True, b=False, c=False, d=True
        
        # Testcase 1: 4 correct statements -> score 1.0
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_tf.id],
            answers={},
            current_index=0,
            completed=False
        )
        client = Client()
        client.force_login(self.student)
        action_url = reverse('quiz_session_action', kwargs={'session_id': session.id})
        
        response = client.post(action_url, {
            'action': 'submit',
            'tf_a': 'true',
            'tf_b': 'false',
            'tf_c': 'false',
            'tf_d': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['correct_count'], 4)
        session.refresh_from_db()
        self.assertEqual(session.score, 1.0)

        # Testcase 2: 3 correct statements -> score 0.5
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_tf.id],
            answers={},
            current_index=0,
            completed=False
        )
        action_url = reverse('quiz_session_action', kwargs={'session_id': session.id})
        response = client.post(action_url, {
            'action': 'submit',
            'tf_a': 'true',
            'tf_b': 'false',
            'tf_c': 'false',
            'tf_d': 'false' # wrong
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['correct_count'], 3)
        session.refresh_from_db()
        self.assertEqual(session.score, 0.5)

        # Testcase 3: 2 correct statements -> score 0.25
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_tf.id],
            answers={},
            current_index=0,
            completed=False
        )
        action_url = reverse('quiz_session_action', kwargs={'session_id': session.id})
        response = client.post(action_url, {
            'action': 'submit',
            'tf_a': 'true',
            'tf_b': 'false',
            'tf_c': 'true', # wrong
            'tf_d': 'false' # wrong
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['correct_count'], 2)
        session.refresh_from_db()
        self.assertEqual(session.score, 0.25)

    def test_session_review_view(self):
        # Create a session and answer a question
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id],
            answers={str(self.q_choice.id): 'B'}, # Correct answer is 'A'
            current_index=0,
            completed=True,
            score=0.0
        )
        
        client = Client()
        client.force_login(self.student)
        
        url = reverse('quiz_session_review', kwargs={'session_id': session.id})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kết Quả Luyện Tập")

    def test_incorrect_questions_filtering_helper(self):
        # Create a session where the user got choice question incorrect
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id, self.q_tf.id],
            answers={
                str(self.q_choice.id): 'B', # Wrong (correct is A)
                str(self.q_tf.id): {
                    'a': True,  # Correct (True)
                    'b': False, # Correct (False)
                    'c': False, # Correct (False)
                    'd': True   # Correct (True)
                } # Correct (all 4 match)
            },
            current_index=1,
            completed=True,
            score=1.0
        )
        
        incorrect_ids = QuizSession.get_incorrect_questions_for_user(user=self.student)
        self.assertIn(self.q_choice.id, incorrect_ids)
        self.assertNotIn(self.q_tf.id, incorrect_ids)

    def test_bulk_import_view(self):
        client = Client()
        client.force_login(self.user) # Teacher has rank 'setter'
        
        import_url = reverse('quiz_bulk_import')
        
        # Test GET
        response = client.get(import_url)
        self.assertEqual(response.status_code, 200)
        
        # Test POST with valid JSON
        import_data = [
            {
                "content": "New imported multiple choice question",
                "type": "choice",
                "difficulty": "medium",
                "tags": ["ImportedTag"],
                "source": "ImportedSource",
                "options": [
                    {"label": "A", "content": "Correct opt", "is_correct": True},
                    {"label": "B", "content": "Wrong opt", "is_correct": False}
                ],
                "explanation": "Imported explanation"
            }
        ]
        
        response = client.post(import_url, {
            'json_data': json.dumps(import_data)
        })
        self.assertEqual(response.status_code, 302) # Redirect to manage dashboard
        
        # Check database
        imported_q = QuizQuestion.objects.filter(content="New imported multiple choice question").first()
        self.assertIsNotNone(imported_q)
        self.assertEqual(imported_q.difficulty, 'medium')
        self.assertEqual(imported_q.options.count(), 2)
        self.assertEqual(imported_q.options.filter(is_correct=True).count(), 1)
        self.assertEqual(imported_q.tags.filter(name="ImportedTag").count(), 1)
        self.assertEqual(imported_q.source.name, "ImportedSource")

        # Test POST with uploaded JSON file
        from django.core.files.uploadedfile import SimpleUploadedFile
        import_file_data = [
            {
                "content": "Uploaded file question",
                "type": "choice",
                "difficulty": "easy",
                "tags": ["FileTag"],
                "source": "FileSource",
                "options": [
                    {"label": "A", "content": "Correct opt", "is_correct": True}
                ],
                "explanation": "File explanation"
            }
        ]
        json_file = SimpleUploadedFile("questions.json", json.dumps(import_file_data).encode('utf-8'), content_type="application/json")
        response = client.post(import_url, {
            'json_file': json_file
        })
        self.assertEqual(response.status_code, 302)

        uploaded_q = QuizQuestion.objects.filter(content="Uploaded file question").first()
        self.assertIsNotNone(uploaded_q)
        self.assertEqual(uploaded_q.options.count(), 1)
        self.assertEqual(uploaded_q.tags.filter(name="FileTag").count(), 1)
        self.assertEqual(uploaded_q.source.name, "FileSource")

    def test_delete_session(self):
        session = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id],
            answers={},
            current_index=0,
            completed=False
        )
        client = Client()
        client.force_login(self.student)
        action_url = reverse('quiz_session_action', kwargs={'session_id': session.id})
        
        response = client.post(action_url, {
            'action': 'delete'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        self.assertFalse(QuizSession.objects.filter(id=session.id).exists())


