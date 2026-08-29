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

    def test_organization_users_view_and_user_list(self):
        from judge.models import Organization, Class
        org = Organization.objects.create(name='FPT Ha Nam', slug='11-fpt-ha-nam', short_name='FPT', about='Test org')
        self.student_profile.organizations.add(org)
        cls = Class.objects.create(organization=org, name='11A1', slug='11a1')
        cls.members.add(self.student_profile)

        client = Client()
        # Test organization users page
        org_users_url = org.get_users_url()
        resp = client.get(org_users_url)
        self.assertEqual(resp.status_code, 200)

        # Test class page
        class_url = cls.get_absolute_url()
        resp = client.get(class_url)
        self.assertEqual(resp.status_code, 200)

        # Test users leaderboard
        users_url = reverse('user_list')
        resp = client.get(users_url)
        self.assertEqual(resp.status_code, 200)

    def test_exam_anti_cheat_logging_and_auto_submit(self):
        # Create an exam with strict anti-cheat enabled (max 2 violations)
        exam = QuizSource.objects.create(
            name="Kiểm tra Tin học 11 GK2",
            created_by=self.user,
            is_strict_anti_cheat=True,
            max_violations=2,
            default_duration=45
        )
        self.q_choice.source = exam
        self.q_choice.save()

        # Start exam
        client = Client()
        client.force_login(self.student)
        start_url = reverse('quiz_start_exam', kwargs={'exam_id': exam.id})
        resp = client.post(start_url, {'duration': '45', 'orientation': 'KHMT'})
        self.assertEqual(resp.status_code, 302)

        session = QuizSession.objects.filter(user=self.student, answers__has_key='__meta__').latest('id')
        meta = session.answers.get('__meta__')
        self.assertTrue(meta['is_strict_anti_cheat'])
        self.assertEqual(meta['max_violations'], 2)
        self.assertEqual(meta['violation_count'], 0)

        action_url = reverse('quiz_exam_action', kwargs={'session_id': session.id})

        # Violation 1: Tab switch
        resp1 = client.post(action_url, {
            'action': 'log_violation',
            'v_type': 'tab_switch',
            'v_detail': 'Chuyển tab'
        })
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1['violation_count'], 1)
        self.assertFalse(data1['force_submitted'])

        session.refresh_from_db()
        self.assertFalse(session.completed)
        self.assertEqual(session.answers['__meta__']['violation_count'], 1)

        # Violation 2: Exit fullscreen -> exceeds max_violations (2) -> auto-submit!
        resp2 = client.post(action_url, {
            'action': 'log_violation',
            'v_type': 'fullscreen_exit',
            'v_detail': 'Thoát toàn màn hình'
        })
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2['violation_count'], 2)
        self.assertTrue(data2['force_submitted'])

        session.refresh_from_db()
        self.assertTrue(session.completed)

    def test_exam_analytics_and_live_monitor_and_export(self):
        # Create exam
        exam = QuizSource.objects.create(
            name="Kiểm tra Tin học cuối kỳ",
            created_by=self.user,
            is_strict_anti_cheat=True,
            max_violations=3
        )
        self.q_choice.source = exam
        self.q_choice.save()
        self.q_tf.source = exam
        self.q_tf.save()

        # Create 1 completed session and 1 active session
        session_completed = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id, self.q_tf.id],
            answers={
                '__meta__': {
                    'is_exam': True,
                    'source_id': exam.id,
                    'source_name': exam.name,
                    'duration': 45,
                    'time_left': 1800,
                    'orientation': 'KHMT',
                    'is_strict_anti_cheat': True,
                    'max_violations': 3,
                    'violation_count': 1,
                    'violations_log': [{'time': '10:15:00', 'type': 'tab_switch', 'detail': 'Chuyển tab'}]
                },
                str(self.q_choice.id): 'A', # Correct
            },
            completed=True,
            score=0.25
        )

        session_active = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id, self.q_tf.id],
            answers={
                '__meta__': {
                    'is_exam': True,
                    'source_id': exam.id,
                    'source_name': exam.name,
                    'duration': 45,
                    'time_left': 2400,
                    'orientation': 'KHMT',
                    'is_strict_anti_cheat': True,
                    'max_violations': 3,
                    'violation_count': 0,
                    'violations_log': []
                }
            },
            completed=False
        )

        teacher_client = Client()
        teacher_client.force_login(self.user)

        # 1. Analytics view
        analytics_url = reverse('quiz_exam_analytics', kwargs={'exam_id': exam.id})
        resp_analytics = teacher_client.get(analytics_url)
        self.assertEqual(resp_analytics.status_code, 200)
        self.assertContains(resp_analytics, "Phân tích số liệu")
        self.assertContains(resp_analytics, "Kiểm tra Tin học cuối kỳ")

        # Test Analytics with Class/Org filter
        from judge.models import Organization, Class
        test_org = Organization.objects.create(name='THPT Chuyên', slug='thpt-chuyen', short_name='CHUYEN')
        self.student_profile.organizations.add(test_org)
        test_class = Class.objects.create(organization=test_org, name='12A1', slug='12a1')
        test_class.members.add(self.student_profile)

        resp_analytics_filtered = teacher_client.get(f"{analytics_url}?class_id={test_class.id}")
        self.assertEqual(resp_analytics_filtered.status_code, 200)
        self.assertContains(resp_analytics_filtered, "12A1")

        # 2. Live monitor page
        monitor_url = reverse('quiz_exam_monitor', kwargs={'exam_id': exam.id})
        resp_monitor = teacher_client.get(monitor_url)
        self.assertEqual(resp_monitor.status_code, 200)

        # 3. Live monitor Ajax API
        ajax_url = reverse('quiz_exam_monitor_ajax', kwargs={'exam_id': exam.id})
        resp_ajax = teacher_client.get(ajax_url)
        self.assertEqual(resp_ajax.status_code, 200)
        data = resp_ajax.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['active_count'], 1)
        self.assertEqual(data['completed_count'], 1)
        self.assertEqual(data['students'][0]['session_id'], session_active.id)

        # 4. CSV Export (with and without class filter)
        export_url = reverse('quiz_exam_export', kwargs={'exam_id': exam.id})
        resp_export = teacher_client.get(f"{export_url}?class_id={test_class.id}")
        self.assertEqual(resp_export.status_code, 200)
        self.assertEqual(resp_export['Content-Type'], 'text/csv; charset=utf-8')
        content = resp_export.content.decode('utf-8')
        self.assertIn('student', content)
        self.assertIn('0.25', content)
        self.assertIn('tab_switch', content)
        self.assertIn('12A1', content)

    def test_exam_hub_pin_join_and_gradebook(self):
        from judge.models import Organization, Class, QuizSource
        
        teacher_client = Client()
        teacher_client.force_login(self.user)

        student_client = Client()
        student_client.force_login(self.student)

        # 1. Test Exam Hub View
        hub_url = reverse('quiz_hub')
        resp_teacher_hub = teacher_client.get(hub_url)
        self.assertEqual(resp_teacher_hub.status_code, 200)

        resp_student_hub = student_client.get(hub_url)
        self.assertEqual(resp_student_hub.status_code, 200)

        # 2. Test Exam with PIN Code
        exam_pin = QuizSource.objects.create(
            name='Đề thi thử PIN Code',
            default_duration=30,
            access_code='987654',
            is_active=True,
            is_visible=True,
            created_by=self.user
        )

        # Test Join by PIN (GET & POST)
        join_url = reverse('quiz_join_pin')
        resp_get = student_client.get(f"{join_url}?pin=987654")
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Đề thi thử PIN Code")

        resp_post = student_client.post(join_url, {'pin_code': '987654'})
        self.assertEqual(resp_post.status_code, 302)
        self.assertTrue(resp_post.url.startswith(f"/quiz/exams/{exam_pin.id}/start/"))

        # Test Toggle Active
        toggle_url = reverse('quiz_exam_toggle_active', kwargs={'exam_id': exam_pin.id})
        resp_toggle = teacher_client.post(toggle_url)
        self.assertEqual(resp_toggle.status_code, 200)
        self.assertFalse(resp_toggle.json()['is_active'])

        # Now when exam is inactive, student cannot join
        resp_closed = student_client.post(join_url, {'pin_code': '987654'})
        self.assertEqual(resp_closed.status_code, 200)
        self.assertContains(resp_closed, "hiện đang đóng")

        # 3. Test PIN Date Restrictions (start_time & end_time)
        from django.utils import timezone
        import datetime

        # Test expired exam (end_time in past)
        exam_pin.is_active = True
        exam_pin.end_time = timezone.now() - datetime.timedelta(days=1)
        exam_pin.save()

        resp_expired = student_client.post(join_url, {'pin_code': '987654'})
        self.assertEqual(resp_expired.status_code, 200)
        self.assertContains(resp_expired, "đã hết hạn")

        # Test future exam (start_time in future)
        exam_pin.end_time = None
        exam_pin.start_time = timezone.now() + datetime.timedelta(days=1)
        exam_pin.save()

        resp_future = student_client.post(join_url, {'pin_code': '987654'})
        self.assertEqual(resp_future.status_code, 200)
        self.assertContains(resp_future, "chưa mở")

        # Reset time
        exam_pin.start_time = None
        exam_pin.save()

        # 4. Test Class Gradebook
        test_org = Organization.objects.create(name='Trường THPT Amsterdam', slug='thpt-ams')
        test_class = Class.objects.create(organization=test_org, name='10 Tin', slug='10-tin')
        test_class.members.add(self.student_profile)
        test_class.admins.add(self.user_profile)

        exam_pin.target_classes.add(test_class)

        gradebook_url = reverse('quiz_class_gradebook', kwargs={'class_id': test_class.id})
        resp_gradebook = teacher_client.get(gradebook_url)
        self.assertEqual(resp_gradebook.status_code, 200)
        self.assertContains(resp_gradebook, "10 Tin")
        self.assertContains(resp_gradebook, "student")

        # Gradebook CSV Export
        gb_export_url = reverse('quiz_class_gradebook_export', kwargs={'class_id': test_class.id})
        resp_gb_export = teacher_client.get(gb_export_url)
        self.assertEqual(resp_gb_export.status_code, 200)
        self.assertIn('student', resp_gb_export.content.decode('utf-8'))

        # 5. Test Live Proctor Actions
        active_sess = QuizSession.objects.create(
            user=self.student,
            questions=[self.q_choice.id, self.q_tf.id],
            answers={'__meta__': {'is_exam': True, 'source_id': exam_pin.id, 'duration': 30, 'time_left': 1800}},
            completed=False
        )

        proctor_url = reverse('quiz_exam_proctor_action', kwargs={'exam_id': exam_pin.id})
        
        # Test 5.1: Warning
        resp_warn = teacher_client.post(proctor_url, {
            'session_id': active_sess.id,
            'action': 'warning',
            'message': 'Chú ý tập trung làm bài, không nhìn sang màn hình khác!'
        })
        self.assertEqual(resp_warn.status_code, 200)
        active_sess.refresh_from_db()
        self.assertIn('proctor_warning', active_sess.answers['__meta__'])
        self.assertIn('Chú ý tập trung', active_sess.answers['__meta__']['proctor_warning']['message'])

        # Test 5.2: Pause
        resp_pause = teacher_client.post(proctor_url, {
            'session_id': active_sess.id,
            'action': 'pause'
        })
        self.assertEqual(resp_pause.status_code, 200)
        active_sess.refresh_from_db()
        self.assertTrue(active_sess.answers['__meta__']['is_paused'])

        # Test 5.3: Resume
        resp_resume = teacher_client.post(proctor_url, {
            'session_id': active_sess.id,
            'action': 'resume'
        })
        self.assertEqual(resp_resume.status_code, 200)
        active_sess.refresh_from_db()
        self.assertFalse(active_sess.answers['__meta__']['is_paused'])

        # Test 5.4: Add Time (+5 minutes)
        initial_time = active_sess.answers['__meta__']['time_left']
        resp_time = teacher_client.post(proctor_url, {
            'session_id': active_sess.id,
            'action': 'add_time',
            'minutes': '5'
        })
        self.assertEqual(resp_time.status_code, 200)
        active_sess.refresh_from_db()
        self.assertEqual(active_sess.answers['__meta__']['time_left'], initial_time + 300)

        # Test 5.5: Force Submit
        resp_force = teacher_client.post(proctor_url, {
            'session_id': active_sess.id,
            'action': 'force_submit'
        })
        self.assertEqual(resp_force.status_code, 200)
        active_sess.refresh_from_db()
        self.assertTrue(active_sess.completed)

        # 6. Test Adaptive Remediation Assignment Generator
        # Link questions to exam_pin
        self.q_choice.source = exam_pin
        self.q_choice.save()
        self.q_tf.source = exam_pin
        self.q_tf.save()

        remed_url = reverse('quiz_exam_remediation', kwargs={'exam_id': exam_pin.id})
        resp_remed = teacher_client.post(remed_url)
        self.assertEqual(resp_remed.status_code, 302)
        
        # Verify new homework exam was created
        homework_exams = QuizSource.objects.filter(exam_type='homework')
        self.assertTrue(homework_exams.exists())
        hw = homework_exams.first()
        self.assertIn('Bài tập củng cố', hw.name)
        self.assertTrue(hw.target_classes.filter(id=test_class.id).exists())







