import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.utils.text import slugify
from django.db.models import Q, Count
import random

from judge.models.quiz import QuizTag, QuizSource, QuizQuestion, QuizOption, QuizSession
from judge.jinja2.markdown import markdown
from judge.widgets.martor import MartorWidget

def is_teacher(user):
    return user.is_authenticated and (
        user.is_staff or 
        user.is_superuser or 
        (hasattr(user, 'profile') and user.profile.display_rank in ('setter', 'admin'))
    )

class QuizHomeView(View):
    def get(self, request):
        # Gather filters
        tag_slug = request.GET.get('tag')
        difficulty = request.GET.get('difficulty')
        q_type = request.GET.get('type')
        source_id = request.GET.get('source')
        search_query = request.GET.get('q')
        only_incorrect = request.GET.get('only_incorrect') == 'true'

        questions = QuizQuestion.objects.all()

        if only_incorrect:
            incorrect_ids = QuizSession.get_incorrect_questions_for_user(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key
            )
            questions = questions.filter(id__in=incorrect_ids)

        if tag_slug:
            questions = questions.filter(tags__slug=tag_slug)
        if difficulty:
            questions = questions.filter(difficulty=difficulty)
        if q_type:
            questions = questions.filter(type=q_type)
        if source_id:
            questions = questions.filter(source_id=source_id)
        if search_query:
            questions = questions.filter(
                Q(content__icontains=search_query) | 
                Q(explanation__icontains=search_query)
            )

        # Get counts and matching questions
        total_matching = questions.count()
        
        # Prefetch options and tags for listing
        questions_list = questions.prefetch_related('options', 'tags').select_related('source')[:100]

        # For filters dropdowns
        tags = QuizTag.objects.all()
        
        # Resolve dynamic list of matching exams (sources) for the 'Theo đề' tab
        from django.db.models import Count
        matching_source_ids = questions.values_list('source_id', flat=True).distinct()
        matching_sources = QuizSource.objects.filter(id__in=matching_source_ids).annotate(total_questions=Count('questions'))
        
        import re
        matching_sources_list = []
        for s in matching_sources:
            first_q = s.questions.order_by('id').first()
            if not first_q:
                continue
            first_q_content = first_q.content
            clean_snippet = re.sub(r'!\[.*?\]\(.*?\)', '', first_q_content)
            clean_snippet = re.sub(r'\[.*?\]\(.*?\)', '', clean_snippet)
            clean_snippet = re.sub(r'#+\s+', '', clean_snippet)
            clean_snippet = clean_snippet.replace('\n', ' ').strip()
            snippet = clean_snippet[:150] + "..." if len(clean_snippet) > 150 else clean_snippet
            
            # Year
            year_match = re.search(r'\b(202\d|199\d)\b', s.name)
            s_year = year_match.group(1) if year_match else "2026"
            
            # Type
            s_name_lower = s.name.lower()
            if "sở" in s_name_lower:
                s_type_label = "Đề sở"
                s_type_key = "dept"
            elif any(x in s_name_lower for x in ["trường", "chuyên", "thpt"]):
                s_type_label = "Đề trường"
                s_type_key = "school"
            elif "tự tạo" in s_name_lower or "custom" in s_name_lower:
                s_type_label = "Tự tạo"
                s_type_key = "custom"
            else:
                s_type_label = "Đề khác"
                s_type_key = "other"
                
            tf_count = s.questions.filter(type='tf').count()
            
            # Fetch user history and best score
            if request.user.is_authenticated:
                sessions_completed = QuizSession.objects.filter(user=request.user, completed=True)
            elif request.session.session_key:
                sessions_completed = QuizSession.objects.filter(session_key=request.session.session_key, completed=True)
            else:
                sessions_completed = []
            
            exam_sessions = [sess for sess in sessions_completed if first_q.id in sess.questions]
            best_score = max(sess.score for sess in exam_sessions) if exam_sessions else None
            is_done = len(exam_sessions) > 0
            
            history = []
            for sess in exam_sessions:
                history.append({
                    'id': sess.id,
                    'score': round(sess.score, 2),
                    'date': sess.created_at.strftime('%H:%M %d/%m/%Y'),
                })
                
            matching_sources_list.append({
                'id': s.id,
                'name': s.name,
                'total_questions': s.total_questions,
                'tf_count': tf_count,
                'snippet': snippet,
                'year': s_year,
                'type_key': s_type_key,
                'type_label': s_type_label,
                'best_score': round(best_score, 2) if best_score is not None else None,
                'is_done': is_done,
                'history': history,
            })
            
        sources = QuizSource.objects.all()
        
        # Current active filters display
        active_filters = []
        if only_incorrect:
            active_filters.append("Chỉ câu hỏi từng làm sai")
        if tag_slug:
            t = QuizTag.objects.filter(slug=tag_slug).first()
            if t: active_filters.append(f"Chủ đề: {t.name}")
        if difficulty:
            diff_dict = dict(QuizQuestion.DIFFICULTY_CHOICES)
            active_filters.append(f"Độ khó: {diff_dict.get(difficulty, difficulty)}")
        if q_type:
            type_dict = dict(QuizQuestion.QUESTION_TYPES)
            active_filters.append(f"Loại câu: {type_dict.get(q_type, q_type)}")
        if source_id:
            s = QuizSource.objects.filter(id=source_id).first()
            if s: active_filters.append(f"Đề: {s.name}")

        # Fetch past sessions for practice history log
        past_sessions = []
        if request.user.is_authenticated:
            past_sessions = QuizSession.objects.filter(user=request.user).order_by('-created_at')[:10]
        elif request.session.session_key:
            past_sessions = QuizSession.objects.filter(session_key=request.session.session_key).order_by('-created_at')[:10]

        context = {
            'title': 'Luyện trắc nghiệm tốt nghiệp THPT',
            'questions': questions_list,
            'total_matching': total_matching,
            'tags': tags,
            'sources': sources,
            'matching_sources': matching_sources_list,
            'active_filters': active_filters,
            'selected_tag': tag_slug,
            'selected_difficulty': difficulty,
            'selected_type': q_type,
            'selected_source': source_id,
            'search_query': search_query,
            'only_incorrect': only_incorrect,
            'past_sessions': past_sessions,
            'is_teacher': is_teacher(request.user),
        }
        return render(request, 'quiz/home.html', context)

    def post(self, request):
        # Start practice session
        tag_slug = request.POST.get('tag')
        difficulty = request.POST.get('difficulty')
        q_type = request.POST.get('type')
        source_id = request.POST.get('source')
        only_incorrect = request.POST.get('only_incorrect') == 'true'
        
        mode = request.POST.get('mode', 'random') # random or original
        num_questions_str = request.POST.get('num_questions', '').strip()

        questions = QuizQuestion.objects.all()

        if only_incorrect:
            incorrect_ids = QuizSession.get_incorrect_questions_for_user(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key
            )
            questions = questions.filter(id__in=incorrect_ids)

        if tag_slug:
            questions = questions.filter(tags__slug=tag_slug)
        if difficulty:
            questions = questions.filter(difficulty=difficulty)
        if q_type:
            questions = questions.filter(type=q_type)
        if source_id:
            questions = questions.filter(source_id=source_id)

        all_matching_ids = list(questions.values_list('id', flat=True))

        if not all_matching_ids:
            return redirect('quiz_home')

        # Get recently answered question IDs to avoid repeating too quickly
        recent_question_ids = []
        if request.user.is_authenticated:
            past_sessions = QuizSession.objects.filter(user=request.user).order_by('-created_at')[:5]
        elif request.session.session_key:
            past_sessions = QuizSession.objects.filter(session_key=request.session.session_key).order_by('-created_at')[:5]
        else:
            past_sessions = []
            
        for sess in past_sessions:
            for q_id_str in sess.answers.keys():
                if q_id_str.isdigit():
                    recent_question_ids.append(int(q_id_str))
        recent_question_ids = set(recent_question_ids)

        # Separate matching IDs into non-recent and recent
        non_recent_ids = [qid for qid in all_matching_ids if qid not in recent_question_ids]
        recent_ids = [qid for qid in all_matching_ids if qid in recent_question_ids]

        if mode == 'random':
            random.shuffle(non_recent_ids)
            random.shuffle(recent_ids)
            question_ids = non_recent_ids + recent_ids
            if num_questions_str:
                try:
                    num_questions = int(num_questions_str)
                    if num_questions > 0:
                        question_ids = question_ids[:num_questions]
                except ValueError:
                    pass
        else:
            non_recent_ids.sort()
            recent_ids.sort()
            question_ids = non_recent_ids + recent_ids
            if num_questions_str:
                try:
                    num_questions = int(num_questions_str)
                    if num_questions > 0:
                        question_ids = question_ids[:num_questions]
                except ValueError:
                    pass

        # Ensure session is created for guests
        if not request.session.session_key:
            request.session.create()

        session = QuizSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else None,
            questions=question_ids,
            answers={},
            current_index=0,
            completed=False,
            score=0.0
        )
        return redirect('quiz_session_detail', session_id=session.id)


class QuizSessionDetailView(View):
    def get(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        
        # Verify ownership
        if session.user:
            if session.user != request.user:
                return HttpResponseForbidden("Bạn không có quyền truy cập phiên luyện tập này.")
        else:
            if session.session_key != request.session.session_key:
                return HttpResponseForbidden("Bạn không có quyền truy cập phiên luyện tập này.")

        if session.completed:
            # Show completed summary page
            # Calculate breakdown
            total_questions = len(session.questions)
            answered_questions = len(session.answers)
            skipped_questions = total_questions - answered_questions
            
            context = {
                'title': 'Kết quả luyện tập',
                'session': session,
                'total_questions': total_questions,
                'answered_questions': answered_questions,
                'skipped_questions': skipped_questions,
                'score': round(session.score, 2),
            }
            return render(request, 'quiz/session_summary.html', context)

        if not session.questions:
            return redirect('quiz_home')

        # Load question
        current_idx = session.current_index
        if current_idx < 0 or current_idx >= len(session.questions):
            session.completed = True
            session.save()
            return redirect('quiz_session_detail', session_id=session.id)

        question_id = session.questions[current_idx]
        question = get_object_or_404(QuizQuestion.objects.prefetch_related('options').select_related('source'), id=question_id)

        # Retrieve previous user answer if already answered
        user_ans = session.answers.get(str(question_id))

        context = {
            'title': f'Câu hỏi {current_idx + 1}',
            'session': session,
            'question': question,
            'options': question.options.all(),
            'current_number': current_idx + 1,
            'total_questions': len(session.questions),
            'user_answer': user_ans,
            'is_answered': user_ans is not None,
        }
        return render(request, 'quiz/session.html', context)


class QuizSessionActionView(View):
    def post(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        
        if session.user and session.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        if not session.user and session.session_key != request.session.session_key:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        action = request.POST.get('action')
        
        if action == 'end':
            session.completed = True
            session.save()
            return JsonResponse({'redirect': request.build_absolute_uri(redirect('quiz_session_detail', session_id=session.id).url)})

        if action == 'delete':
            session.delete()
            return JsonResponse({'success': True})

        if action == 'prev':
            if session.current_index > 0:
                session.current_index -= 1
                session.save()
            return JsonResponse({'success': True})

        if action == 'next':
            if session.current_index < len(session.questions) - 1:
                session.current_index += 1
                session.save()
            else:
                session.completed = True
                session.save()
            return JsonResponse({'success': True})

        if action == 'skip':
            # Mark question as skipped (empty answer)
            current_q_id = str(session.questions[session.current_index])
            if current_q_id not in session.answers:
                # We can store null or skip value
                session.answers[current_q_id] = '__skipped__'
            
            if session.current_index < len(session.questions) - 1:
                session.current_index += 1
                session.save()
                return JsonResponse({'success': True, 'ended': False})
            else:
                session.completed = True
                session.save()
                return JsonResponse({'success': True, 'ended': True})

        if action == 'submit':
            # Grade the current question
            current_q_id = session.questions[session.current_index]
            question = get_object_or_404(QuizQuestion.objects.prefetch_related('options'), id=current_q_id)
            
            # Answer inputs from request
            if question.type == 'choice':
                selected_label = request.POST.get('answer') # e.g. 'A'
                if not selected_label:
                    return JsonResponse({'error': 'No answer selected'}, status=400)
                
                # Check correctness
                correct_option = question.options.filter(is_correct=True).first()
                correct_label = correct_option.label if correct_option else 'A'
                
                is_correct = (selected_label == correct_label)
                score_delta = 1.0 if is_correct else 0.0

                session.answers[str(current_q_id)] = selected_label
                session.score += score_delta
                session.save()

                rendered_explanation = markdown(question.explanation or "Chưa có lời giải chi tiết cho câu hỏi này.", "problem")

                return JsonResponse({
                    'correct': is_correct,
                    'correct_answers': [correct_label],
                    'explanation': rendered_explanation,
                })

            elif question.type == 'tf':
                # Chùm Đúng/Sai
                # User submits answers like tf_a=true, tf_b=false, tf_c=true, tf_d=false
                # We expect data keys mapping label -> boolean
                submitted_answers = {}
                options = question.options.all()
                
                for opt in options:
                    val = request.POST.get(f'tf_{opt.label}') # 'true' or 'false'
                    if val is not None:
                        submitted_answers[opt.label] = (val == 'true')
                    else:
                        submitted_answers[opt.label] = None

                # Calculate score
                # Count correct statements
                correct_count = 0
                total_statements = len(options)
                correct_details = {}
                correct_answers = {}

                for opt in options:
                    correct_answers[opt.label] = opt.is_correct
                    user_val = submitted_answers.get(opt.label)
                    is_statement_correct = (user_val == opt.is_correct)
                    correct_details[opt.label] = is_statement_correct
                    if is_statement_correct:
                        correct_count += 1

                # Official Vietnamese THPT True/False set grading:
                # 1 correct statement: 0.1 pt
                # 2 correct statements: 0.25 pt
                # 3 correct statements: 0.5 pt
                # 4 correct statements: 1.0 pt
                score_delta = 0.0
                if correct_count == 1:
                    score_delta = 0.1
                elif correct_count == 2:
                    score_delta = 0.25
                elif correct_count == 3:
                    score_delta = 0.5
                elif correct_count == 4:
                    score_delta = 1.0

                session.answers[str(current_q_id)] = submitted_answers
                session.score += score_delta
                session.save()

                rendered_explanation = markdown(question.explanation or "Chưa có lời giải chi tiết cho câu hỏi này.", "problem")

                return JsonResponse({
                    'correct_count': correct_count,
                    'correct_details': correct_details,
                    'correct_answers': correct_answers,
                    'explanation': rendered_explanation,
                })

        return JsonResponse({'error': 'Invalid action'}, status=400)


class QuizManageDashboardView(View):
    def get(self, request):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền truy cập trang quản lý câu hỏi.")

        # List questions created by the teacher (or all questions for admins)
        if request.user.is_superuser:
            questions = QuizQuestion.objects.all()
        else:
            questions = QuizQuestion.objects.filter(created_by=request.user)

        questions = questions.prefetch_related('tags').select_related('source').order_by('-created_at')

        context = {
            'title': 'Quản lý câu hỏi trắc nghiệm',
            'questions': questions,
        }
        return render(request, 'quiz/manage.html', context)


class QuizQuestionCreateEditView(View):
    def get(self, request, question_id=None):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền tạo/sửa câu hỏi.")

        question = None
        options_data = []
        if question_id:
            question = get_object_or_404(QuizQuestion, id=question_id)
            # If not superuser, must be creator
            if not request.user.is_superuser and question.created_by != request.user:
                return HttpResponseForbidden("Bạn không có quyền chỉnh sửa câu hỏi này.")
            options_data = list(question.options.all().order_by('label'))

        tags = QuizTag.objects.all()
        sources = QuizSource.objects.all()

        content_widget = MartorWidget(attrs={'id': 'id_content', 'name': 'content', 'required': 'required'})
        explanation_widget = MartorWidget(attrs={'id': 'id_explanation', 'name': 'explanation'})

        content_html = content_widget.render('content', question.content if question else '', attrs={})
        explanation_html = explanation_widget.render('explanation', question.explanation if question and question.explanation else '', attrs={})

        context = {
            'title': 'Sửa câu hỏi' if question else 'Thêm câu hỏi mới',
            'question': question,
            'options': options_data,
            'tags': tags,
            'sources': sources,
            'difficulty_choices': QuizQuestion.DIFFICULTY_CHOICES,
            'question_types': QuizQuestion.QUESTION_TYPES,
            'content_html': content_html,
            'explanation_html': explanation_html,
            'media': content_widget.media,
        }
        return render(request, 'quiz/edit.html', context)

    def post(self, request, question_id=None):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền tạo/sửa câu hỏi.")

        question = None
        if question_id:
            question = get_object_or_404(QuizQuestion, id=question_id)
            if not request.user.is_superuser and question.created_by != request.user:
                return HttpResponseForbidden("Bạn không có quyền chỉnh sửa câu hỏi này.")

        content = request.POST.get('content')
        q_type = request.POST.get('type')
        difficulty = request.POST.get('difficulty')
        explanation = request.POST.get('explanation')
        source_name = request.POST.get('source_new', '').strip()
        source_id = request.POST.get('source')
        tags_raw = request.POST.getlist('tags') # List of tag IDs or tag names

        if not content:
            content_widget = MartorWidget(attrs={'id': 'id_content', 'name': 'content', 'required': 'required'})
            explanation_widget = MartorWidget(attrs={'id': 'id_explanation', 'name': 'explanation'})
            content_html = content_widget.render('content', question.content if question else '', attrs={})
            explanation_html = explanation_widget.render('explanation', question.explanation if question and question.explanation else '', attrs={})
            return render(request, 'quiz/edit.html', {
                'error': 'Nội dung câu hỏi không được để trống.',
                'question': question,
                'tags': QuizTag.objects.all(),
                'sources': QuizSource.objects.all(),
                'difficulty_choices': QuizQuestion.DIFFICULTY_CHOICES,
                'question_types': QuizQuestion.QUESTION_TYPES,
                'content_html': content_html,
                'explanation_html': explanation_html,
                'media': content_widget.media,
            })

        with transaction.atomic():
            # Resolve source
            source = None
            if source_name:
                source, _ = QuizSource.objects.get_or_create(name=source_name)
            elif source_id:
                source = QuizSource.objects.filter(id=source_id).first()

            if not question:
                question = QuizQuestion(created_by=request.user)

            question.content = content
            question.type = q_type
            question.difficulty = difficulty
            question.explanation = explanation
            question.source = source
            question.save()

            # Handle Tags
            question.tags.clear()
            for tag_val in tags_raw:
                if tag_val.isdigit():
                    t = QuizTag.objects.filter(id=int(tag_val)).first()
                    if t: question.tags.add(t)
                else:
                    slug = slugify(tag_val)
                    t, _ = QuizTag.objects.get_or_create(name=tag_val, defaults={'slug': slug})
                    question.tags.add(t)

            # Handle Options
            # Remove old options
            question.options.all().delete()

            if q_type == 'choice':
                # Expect labels A, B, C, D
                correct_label = request.POST.get('correct_choice')
                for label in ['A', 'B', 'C', 'D']:
                    opt_content = request.POST.get(f'option_{label}', '').strip()
                    if opt_content:
                        QuizOption.objects.create(
                            question=question,
                            label=label,
                            content=opt_content,
                            is_correct=(label == correct_label)
                        )
            elif q_type == 'tf':
                # Expect labels a, b, c, d
                for label in ['a', 'b', 'c', 'd']:
                    opt_content = request.POST.get(f'option_{label}', '').strip()
                    correct_val = (request.POST.get(f'correct_tf_{label}') == 'true') # 'true' means True (Đúng), 'false' means False (Sai)
                    if opt_content:
                        QuizOption.objects.create(
                            question=question,
                            label=label,
                            content=opt_content,
                            is_correct=correct_val
                        )

        return redirect('quiz_manage_dashboard')


class QuizQuestionDeleteView(View):
    def post(self, request, question_id):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền xóa câu hỏi.")

        question = get_object_or_404(QuizQuestion, id=question_id)
        if not request.user.is_superuser and question.created_by != request.user:
            return HttpResponseForbidden("Bạn không có quyền xóa câu hỏi này.")

        question.delete()
        return redirect('quiz_manage_dashboard')


class QuizSessionReviewView(View):
    def get(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        
        # Verify ownership
        if session.user:
            if session.user != request.user:
                return HttpResponseForbidden("Bạn không có quyền truy cập phiên luyện tập này.")
        else:
            if session.session_key != request.session.session_key:
                return HttpResponseForbidden("Bạn không có quyền truy cập phiên luyện tập này.")

        # Load all questions in order
        q_ids = session.questions
        questions_map = {q.id: q for q in QuizQuestion.objects.filter(id__in=q_ids).prefetch_related('options').select_related('source')}
        
        # Pair questions with user answers
        review_data = []
        for index, q_id in enumerate(q_ids):
            q = questions_map.get(q_id)
            if not q:
                continue
            
            user_ans = session.answers.get(str(q_id))
            
            # Grade it
            is_correct = False
            correct_answers = []
            correct_count = 0
            
            if q.type == 'choice':
                correct_opt = q.options.filter(is_correct=True).first()
                correct_label = correct_opt.label if correct_opt else 'A'
                correct_answers.append(correct_label)
                is_correct = (user_ans == correct_label)
            elif q.type == 'tf':
                # dict representing statement correctness
                correct_map = {opt.label: opt.is_correct for opt in q.options.all()}
                correct_answers = correct_map
                
                if isinstance(user_ans, dict):
                    correct_count = 0
                    for label, correct_val in correct_map.items():
                        if user_ans.get(label) == correct_val:
                            correct_count += 1
                    is_correct = (correct_count == len(correct_map))
            
            review_data.append({
                'index': index + 1,
                'question': q,
                'options': q.options.all(),
                'user_answer': user_ans,
                'is_answered': user_ans is not None and user_ans != '__skipped__',
                'is_skipped': user_ans == '__skipped__',
                'is_correct': is_correct,
                'correct_answers': correct_answers,
                'correct_count': correct_count,
            })

        context = {
            'title': f'Xem lại phiên luyện tập #{session.id}',
            'session': session,
            'review_data': review_data,
        }
        return render(request, 'quiz/session_review.html', context)


class QuizBulkImportView(View):
    def get(self, request):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền import câu hỏi.")
        
        context = {
            'title': 'Import câu hỏi hàng loạt',
        }
        return render(request, 'quiz/import.html', context)

    def post(self, request):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền import câu hỏi.")
        
        json_file = request.FILES.get('json_file')
        if json_file:
            try:
                json_data = json_file.read().decode('utf-8').strip()
            except Exception as e:
                return render(request, 'quiz/import.html', {
                    'title': 'Import câu hỏi hàng loạt',
                    'error': f'Không thể đọc tệp tin tải lên: {str(e)}'
                })
        else:
            json_data = request.POST.get('json_data', '').strip()

        if not json_data:
            return render(request, 'quiz/import.html', {
                'title': 'Import câu hỏi hàng loạt',
                'error': 'Vui lòng dán dữ liệu JSON hoặc tải lên tệp tin JSON.'
            })

        try:
            questions_list = json.loads(json_data)
        except json.JSONDecodeError as e:
            return render(request, 'quiz/import.html', {
                'title': 'Import câu hỏi hàng loạt',
                'error': f'Lỗi định dạng JSON: {str(e)}',
                'json_data': json_data
            })

        if not isinstance(questions_list, list):
            return render(request, 'quiz/import.html', {
                'title': 'Import câu hỏi hàng loạt',
                'error': 'Dữ liệu JSON phải là một danh sách (JSON Array) chứa các câu hỏi.',
                'json_data': json_data
            })

        created_count = 0
        error_logs = []

        with transaction.atomic():
            for index, q_data in enumerate(questions_list):
                try:
                    content = q_data.get('content', '').strip()
                    q_type = q_data.get('type', 'choice').strip()
                    difficulty = q_data.get('difficulty', 'easy').strip()
                    explanation = q_data.get('explanation', '').strip()
                    source_name = q_data.get('source', '').strip()
                    tags = q_data.get('tags', [])
                    options = q_data.get('options', [])

                    if not content:
                        error_logs.append(f"Mục #{index+1}: Thiếu nội dung câu hỏi ('content').")
                        continue

                    # Resolve source
                    source = None
                    if source_name:
                        source, _ = QuizSource.objects.get_or_create(name=source_name)

                    question = QuizQuestion.objects.create(
                        content=content,
                        type=q_type,
                        difficulty=difficulty,
                        explanation=explanation,
                        source=source,
                        created_by=request.user
                    )

                    # Handle Tags
                    for tag_name in tags:
                        tag_name = tag_name.strip()
                        if tag_name:
                            slug = slugify(tag_name)
                            t, _ = QuizTag.objects.get_or_create(name=tag_name, defaults={'slug': slug})
                            question.tags.add(t)

                    # Handle Options
                    for opt_data in options:
                        label = opt_data.get('label', '').strip()
                        opt_content = opt_data.get('content', '').strip()
                        is_correct = opt_data.get('is_correct', False)
                        
                        if label and opt_content:
                            QuizOption.objects.create(
                                question=question,
                                label=label,
                                content=opt_content,
                                is_correct=is_correct
                            )

                    created_count += 1
                except Exception as ex:
                    error_logs.append(f"Mục #{index+1}: Lỗi không xác định: {str(ex)}")

        if error_logs:
            return render(request, 'quiz/import.html', {
                'title': 'Import câu hỏi hàng loạt',
                'error': f"Đã import thành công {created_count} câu hỏi. Có {len(error_logs)} lỗi phát sinh.",
                'error_logs': error_logs,
                'json_data': json_data
            })

        return redirect('quiz_manage_dashboard')


class QuizExamsListView(View):
    def get(self, request):
        # Fetch all exams (sources with matching questions)
        sources = QuizSource.objects.annotate(total_questions=Count('questions')).filter(total_questions__gt=0)
        
        # Filtering
        source_type = request.GET.get('source_type') # school, dept, other, custom
        year = request.GET.get('year') # 2026, 2025, etc.
        status = request.GET.get('status') # done, not_done
        search_query = request.GET.get('q')
        sort = request.GET.get('sort', 'newest') # newest, oldest, highest, lowest
        
        import re
        exams = []
        for s in sources:
            first_q = s.questions.order_by('id').first()
            if not first_q:
                continue
            first_q_content = first_q.content
            clean_snippet = re.sub(r'!\[.*?\]\(.*?\)', '', first_q_content)
            clean_snippet = re.sub(r'\[.*?\]\(.*?\)', '', clean_snippet)
            clean_snippet = re.sub(r'#+\s+', '', clean_snippet)
            clean_snippet = clean_snippet.replace('\n', ' ').strip()
            snippet = clean_snippet[:150] + "..." if len(clean_snippet) > 150 else clean_snippet
            
            # Year
            year_match = re.search(r'\b(202\d|199\d)\b', s.name)
            s_year = year_match.group(1) if year_match else "2026"
            
            # Type
            s_name_lower = s.name.lower()
            if "sở" in s_name_lower:
                s_type_label = "Đề sở"
                s_type_key = "dept"
            elif any(x in s_name_lower for x in ["trường", "chuyên", "thpt"]):
                s_type_label = "Đề trường"
                s_type_key = "school"
            elif "tự tạo" in s_name_lower or "custom" in s_name_lower:
                s_type_label = "Tự tạo"
                s_type_key = "custom"
            else:
                s_type_label = "Đề khác"
                s_type_key = "other"
                
            tf_count = s.questions.filter(type='tf').count()
            
            # Fetch user history and best score
            if request.user.is_authenticated:
                sessions = QuizSession.objects.filter(user=request.user, completed=True)
            elif request.session.session_key:
                sessions = QuizSession.objects.filter(session_key=request.session.session_key, completed=True)
            else:
                sessions = []
            
            exam_sessions = [sess for sess in sessions if first_q.id in sess.questions]
            best_score = max(sess.score for sess in exam_sessions) if exam_sessions else None
            is_done = len(exam_sessions) > 0
            
            history = []
            for sess in exam_sessions:
                history.append({
                    'id': sess.id,
                    'score': round(sess.score, 2),
                    'date': sess.created_at.strftime('%H:%M %d/%m/%Y'),
                })
            
            exams.append({
                'id': s.id,
                'name': s.name,
                'total_questions': s.total_questions,
                'tf_count': tf_count,
                'snippet': snippet,
                'year': s_year,
                'type_key': s_type_key,
                'type_label': s_type_label,
                'best_score': round(best_score, 2) if best_score is not None else None,
                'is_done': is_done,
                'history': history,
                'created_at': first_q.created_at,
            })
            
        # Apply filters
        if source_type:
            exams = [e for e in exams if e['type_key'] == source_type]
        if year:
            exams = [e for e in exams if e['year'] == year]
        if status:
            if status == 'done':
                exams = [e for e in exams if e['is_done']]
            elif status == 'not_done':
                exams = [e for e in exams if not e['is_done']]
        if search_query:
            q_lower = search_query.lower()
            exams = [e for e in exams if q_lower in e['name'].lower()]
            
        # Apply sorting
        if sort == 'newest':
            exams.sort(key=lambda x: x['created_at'], reverse=True)
        elif sort == 'oldest':
            exams.sort(key=lambda x: x['created_at'])
        elif sort == 'highest':
            exams.sort(key=lambda x: x['best_score'] if x['best_score'] is not None else -1, reverse=True)
        elif sort == 'lowest':
            exams.sort(key=lambda x: x['best_score'] if x['best_score'] is not None else 999)

        total_exams = len(exams)

        context = {
            'title': 'Kho đề luyện thi tốt nghiệp THPT',
            'exams': exams,
            'total_exams': total_exams,
            'selected_source_type': source_type,
            'selected_year': year,
            'selected_status': status,
            'search_query': search_query,
            'selected_sort': sort,
        }
        return render(request, 'quiz/exams_list.html', context)


class QuizStartExamView(View):
    def post(self, request, exam_id):
        source = get_object_or_404(QuizSource, id=exam_id)
        
        duration_str = request.POST.get('duration', '45')
        orientation = request.POST.get('orientation', 'KHMT')
        
        try:
            duration = int(duration_str)
        except ValueError:
            duration = 45
            
        questions = QuizQuestion.objects.filter(source=source).order_by('id')
        question_ids = list(questions.values_list('id', flat=True))
        
        if not question_ids:
            return redirect('quiz_exams_list')
            
        if not request.session.session_key:
            request.session.create()
            
        meta = {
            'is_exam': True,
            'source_id': source.id,
            'source_name': source.name,
            'duration': duration,
            'time_left': duration * 60,
            'orientation': orientation,
        }
        
        session = QuizSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else None,
            questions=question_ids,
            answers={'__meta__': meta},
            current_index=0,
            completed=False,
            score=0.0
        )
        
        return redirect('quiz_exam_session', session_id=session.id)


class QuizExamSessionView(View):
    def get(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        
        if session.user:
            if session.user != request.user:
                return HttpResponseForbidden("Bạn không có quyền truy cập phiên thi này.")
        else:
            if session.session_key != request.session.session_key:
                return HttpResponseForbidden("Bạn không có quyền truy cập phiên thi này.")
                
        meta = session.answers.get('__meta__', {})
        if not meta or not meta.get('is_exam'):
            return redirect('quiz_session_detail', session_id=session.id)
            
        if session.completed:
            return redirect('quiz_exam_review', session_id=session.id)
            
        q_ids = session.questions
        questions = QuizQuestion.objects.filter(id__in=q_ids).prefetch_related('options').select_related('source')
        q_map = {q.id: q for q in questions}
        ordered_questions = [q_map[qid] for qid in q_ids if qid in q_map]
        
        part1 = []
        part2 = []
        
        for index, q in enumerate(ordered_questions):
            q_info = {
                'id': q.id,
                'index': index + 1,
                'content': q.content,
                'type': q.type,
                'difficulty': q.difficulty,
                'explanation': q.explanation,
                'options': q.options.all(),
                'source_name': q.source.name if q.source else '',
                'orientation': 'Common',
            }
            
            q_tags = [t.slug for t in q.tags.all()]
            if 'khmt' in q_tags:
                q_info['orientation'] = 'KHMT'
            elif 'thud' in q_tags:
                q_info['orientation'] = 'THUD'
                
            user_ans = session.answers.get(str(q.id))
            q_info['user_answer'] = user_ans
            q_info['is_answered'] = user_ans is not None
            
            if q.type == 'choice':
                part1.append(q_info)
            else:
                part2.append(q_info)
                
        time_left = meta.get('time_left', 2700)
        minutes = time_left // 60
        seconds = time_left % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        context = {
            'title': meta.get('source_name', 'Thi trắc nghiệm'),
            'session': session,
            'meta': meta,
            'part1': part1,
            'part2': part2,
            'time_left_seconds': time_left,
            'time_left_str': time_str,
            'selected_orientation': meta.get('orientation', 'KHMT'),
        }
        return render(request, 'quiz/exam_session.html', context)


class QuizExamActionView(View):
    def post(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        
        if session.user and session.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        if not session.user and session.session_key != request.session.session_key:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        action = request.POST.get('action')
        
        if action == 'tick_timer':
            time_left = request.POST.get('time_left')
            if time_left is not None:
                try:
                    tl = int(time_left)
                    if '__meta__' in session.answers:
                        session.answers['__meta__']['time_left'] = max(0, tl)
                        session.save()
                except ValueError:
                    pass
            return JsonResponse({'success': True})
            
        if action == 'save_answer':
            qid = request.POST.get('qid')
            q_type = request.POST.get('q_type', 'choice')
            
            if not qid:
                return JsonResponse({'error': 'Missing qid'}, status=400)
                
            if q_type == 'choice':
                val = request.POST.get('answer')
                if val:
                    session.answers[str(qid)] = val
                else:
                    session.answers.pop(str(qid), None)
            else:
                curr_ans = session.answers.get(str(qid))
                if not isinstance(curr_ans, dict):
                    curr_ans = {}
                for lbl in ['a', 'b', 'c', 'd']:
                    val = request.POST.get(f'tf_{lbl}')
                    if val == 'true':
                        curr_ans[lbl] = True
                    elif val == 'false':
                        curr_ans[lbl] = False
                session.answers[str(qid)] = curr_ans
                
            session.save()
            return JsonResponse({'success': True})
            
        if action == 'change_orientation':
            orientation = request.POST.get('orientation')
            if orientation in ['KHMT', 'THUD']:
                if '__meta__' in session.answers:
                    session.answers['__meta__']['orientation'] = orientation
                    session.save()
                    return JsonResponse({'success': True})
            return JsonResponse({'error': 'Invalid orientation'}, status=400)
            
        if action == 'submit_exam':
            meta = session.answers.get('__meta__', {})
            orientation = meta.get('orientation', 'KHMT')
            
            q_ids = session.questions
            questions = QuizQuestion.objects.filter(id__in=q_ids).prefetch_related('options')
            q_map = {q.id: q for q in questions}
            
            graded_part1 = []
            graded_part2 = []
            
            for q_id in q_ids:
                q = q_map.get(q_id)
                if not q:
                    continue
                q_tags = [t.slug for t in q.tags.all()]
                
                if 'khmt' in q_tags and orientation != 'KHMT':
                    continue
                if 'thud' in q_tags and orientation != 'THUD':
                    continue
                    
                if q.type == 'choice':
                    graded_part1.append(q)
                else:
                    graded_part2.append(q)
            
            part1_correct = 0
            for q in graded_part1:
                ans = session.answers.get(str(q.id))
                correct_opt = q.options.filter(is_correct=True).first()
                correct_label = correct_opt.label if correct_opt else 'A'
                if ans == correct_label:
                    part1_correct += 1
            
            part1_score = part1_correct * 0.25
            
            part2_score = 0.0
            for q in graded_part2:
                ans = session.answers.get(str(q.id))
                if not isinstance(ans, dict):
                    continue
                    
                correct_map = {opt.label: opt.is_correct for opt in q.options.all()}
                correct_count = 0
                for lbl, correct_val in correct_map.items():
                    if ans.get(lbl) == correct_val:
                        correct_count += 1
                        
                if correct_count == 1:
                    part2_score += 0.1
                elif correct_count == 2:
                    part2_score += 0.25
                elif correct_count == 3:
                    part2_score += 0.5
                elif correct_count == 4:
                    part2_score += 1.0
            
            total_score = min(10.0, part1_score + part2_score)
            
            session.score = total_score
            session.completed = True
            session.save()
            
            return JsonResponse({
                'success': True,
                'redirect': request.build_absolute_uri(redirect('quiz_exam_review', session_id=session.id).url)
            })
            
        return JsonResponse({'error': 'Invalid action'}, status=400)


class QuizExamReviewView(View):
    def get(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        
        if session.user:
            if session.user != request.user:
                return HttpResponseForbidden("Bạn không có quyền truy cập kết quả thi này.")
        else:
            if session.session_key != request.session.session_key:
                return HttpResponseForbidden("Bạn không có quyền truy cập kết quả thi này.")
                
        meta = session.answers.get('__meta__', {})
        if not meta or not meta.get('is_exam'):
            return redirect('quiz_session_review', session_id=session.id)
            
        orientation = meta.get('orientation', 'KHMT')
        
        q_ids = session.questions
        questions = QuizQuestion.objects.filter(id__in=q_ids).prefetch_related('options').select_related('source')
        q_map = {q.id: q for q in questions}
        ordered_questions = [q_map[qid] for qid in q_ids if qid in q_map]
        
        review_part1 = []
        review_part2 = []
        
        part1_correct = 0
        part1_total = 0
        part2_correct_full = 0
        part2_total = 0
        
        for index, q in enumerate(ordered_questions):
            q_tags = [t.slug for t in q.tags.all()]
            q_orientation = 'Common'
            if 'khmt' in q_tags:
                q_orientation = 'KHMT'
            elif 'thud' in q_tags:
                q_orientation = 'THUD'
                
            is_graded = True
            if q_orientation == 'KHMT' and orientation != 'KHMT':
                is_graded = False
            elif q_orientation == 'THUD' and orientation != 'THUD':
                is_graded = False
                
            user_ans = session.answers.get(str(q.id))
            
            is_correct = False
            correct_answers = {}
            correct_details = {}
            correct_count = 0
            
            if q.type == 'choice':
                correct_opt = q.options.filter(is_correct=True).first()
                correct_label = correct_opt.label if correct_opt else 'A'
                correct_answers = [correct_label]
                is_correct = (user_ans == correct_label)
                if is_graded:
                    part1_total += 1
                    if is_correct:
                        part1_correct += 1
            else:
                correct_map = {opt.label: opt.is_correct for opt in q.options.all()}
                correct_answers = correct_map
                if isinstance(user_ans, dict):
                    for lbl, correct_val in correct_map.items():
                        is_stmt_correct = (user_ans.get(lbl) == correct_val)
                        correct_details[lbl] = is_stmt_correct
                        if is_stmt_correct:
                            correct_count += 1
                    is_correct = (correct_count == len(correct_map))
                else:
                    correct_details = {lbl: False for lbl in correct_map}
                
                if is_graded:
                    part2_total += 1
                    if is_correct:
                        part2_correct_full += 1
                        
            q_info = {
                'index': index + 1,
                'question': q,
                'options': q.options.all(),
                'user_answer': user_ans,
                'is_answered': user_ans is not None and user_ans != '__skipped__',
                'is_skipped': user_ans == '__skipped__' or user_ans is None,
                'is_correct': is_correct,
                'correct_answers': correct_answers,
                'correct_details': correct_details,
                'correct_count': correct_count,
                'orientation': q_orientation,
                'is_graded': is_graded,
            }
            
            if q.type == 'choice':
                review_part1.append(q_info)
            else:
                review_part2.append(q_info)
                
        attempt_date = session.created_at.strftime('%H:%M:%S %d/%m/%Y')
        
        context = {
            'title': f"Kết quả: {meta.get('source_name', 'Thi trắc nghiệm')}",
            'session': session,
            'meta': meta,
            'orientation': orientation,
            'review_part1': review_part1,
            'review_part2': review_part2,
            'part1_correct': part1_correct,
            'part1_total': part1_total,
            'part2_correct_full': part2_correct_full,
            'part2_total': part2_total,
            'attempt_date': attempt_date,
        }
        return render(request, 'quiz/exam_review.html', context)


