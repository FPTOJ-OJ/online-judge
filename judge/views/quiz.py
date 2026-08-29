import json
import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, Http404, HttpResponseForbidden, HttpResponse
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext as _, gettext_lazy as _l
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Q, Count
import random

from judge.models.quiz import QuizTag, QuizSource, QuizQuestion, QuizOption, QuizSession
from judge.models.profile import Organization
from judge.jinja2.markdown import markdown
from judge.widgets.martor import MartorWidget
from judge import event_poster as event


class QuizSessionAccessMixin(AccessMixin):
    """Mixin that allows access if user owns the session (by user FK or session_key)."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.session.session_key:
            return super().dispatch(request, *args, **kwargs)
        return self.handle_no_permission()

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
            clean_snippet = re.sub(r'```.*?```', '', first_q_content, flags=re.DOTALL)
            clean_snippet = re.sub(r'`[^`\n]+`', '', clean_snippet)
            clean_snippet = re.sub(r'!\[.*?\]\(.*?\)', '', clean_snippet)
            clean_snippet = re.sub(r'\[.*?\]\(.*?\)', '', clean_snippet)
            clean_snippet = re.sub(r'#+\s+', '', clean_snippet)
            clean_snippet = clean_snippet.replace('\n', ' ').strip()
            clean_snippet = re.sub(r'\s+', ' ', clean_snippet)
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
        if not request.user.is_authenticated:
            from django.urls import reverse
            return redirect(f'{reverse("auth_login")}?next={request.get_full_path()}')
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


class QuizSessionDetailView(QuizSessionAccessMixin, View):
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
            'score': round(session.score, 2),
        }
        return render(request, 'quiz/session.html', context)


class QuizSessionActionView(QuizSessionAccessMixin, View):
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


class QuizSessionReviewView(QuizSessionAccessMixin, View):
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


def can_access_exam(user, source):
    """Check if a user can view/access an exam based on its settings."""
    if not source.is_visible:
        return False
    if source.require_login and not user.is_authenticated:
        return False
    if user.is_authenticated and is_teacher(user):
        return True
    if not source.is_currently_open():
        return False
    if source.target_classes.exists():
        if not user.is_authenticated or not hasattr(user, 'profile'):
            return False
        user_class_ids = set(user.profile.classes.values_list('id', flat=True))
        target_ids = set(source.target_classes.values_list('id', flat=True))
        if not (user_class_ids & target_ids):
            return False
    if source.is_organization_only:
        if not user.is_authenticated:
            return False
        if not hasattr(user, 'profile'):
            return False
        org_ids = list(source.organizations.values_list('id', flat=True))
        if org_ids:
            user_orgs = user.profile.organizations.all()
            user_org_ids = set(user_orgs.values_list('id', flat=True))
            if not any(oid in user_org_ids for oid in org_ids):
                return False
    return True


class QuizExamsListView(View):
    def get(self, request):
        # Fetch visible exams (sources with matching questions)
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
            # Permission check
            if not can_access_exam(request.user, s):
                if not request.user.is_staff and not request.user.is_superuser and not is_teacher(request.user):
                    continue

            first_q = s.questions.order_by('id').first()
            if not first_q:
                continue
            first_q_content = first_q.content
            clean_snippet = re.sub(r'```.*?```', '', first_q_content, flags=re.DOTALL)
            clean_snippet = re.sub(r'`[^`\n]+`', '', clean_snippet)
            clean_snippet = re.sub(r'!\[.*?\]\(.*?\)', '', clean_snippet)
            clean_snippet = re.sub(r'\[.*?\]\(.*?\)', '', clean_snippet)
            clean_snippet = re.sub(r'#+\s+', '', clean_snippet)
            clean_snippet = clean_snippet.replace('\n', ' ').strip()
            clean_snippet = re.sub(r'\s+', ' ', clean_snippet)
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
                'is_locked': s.is_locked,
                'is_featured': s.is_featured,
                'require_login': s.require_login,
                'is_organization_only': s.is_organization_only,
                'description': s.description,
                'default_duration': s.default_duration,
                'can_access': can_access_exam(request.user, s),
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
            'is_teacher': is_teacher(request.user),
        }
        return render(request, 'quiz/exams_list.html', context)


class QuizStartExamView(View):
    def post(self, request, exam_id):
        if not request.user.is_authenticated:
            from django.urls import reverse
            return redirect(f'{reverse("auth_login")}?next={request.get_full_path()}')
        source = get_object_or_404(QuizSource, id=exam_id)
        
        if source.is_locked and not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'Đề thi này đã bị khóa bởi quản trị viên.')
            return redirect('quiz_exams_list')

        if not can_access_exam(request.user, source) and not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'Bạn không có quyền truy cập đề thi này (chỉ dành cho học sinh trong tổ chức/lớp được chỉ định).')
            return redirect('quiz_exams_list')
        
        duration_str = request.POST.get('duration', str(source.default_duration))
        orientation = request.POST.get('orientation') or request.GET.get('orientation', 'ALL')
        show_score_per_question = request.POST.get('show_score_per_question') == '1'
        show_feedback = request.POST.get('show_feedback') == '1'
        enable_scratchpad = request.POST.get('enable_scratchpad', '1') == '1'
        
        try:
            duration = int(duration_str)
        except ValueError:
            duration = source.default_duration
            
        questions = QuizQuestion.objects.filter(source=source).order_by('id')
        question_ids = list(questions.values_list('id', flat=True))
        
        if not question_ids:
            return redirect('quiz_exams_list')

        if source.shuffle_questions:
            import random
            random.shuffle(question_ids)
            
        if not request.session.session_key:
            request.session.create()
            
        meta = {
            'is_exam': True,
            'source_id': source.id,
            'source_name': source.name,
            'duration': duration,
            'time_left': duration * 60,
            'orientation': orientation,
            'show_score_per_question': show_score_per_question,
            'show_feedback': show_feedback,
            'enable_scratchpad': enable_scratchpad,
            'is_strict_anti_cheat': source.is_strict_anti_cheat,
            'max_violations': source.max_violations,
            'violation_count': 0,
            'violations_log': [],
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


def grade_exam_session(session):
    meta = session.answers.get('__meta__', {})
    orientation = meta.get('orientation', 'ALL')
    
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
        
        if 'khmt' in q_tags and orientation not in ('KHMT', 'ALL'):
            continue
        if 'thud' in q_tags and orientation not in ('THUD', 'ALL'):
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
    session.score = round(total_score, 2)
    session.completed = True
    session.save()
    return total_score


class QuizExamSessionView(LoginRequiredMixin, View):
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
        
        choice_count = 0
        tf_count = 0
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
                choice_count += 1
                q_info['display_index'] = choice_count
                part1.append(q_info)
            else:
                tf_count += 1
                q_info['display_index'] = tf_count
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
            'show_score_per_question': meta.get('show_score_per_question', False),
            'show_feedback': meta.get('show_feedback', False),
            'enable_scratchpad': meta.get('enable_scratchpad', True),
            'is_strict_anti_cheat': meta.get('is_strict_anti_cheat', False),
            'max_violations': meta.get('max_violations', 5),
            'violation_count': meta.get('violation_count', 0),
            'last_msg': event.last() if hasattr(event, 'last') else 0,
        }

        # Broadcast student joined room event
        exam_id = meta.get('source_id')
        if exam_id:
            try:
                event.post(f"quiz_exam_{exam_id}", {
                    'type': 'student_joined',
                    'session_id': session.id,
                    'username': request.user.username if request.user.is_authenticated else 'Khách',
                    'display_name': (request.user.profile.display_name if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.display_name else (request.user.username if request.user.is_authenticated else 'Khách')),
                })
            except Exception:
                pass

        return render(request, 'quiz/exam_session.html', context)


class QuizExamActionView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        
        if session.user and session.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        if not session.user and session.session_key != request.session.session_key:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        action = request.POST.get('action')

        if session.completed:
            if action == 'submit_exam':
                from django.urls import reverse
                return JsonResponse({
                    'success': True,
                    'redirect': request.build_absolute_uri(reverse('quiz_exam_review', kwargs={'session_id': session.id}))
                })
            return JsonResponse({'error': 'Exam session already completed.'}, status=400)
        
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
            meta = session.answers.get('__meta__', {})
            return JsonResponse({
                'success': True,
                'is_paused': meta.get('is_paused', False),
                'proctor_warning': meta.get('proctor_warning'),
                'extra_time_added': meta.get('extra_time_added', 0),
                'time_left': meta.get('time_left', 0),
                'force_submitted': meta.get('force_submitted_by_teacher', False) or session.completed,
            })

        if action == 'ack_warning':
            if '__meta__' in session.answers:
                session.answers['__meta__'].pop('proctor_warning', None)
                session.save()
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
            meta = session.answers.get('__meta__', {})

            # Broadcast progress update via WebSocket
            exam_id = meta.get('source_id')
            if exam_id:
                try:
                    answered_keys = [k for k in session.answers.keys() if k != '__meta__']
                    total_q = len(session.questions) if session.questions else 0
                    pct = round((len(answered_keys) / total_q) * 100) if total_q > 0 else 0
                    event.post(f"quiz_exam_{exam_id}", {
                        'type': 'progress_update',
                        'session_id': session.id,
                        'username': session.user.username if session.user else 'Khách',
                        'display_name': (session.user.profile.display_name if session.user and hasattr(session.user, 'profile') and session.user.profile.display_name else (session.user.username if session.user else 'Khách')),
                        'answered_count': len(answered_keys),
                        'total_questions': total_q,
                        'progress_pct': pct,
                        'time_left': meta.get('time_left', 0),
                    })
                except Exception:
                    pass

            return JsonResponse({
                'success': True,
                'is_paused': meta.get('is_paused', False),
                'proctor_warning': meta.get('proctor_warning'),
                'extra_time_added': meta.get('extra_time_added', 0),
                'time_left': meta.get('time_left', 0),
                'force_submitted': meta.get('force_submitted_by_teacher', False) or session.completed,
            })
            
        if action == 'change_orientation':
            new_orient = request.POST.get('orientation', 'KHMT').upper()
            if new_orient in ('KHMT', 'THUD', 'ALL'):
                meta = session.answers.setdefault('__meta__', {})
                meta['orientation'] = new_orient
                session.save()
                return JsonResponse({'success': True, 'orientation': new_orient})
            return JsonResponse({'error': 'Invalid orientation'}, status=400)
            
        if action == 'log_violation':
            v_type = request.POST.get('v_type', 'unknown')
            v_detail = request.POST.get('v_detail', '')

            meta = session.answers.setdefault('__meta__', {})
            violation_count = meta.get('violation_count', 0) + 1
            meta['violation_count'] = violation_count

            violations_log = meta.setdefault('violations_log', [])
            violations_log.append({
                'time': timezone.now().strftime('%H:%M:%S'),
                'type': v_type,
                'detail': v_detail,
                'count': violation_count,
            })

            is_strict = meta.get('is_strict_anti_cheat', False)
            max_violations = meta.get('max_violations', 5)

            force_submitted = False
            if is_strict and max_violations > 0 and violation_count >= max_violations:
                grade_exam_session(session)
                force_submitted = True
            else:
                session.save()

            # Broadcast violation via WebSocket
            exam_id = meta.get('source_id')
            if exam_id:
                try:
                    event.post(f"quiz_exam_{exam_id}", {
                        'type': 'violation',
                        'session_id': session.id,
                        'username': session.user.username if session.user else 'Khách',
                        'display_name': (session.user.profile.display_name if session.user and hasattr(session.user, 'profile') and session.user.profile.display_name else (session.user.username if session.user else 'Khách')),
                        'violation_count': violation_count,
                        'latest_violation': {
                            'time': timezone.now().strftime('%H:%M:%S'),
                            'type': v_type,
                            'detail': v_detail,
                            'count': violation_count,
                        },
                        'force_submitted': force_submitted,
                    })
                except Exception:
                    pass

            return JsonResponse({
                'success': True,
                'violation_count': violation_count,
                'max_violations': max_violations,
                'force_submitted': force_submitted,
                'redirect': request.build_absolute_uri(redirect('quiz_exam_review', session_id=session.id).url) if force_submitted else None,
            })
            
        if action == 'submit_exam':
            grade_exam_session(session)
            meta = session.answers.get('__meta__', {})
            exam_id = meta.get('source_id')
            if exam_id:
                try:
                    event.post(f"quiz_exam_{exam_id}", {
                        'type': 'submission',
                        'session_id': session.id,
                        'username': session.user.username if session.user else 'Khách',
                        'display_name': (session.user.profile.display_name if session.user and hasattr(session.user, 'profile') and session.user.profile.display_name else (session.user.username if session.user else 'Khách')),
                        'score': round(session.score, 2),
                    })
                except Exception:
                    pass

            return JsonResponse({
                'success': True,
                'redirect': request.build_absolute_uri(redirect('quiz_exam_review', session_id=session.id).url)
            })
            
        return JsonResponse({'error': 'Invalid action'}, status=400)


class QuizExamReviewView(LoginRequiredMixin, View):
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
        
        choice_count = 0
        tf_count = 0
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
                choice_count += 1
                q_info['display_index'] = choice_count
                review_part1.append(q_info)
            else:
                tf_count += 1
                q_info['display_index'] = tf_count
                review_part2.append(q_info)
                
        attempt_date = session.created_at.strftime('%H:%M:%S %d/%m/%Y')
        duration_min = meta.get('duration', 45)
        duration_seconds = duration_min * 60
        time_left = meta.get('time_left', 0)
        time_spent_seconds = max(0, duration_seconds - time_left)
        time_spent_min = time_spent_seconds // 60
        time_spent_sec = time_spent_seconds % 60
        time_spent_str = f"{time_spent_min} phút {time_spent_sec:02d} giây"
        
        part1_score = round(part1_correct * 0.25, 2)
        part2_score = max(0.0, round(float(session.score or 0) - part1_score, 2))
        total_questions_graded = part1_total + part2_total
        accuracy_pct = round(((part1_correct + part2_correct_full) / max(1, total_questions_graded)) * 100) if total_questions_graded > 0 else 0
        
        context = {
            'title': f"Kết quả: {meta.get('source_name', 'Thi trắc nghiệm')}",
            'session': session,
            'meta': meta,
            'orientation': orientation,
            'review_part1': review_part1,
            'review_part2': review_part2,
            'part1_correct': part1_correct,
            'part1_total': part1_total,
            'part1_score': part1_score,
            'part2_correct_full': part2_correct_full,
            'part2_total': part2_total,
            'part2_score': part2_score,
            'total_score': session.score,
            'accuracy_pct': accuracy_pct,
            'duration_min': duration_min,
            'time_spent_str': time_spent_str,
            'attempt_date': attempt_date,
            'violation_count': meta.get('violation_count', 0),
            'violations_log': meta.get('violations_log', []),
            'is_strict_anti_cheat': meta.get('is_strict_anti_cheat', False),
            'force_submitted_by_teacher': meta.get('force_submitted_by_teacher', False),
            'force_submitted_by_cheat': meta.get('force_submitted_by_cheat', False),
        }
        return render(request, 'quiz/exam_review.html', context)


class QuizExamManageView(View):
    """List all exams for management by teachers/admin."""
    def get(self, request):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền truy cập trang quản lý đề thi.")

        # Superusers see all; teachers see their own
        if request.user.is_superuser:
            exams = QuizSource.objects.annotate(total_questions=Count('questions')).prefetch_related('target_classes').order_by('-created_at')
        else:
            exams = QuizSource.objects.filter(
                Q(created_by=request.user) | Q(created_by__isnull=True)
            ).annotate(total_questions=Count('questions')).prefetch_related('target_classes').order_by('-created_at')

        from judge.models import Class
        if request.user.is_superuser:
            teacher_classes = Class.objects.filter(is_active=True).order_by('name')
        else:
            teacher_classes = Class.objects.filter(created_by=request.user, is_active=True).order_by('name')

        context = {
            'title': 'Quản lý đề thi trắc nghiệm',
            'exams': exams,
            'teacher_classes': teacher_classes,
        }
        return render(request, 'quiz/manage_exams.html', context)


class QuizExamAssignBulkClassesView(View):
    """Assign an exam to multiple classes from the Exam Repository."""
    def post(self, request, exam_id):
        if not is_teacher(request.user):
            return JsonResponse({'success': False, 'error': _('Không có quyền.')}, status=403)
        exam = get_object_or_404(QuizSource, id=exam_id)
        from judge.models import Class
        class_ids = request.POST.getlist('class_ids')
        if request.user.is_superuser:
            available_classes = Class.objects.filter(is_active=True)
        else:
            available_classes = Class.objects.filter(created_by=request.user, is_active=True)
        
        target_classes = available_classes.filter(id__in=class_ids)
        exam.target_classes.set(target_classes)
        return JsonResponse({
            'success': True,
            'assigned_count': target_classes.count(),
            'message': _('Đã phân công đề thi "%s" cho %d lớp học.') % (exam.name, target_classes.count())
        })


class QuizExamCreateEditView(View):
    """Create or edit an exam (QuizSource)."""
    def get(self, request, exam_id=None):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền quản lý đề thi.")

        exam = None
        if exam_id:
            exam = get_object_or_404(QuizSource, id=exam_id)
            if not request.user.is_superuser and exam.created_by not in (None, request.user):
                return HttpResponseForbidden("Bạn không có quyền chỉnh sửa đề thi này.")

        organizations = Organization.objects.all() if request.user.is_superuser else (
            request.user.profile.admin_of.all() if hasattr(request.user, 'profile') else []
        )

        from judge.models import Class
        if request.user.is_superuser:
            available_classes = Class.objects.all()
        elif hasattr(request.user, 'profile'):
            admin_org_ids = request.user.profile.admin_of.values_list('id', flat=True)
            available_classes = Class.objects.filter(Q(organization_id__in=admin_org_ids) | Q(admins=request.user.profile)).distinct()
        else:
            available_classes = Class.objects.none()

        context = {
            'title': 'Sửa đề thi' if exam else 'Thêm đề thi mới',
            'exam': exam,
            'organizations': organizations,
            'classes': available_classes,
        }
        return render(request, 'quiz/edit_exam.html', context)

    def post(self, request, exam_id=None):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền quản lý đề thi.")

        exam = None
        if exam_id:
            exam = get_object_or_404(QuizSource, id=exam_id)
            if not request.user.is_superuser and exam.created_by not in (None, request.user):
                return HttpResponseForbidden("Bạn không có quyền chỉnh sửa đề thi này.")

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        default_duration = request.POST.get('default_duration', '45')
        is_visible = request.POST.get('is_visible') == 'on'
        require_login = request.POST.get('require_login') == 'on'
        is_locked = request.POST.get('is_locked') == 'on'
        shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        shuffle_options = request.POST.get('shuffle_options') == 'on'

        if not name:
            return render(request, 'quiz/edit_exam.html', {
                'error': 'Tên đề thi không được để trống.',
                'exam': exam,
                'title': 'Sửa đề thi' if exam else 'Thêm đề thi mới',
            })

        try:
            default_duration = int(default_duration)
            if default_duration < 1:
                default_duration = 45
        except ValueError:
            default_duration = 45

        with transaction.atomic():
            if not exam:
                exam = QuizSource(created_by=request.user)

            exam.name = name
            exam.description = description
            exam.default_duration = default_duration
            exam.is_visible = is_visible
            exam.require_login = require_login
            exam.is_locked = is_locked
            exam.shuffle_questions = shuffle_questions
            exam.shuffle_options = shuffle_options
            exam.save()

        return redirect('quiz_exam_manage')


class QuizExamDeleteView(View):
    """Delete an exam (QuizSource)."""
    def post(self, request, exam_id):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền xóa đề thi.")

        exam = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and exam.created_by not in (None, request.user):
            return HttpResponseForbidden("Bạn không có quyền xóa đề thi này.")

        name = exam.name
        exam.delete()
        messages.success(request, f'Đã xóa đề thi "{name}".')
        return redirect('quiz_exam_manage')


class QuizExamManageQuestionsView(View):
    """View and manage questions within an exam."""
    def get(self, request, exam_id):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền quản lý đề thi.")

        source = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and source.created_by not in (None, request.user):
            return HttpResponseForbidden("Bạn không có quyền quản lý đề thi này.")

        questions = QuizQuestion.objects.filter(source=source).prefetch_related('tags').order_by('id')

        context = {
            'title': f'Câu hỏi trong đề: {source.name}',
            'source': source,
            'questions': questions,
        }
        return render(request, 'quiz/manage_exam_questions.html', context)


class QuizExamAnalyticsView(View):
    """Analytics and detailed statistics dashboard for an exam with Organization/Class filtering."""
    def get(self, request, exam_id):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền xem phân tích đề thi.")

        exam = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and exam.created_by not in (None, request.user):
            return HttpResponseForbidden("Bạn không có quyền xem phân tích đề thi này.")

        filter_org_id = request.GET.get('org_id')
        filter_class_id = request.GET.get('class_id')

        all_sessions = QuizSession.objects.filter(
            completed=True,
            answers__has_key='__meta__'
        ).select_related('user__profile').prefetch_related(
            'user__profile__organizations',
            'user__profile__classes__organization'
        ).order_by('-created_at')

        raw_exam_sessions = [
            s for s in all_sessions 
            if s.answers.get('__meta__', {}).get('source_id') == exam.id
        ]

        # Extract available organizations and classes from attempts for filter dropdown
        available_org_map = {}
        available_class_map = {}
        for s in raw_exam_sessions:
            if s.user and hasattr(s.user, 'profile'):
                for org in s.user.profile.organizations.all():
                    available_org_map[org.id] = org.short_name or org.name
                for cls in s.user.profile.classes.all():
                    org_label = cls.organization.short_name or cls.organization.name
                    available_class_map[cls.id] = f"{cls.name} ({org_label})"

        available_orgs = [{'id': k, 'name': v} for k, v in available_org_map.items()]
        available_classes = [{'id': k, 'name': v} for k, v in available_class_map.items()]

        # Filter by selected org or class
        exam_sessions = []
        for s in raw_exam_sessions:
            if filter_org_id:
                try:
                    f_oid = int(filter_org_id)
                    if not s.user or not hasattr(s.user, 'profile') or not s.user.profile.organizations.filter(id=f_oid).exists():
                        continue
                except ValueError:
                    pass

            if filter_class_id:
                try:
                    f_cid = int(filter_class_id)
                    if not s.user or not hasattr(s.user, 'profile') or not s.user.profile.classes.filter(id=f_cid).exists():
                        continue
                except ValueError:
                    pass

            exam_sessions.append(s)

        total_attempts = len(exam_sessions)
        unique_users = len(set(s.user_id for s in exam_sessions if s.user_id))

        scores = [s.score for s in exam_sessions]
        avg_score = round(sum(scores) / total_attempts, 2) if total_attempts > 0 else 0.0
        max_score = max(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0

        sorted_scores = sorted(scores)
        if total_attempts > 0:
            mid = total_attempts // 2
            median_score = sorted_scores[mid] if total_attempts % 2 != 0 else round((sorted_scores[mid - 1] + sorted_scores[mid]) / 2.0, 2)
        else:
            median_score = 0.0

        buckets = {
            '< 5.0': 0,
            '5.0 - 6.4': 0,
            '6.5 - 7.9': 0,
            '8.0 - 8.9': 0,
            '9.0 - 10.0': 0,
        }
        for sc in scores:
            if sc < 5.0:
                buckets['< 5.0'] += 1
            elif sc < 6.5:
                buckets['5.0 - 6.4'] += 1
            elif sc < 8.0:
                buckets['6.5 - 7.9'] += 1
            elif sc < 9.0:
                buckets['8.0 - 8.9'] += 1
            else:
                buckets['9.0 - 10.0'] += 1

        bucket_data = []
        for label, count in buckets.items():
            pct = round(count / total_attempts * 100, 1) if total_attempts > 0 else 0
            bucket_data.append({
                'label': label,
                'count': count,
                'pct': pct,
            })

        total_time_seconds = 0
        total_violations = 0
        sessions_with_violation = 0

        student_attempts = []
        for s in exam_sessions:
            meta = s.answers.get('__meta__', {})
            duration = meta.get('duration', exam.default_duration)
            time_left = meta.get('time_left', 0)
            time_spent_sec = max(0, duration * 60 - time_left)
            total_time_seconds += time_spent_sec
            
            v_count = meta.get('violation_count', 0)
            total_violations += v_count
            if v_count > 0:
                sessions_with_violation += 1
                
            org_names = []
            class_names = []
            if s.user and hasattr(s.user, 'profile'):
                org_names = [org.short_name or org.name for org in s.user.profile.organizations.all()]
                class_names = [cls.name for cls in s.user.profile.classes.all()]

            student_attempts.append({
                'id': s.id,
                'username': s.user.username if s.user else 'Khách',
                'display_name': s.user.profile.display_name if s.user and hasattr(s.user, 'profile') else 'Khách',
                'organizations': org_names,
                'classes': class_names,
                'score': round(s.score, 2),
                'date': s.created_at.strftime('%H:%M %d/%m/%Y'),
                'time_spent': f"{time_spent_sec // 60}m {time_spent_sec % 60}s",
                'violation_count': v_count,
                'violations_log': meta.get('violations_log', []),
            })

        avg_time_minutes = round((total_time_seconds / total_attempts) / 60, 1) if total_attempts > 0 else 0.0
        violation_rate = round(sessions_with_violation / total_attempts * 100, 1) if total_attempts > 0 else 0.0

        questions = QuizQuestion.objects.filter(source=exam).prefetch_related('options', 'tags').order_by('id')
        question_stats = []

        for idx, q in enumerate(questions):
            total_q_answers = 0
            correct_q_answers = 0
            options_count = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'skipped': 0}
            tf_part_correct = {'a': 0, 'b': 0, 'c': 0, 'd': 0}
            
            if q.type == 'choice':
                correct_opt = q.options.filter(is_correct=True).first()
                correct_label = correct_opt.label if correct_opt else 'A'
            else:
                correct_tf_map = {opt.label: opt.is_correct for opt in q.options.all()}

            for s in exam_sessions:
                if str(q.id) in s.answers:
                    total_q_answers += 1
                    u_ans = s.answers[str(q.id)]
                    if q.type == 'choice':
                        if u_ans in options_count:
                            options_count[u_ans] += 1
                        if u_ans == correct_label:
                            correct_q_answers += 1
                    elif q.type == 'tf' and isinstance(u_ans, dict):
                        is_all = True
                        for lbl, c_val in correct_tf_map.items():
                            if u_ans.get(lbl) == c_val:
                                tf_part_correct[lbl] += 1
                            else:
                                is_all = False
                        if is_all:
                            correct_q_answers += 1
                else:
                    options_count['skipped'] += 1

            acc_rate = round(correct_q_answers / total_attempts * 100, 1) if total_attempts > 0 else 0.0

            q_stat = {
                'id': q.id,
                'index': idx + 1,
                'type': q.type,
                'difficulty': q.difficulty,
                'content': q.content,
                'tags': [t.name for t in q.tags.all()],
                'accuracy': acc_rate,
                'total_answers': total_q_answers,
                'options_count': options_count,
                'tf_part_correct': tf_part_correct,
            }
            question_stats.append(q_stat)

        weakest_questions = sorted(question_stats, key=lambda x: x['accuracy'])[:5] if question_stats else []

        # Calculate accuracy by topic / tag
        tag_data = {}
        for qs in question_stats:
            for tname in qs['tags']:
                if tname not in tag_data:
                    tag_data[tname] = {'name': tname, 'question_count': 0, 'acc_sum': 0.0}
                tag_data[tname]['question_count'] += 1
                tag_data[tname]['acc_sum'] += qs['accuracy']

        topic_stats = []
        for tname, tinfo in tag_data.items():
            q_cnt = tinfo['question_count']
            topic_stats.append({
                'name': tname,
                'question_count': q_cnt,
                'accuracy': round(tinfo['acc_sum'] / q_cnt, 1) if q_cnt > 0 else 0.0
            })
        topic_stats.sort(key=lambda x: x['accuracy'])

        # Orientation stats (KHMT vs THUD)
        khmt_scores = [s.score for s in exam_sessions if s.answers.get('__meta__', {}).get('orientation') == 'KHMT']
        thud_scores = [s.score for s in exam_sessions if s.answers.get('__meta__', {}).get('orientation') == 'THUD']

        khmt_avg = round(sum(khmt_scores) / len(khmt_scores), 2) if khmt_scores else None
        thud_avg = round(sum(thud_scores) / len(thud_scores), 2) if thud_scores else None

        context = {
            'title': f'Phân tích số liệu: {exam.name}',
            'exam': exam,
            'total_attempts': total_attempts,
            'unique_users': unique_users,
            'avg_score': avg_score,
            'median_score': median_score,
            'max_score': max_score,
            'min_score': min_score,
            'avg_time_minutes': avg_time_minutes,
            'total_violations': total_violations,
            'violation_rate': violation_rate,
            'bucket_data': bucket_data,
            'question_stats': question_stats,
            'weakest_questions': weakest_questions,
            'topic_stats': topic_stats,
            'khmt_count': len(khmt_scores),
            'khmt_avg': khmt_avg,
            'thud_count': len(thud_scores),
            'thud_avg': thud_avg,
            'student_attempts': student_attempts,
            'available_orgs': available_orgs,
            'available_classes': available_classes,
            'selected_org_id': filter_org_id or '',
            'selected_class_id': filter_class_id or '',
        }
        return render(request, 'quiz/exam_analytics.html', context)


class QuizExamLiveMonitorView(View):
    """Live proctoring monitor room for teachers/admin."""
    def get(self, request, exam_id):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền giám sát đề thi.")

        exam = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and exam.created_by not in (None, request.user):
            return HttpResponseForbidden("Bạn không có quyền giám sát đề thi này.")

        context = {
            'title': f'Phòng giám sát trực tiếp: {exam.name}',
            'exam': exam,
            'is_teacher': True,
            'last_msg': event.last() if hasattr(event, 'last') else 0,
        }
        return render(request, 'quiz/exam_monitor.html', context)


class QuizExamLiveMonitorAjaxView(View):
    """API endpoint to poll active and completed sessions for live proctoring with user deduplication."""
    def get(self, request, exam_id):
        if not is_teacher(request.user):
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        exam = get_object_or_404(QuizSource, id=exam_id)
        
        from datetime import timedelta
        recent_threshold = timezone.now() - timedelta(hours=6)

        all_recent_sessions = QuizSession.objects.filter(
            created_at__gte=recent_threshold,
            answers__has_key='__meta__'
        ).select_related('user__profile').order_by('-updated_at')

        exam_sessions = [
            s for s in all_recent_sessions 
            if s.answers.get('__meta__', {}).get('source_id') == exam.id
        ]

        total_questions = exam.questions.count()

        # DEDUPLICATION BY USER: Exactly 1 row/card per student
        # Priority: Active (in-progress) session > Completed session; then newest updated_at
        user_sessions = {}
        for s in exam_sessions:
            uid = s.user_id if s.user_id else f"guest_{s.id}"
            if uid not in user_sessions:
                user_sessions[uid] = s
            else:
                curr_best = user_sessions[uid]
                if curr_best.completed and not s.completed:
                    user_sessions[uid] = s
                elif curr_best.completed == s.completed and s.updated_at > curr_best.updated_at:
                    user_sessions[uid] = s

        deduped_sessions = list(user_sessions.values())
        # Sort so active students appear first, then sorted by updated_at descending
        deduped_sessions.sort(key=lambda s: (not s.completed, s.updated_at), reverse=True)

        live_students = []
        completed_students = []
        total_violations_active = 0
        total_violations_all = 0

        for s in deduped_sessions:
            meta = s.answers.get('__meta__', {})
            duration = meta.get('duration', exam.default_duration)
            time_left = meta.get('time_left', duration * 60)
            v_count = meta.get('violation_count', 0)
            v_log = meta.get('violations_log', [])
            latest_v = v_log[-1] if v_log else None

            answered_keys = [k for k in s.answers.keys() if k != '__meta__']
            q_count = len(s.questions) if s.questions else total_questions
            progress_pct = round((len(answered_keys) / q_count) * 100) if q_count > 0 else 0

            classes_str = ""
            if s.user and hasattr(s.user, 'profile'):
                cls_list = [c.name for c in s.user.profile.classes.all()[:2]]
                classes_str = ", ".join(cls_list)

            student_info = {
                'session_id': s.id,
                'username': s.user.username if s.user else 'Khách',
                'display_name': (s.user.profile.display_name if s.user and hasattr(s.user, 'profile') and s.user.profile.display_name else (s.user.username if s.user else 'Khách')),
                'class_name': classes_str,
                'orientation': meta.get('orientation', 'KHMT'),
                'started_at': s.created_at.strftime('%H:%M:%S'),
                'updated_at': s.updated_at.strftime('%H:%M:%S'),
                'time_left_seconds': time_left,
                'time_left_str': f"{time_left // 60:02d}:{time_left % 60:02d}" if time_left > 0 else "00:00",
                'answered_count': len(answered_keys),
                'total_questions': q_count,
                'progress_pct': progress_pct,
                'score': round(s.score, 2) if s.completed else None,
                'is_completed': s.completed,
                'violation_count': v_count,
                'latest_violation': latest_v,
                'violations_log': v_log,
                'is_paused': meta.get('is_paused', False),
                'extra_time_added': meta.get('extra_time_added', 0),
                'proctor_warning': meta.get('proctor_warning'),
            }

            total_violations_all += v_count
            if not s.completed:
                total_violations_active += v_count
                live_students.append(student_info)
            else:
                completed_students.append(student_info)

        return JsonResponse({
            'success': True,
            'exam_name': exam.name,
            'max_violations': exam.max_violations,
            'is_strict_anti_cheat': exam.is_strict_anti_cheat,
            'active_count': len(live_students),
            'completed_count': len(completed_students),
            'total_students_count': len(deduped_sessions),
            'total_violations_active': total_violations_active,
            'total_violations_all': total_violations_all,
            'active_students': live_students,
            'completed_students': completed_students,
            'students': live_students + completed_students,
        })


def broadcast_proctor_event(channel, message_data):
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        s.connect(('127.0.0.1', 15101))
        payload = json.dumps({'command': 'post', 'channel': channel, 'message': message_data})
        s.sendall(payload.encode('utf-8'))
        s.close()
    except Exception:
        pass


class QuizExamProctorActionView(View):
    """Allows teacher to intervene in live student exam sessions."""
    def post(self, request, exam_id):
        if not is_teacher(request.user):
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        exam = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and exam.created_by not in (None, request.user):
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        session_id = request.POST.get('session_id')
        action = request.POST.get('action')
        
        session = get_object_or_404(QuizSession, id=session_id)
        meta = session.answers.setdefault('__meta__', {})

        event_data = {'action': action, 'session_id': session.id}

        if action in ('warning', 'send_warning'):
            message = request.POST.get('message', request.POST.get('warning_text', '')).strip()
            if not message:
                message = _("Giám thị nhắc nhở bạn cần tập trung làm bài nghiêm túc, không nhìn ra ngoài hoặc chuyển tab!")
            import uuid
            warning_obj = {
                'id': str(uuid.uuid4())[:8],
                'message': message,
                'time': timezone.now().strftime('%H:%M:%S'),
                'teacher': request.user.username,
            }
            meta['proctor_warning'] = warning_obj
            event_data['warning'] = warning_obj
            session.save()

        elif action == 'pause':
            meta['is_paused'] = True
            meta['paused_at'] = timezone.now().isoformat()
            event_data['is_paused'] = True
            session.save()

        elif action == 'resume':
            meta['is_paused'] = False
            meta.pop('paused_at', None)
            event_data['is_paused'] = False
            session.save()

        elif action == 'add_time':
            try:
                minutes = int(request.POST.get('minutes', 5))
            except ValueError:
                minutes = 5
            extra_sec = minutes * 60
            meta['extra_time_added'] = meta.get('extra_time_added', 0) + extra_sec
            meta['time_left'] = max(0, meta.get('time_left', 0) + extra_sec)
            event_data['extra_minutes'] = minutes
            event_data['time_left'] = meta['time_left']
            session.save()

        elif action == 'force_submit':
            meta['force_submitted_by_teacher'] = True
            grade_exam_session(session)
            event_data['force_submitted'] = True

        elif action == 'reset_session':
            # Reset student session so they can start fresh
            session.completed = False
            session.score = 0.0
            meta['violation_count'] = 0
            meta['violations_log'] = []
            meta['is_paused'] = False
            meta.pop('force_submitted_by_teacher', None)
            meta.pop('force_submitted_by_cheat', None)
            session.answers = {'__meta__': meta}
            session.save()
            event_data['reset'] = True

        elif action == 'inspect_session':
            # Return answered detail
            answered_keys = [k for k in session.answers.keys() if k != '__meta__']
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'username': session.user.username if session.user else 'Khách',
                'display_name': (session.user.profile.display_name if session.user and hasattr(session.user, 'profile') and session.user.profile.display_name else (session.user.username if session.user else 'Khách')),
                'answered_count': len(answered_keys),
                'total_questions': len(session.questions) if session.questions else exam.questions.count(),
                'answers': {k: session.answers[k] for k in answered_keys},
                'violations_log': meta.get('violations_log', []),
                'violation_count': meta.get('violation_count', 0),
                'score': round(session.score, 2) if session.completed else None,
                'is_completed': session.completed,
                'is_paused': meta.get('is_paused', False),
            })

        else:
            return JsonResponse({'error': 'Invalid proctor action'}, status=400)

        # Broadcast event to WebSocket channels
        try:
            event.post(f"quiz_session_{session.id}", event_data)
            event.post(f"quiz_exam_{exam.id}", {
                'type': 'proctor_action',
                'action': action,
                'session_id': session.id,
                'event_data': event_data,
            })
        except Exception:
            pass

        return JsonResponse({'success': True, 'action': action, 'session_id': session.id})


class QuizCreateRemediationAssignmentView(View):
    """Automatically generates a targeted homework assignment addressing students' weakest topics/questions."""
    def post(self, request, exam_id):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền tạo bài tập củng cố.")

        exam = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and exam.created_by not in (None, request.user):
            return HttpResponseForbidden("Bạn không có quyền thực hiện trên đề thi này.")

        # Find weak questions and tags from completed sessions
        sessions = QuizSession.objects.filter(completed=True, answers__has_key='__meta__')
        exam_sessions = [s for s in sessions if s.answers.get('__meta__', {}).get('source_id') == exam.id]

        questions = list(QuizQuestion.objects.filter(source=exam).prefetch_related('tags', 'options'))
        
        weak_q_ids = []
        weak_tag_ids = set()

        for q in questions:
            total_attempts = 0
            correct_attempts = 0
            if q.type == 'choice':
                c_opt = q.options.filter(is_correct=True).first()
                c_lbl = c_opt.label if c_opt else 'A'
            else:
                c_tf_map = {opt.label: opt.is_correct for opt in q.options.all()}

            for s in exam_sessions:
                if str(q.id) in s.answers:
                    total_attempts += 1
                    u_ans = s.answers[str(q.id)]
                    if q.type == 'choice' and u_ans == c_lbl:
                        correct_attempts += 1
                    elif q.type == 'tf' and isinstance(u_ans, dict):
                        if all(u_ans.get(lbl) == c_val for lbl, c_val in c_tf_map.items()):
                            correct_attempts += 1

            acc = (correct_attempts / total_attempts) if total_attempts > 0 else 1.0
            if acc < 0.75:
                weak_q_ids.append(q.id)
                for t in q.tags.all():
                    weak_tag_ids.add(t.id)

        if not weak_tag_ids:
            for q in questions:
                for t in q.tags.all():
                    weak_tag_ids.add(t.id)

        candidate_qs = QuizQuestion.objects.filter(tags__id__in=list(weak_tag_ids)).distinct().exclude(id__in=[q.id for q in questions])
        remediation_questions = list(candidate_qs[:15])

        if len(remediation_questions) < 10:
            remediation_questions.extend(questions)
            remediation_questions = list({q.id: q for q in remediation_questions}.values())[:20]

        with transaction.atomic():
            rem_exam = QuizSource.objects.create(
                name=f"Bài tập củng cố: {exam.name} (Khắc phục lỗ hổng)",
                description=f"Bài tập tự động tạo nhằm củng cố các chuyên đề học sinh có tỉ lệ làm sai cao trong bài kiểm tra '{exam.name}'.",
                default_duration=30,
                exam_type='homework',
                access_code=QuizSource.generate_unique_pin(),
                shuffle_questions=True,
                created_by=request.user,
                is_visible=True,
                is_active=True,
                require_login=True,
            )
            rem_exam.target_classes.set(exam.target_classes.all())
            rem_exam.organizations.set(exam.organizations.all())

            for q in remediation_questions:
                if q.source != rem_exam:
                    new_q = QuizQuestion.objects.create(
                        content=q.content,
                        type=q.type,
                        difficulty=q.difficulty,
                        explanation=q.explanation,
                        source=rem_exam,
                        created_by=request.user
                    )
                    new_q.tags.set(q.tags.all())
                    for opt in q.options.all():
                        QuizOption.objects.create(
                            question=new_q,
                            label=opt.label,
                            content=opt.content,
                            is_correct=opt.is_correct
                        )

        messages.success(request, f"Đã tự động tạo bài tập củng cố kiến thức thành công với {rem_exam.questions.count()} câu hỏi!")
        return redirect('quiz_exam_edit', exam_id=rem_exam.id)


class QuizExamExportView(View):
    """Export exam results to CSV with optional Org/Class filter."""
    def get(self, request, exam_id):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền xuất dữ liệu.")

        exam = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and exam.created_by not in (None, request.user):
            return HttpResponseForbidden("Bạn không có quyền xuất dữ liệu đề thi này.")

        filter_org_id = request.GET.get('org_id')
        filter_class_id = request.GET.get('class_id')

        all_sessions = QuizSession.objects.filter(
            completed=True,
            answers__has_key='__meta__'
        ).select_related('user__profile').prefetch_related(
            'user__profile__organizations',
            'user__profile__classes'
        ).order_by('-created_at')

        raw_exam_sessions = [
            s for s in all_sessions 
            if s.answers.get('__meta__', {}).get('source_id') == exam.id
        ]

        exam_sessions = []
        for s in raw_exam_sessions:
            if filter_org_id:
                try:
                    f_oid = int(filter_org_id)
                    if not s.user or not hasattr(s.user, 'profile') or not s.user.profile.organizations.filter(id=f_oid).exists():
                        continue
                except ValueError:
                    pass

            if filter_class_id:
                try:
                    f_cid = int(filter_class_id)
                    if not s.user or not hasattr(s.user, 'profile') or not s.user.profile.classes.filter(id=f_cid).exists():
                        continue
                except ValueError:
                    pass

            exam_sessions.append(s)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        safe_name = slugify(exam.name) or "exam"
        response['Content-Disposition'] = f'attachment; filename="ket_qua_thi_{exam.id}_{safe_name}.csv"'
        response.write('\ufeff') # UTF-8 BOM for Excel

        writer = csv.writer(response)
        writer.writerow(['STT', 'Tên đăng nhập', 'Tên hiển thị', 'Lớp', 'Trường / Tổ chức', 'Điểm số', 'Thời gian làm bài', 'Số lần vi phạm', 'Thời điểm nộp', 'Chi tiết vi phạm'])

        for idx, s in enumerate(exam_sessions, 1):
            meta = s.answers.get('__meta__', {})
            duration = meta.get('duration', exam.default_duration)
            time_left = meta.get('time_left', 0)
            time_spent_sec = max(0, duration * 60 - time_left)
            time_str = f"{time_spent_sec // 60}p {time_spent_sec % 60}s"

            v_count = meta.get('violation_count', 0)
            v_logs = meta.get('violations_log', [])
            v_detail_str = "; ".join([f"[{v.get('time')}] {v.get('type')}: {v.get('detail')}" for v in v_logs])

            orgs = ""
            classes = ""
            if s.user and hasattr(s.user, 'profile'):
                orgs = ", ".join([org.short_name or org.name for org in s.user.profile.organizations.all()])
                classes = ", ".join([cls.name for cls in s.user.profile.classes.all()])

            writer.writerow([
                idx,
                s.user.username if s.user else 'Khách',
                s.user.profile.display_name if s.user and hasattr(s.user, 'profile') else 'Khách',
                classes,
                orgs,
                s.score,
                time_str,
                v_count,
                s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                v_detail_str,
            ])

        return response


class QuizExamToggleActiveView(View):
    """Teacher toggles an exam active / inactive (open or close room)."""
    def post(self, request, exam_id):
        if not is_teacher(request.user):
            return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

        exam = get_object_or_404(QuizSource, id=exam_id)
        if not request.user.is_superuser and exam.created_by not in (None, request.user):
            return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

        exam.is_active = not exam.is_active
        exam.save()

        return JsonResponse({
            'success': True,
            'is_active': exam.is_active,
            'message': 'Đã mở phòng thi' if exam.is_active else 'Đã đóng phòng thi'
        })


def get_exam_access_error_message(user, exam):
    now = timezone.now()
    if not exam.is_active or exam.is_locked:
        return _("Phòng thi hiện đang đóng bởi giáo viên.")
    if exam.start_time and now < exam.start_time:
        st_str = timezone.localtime(exam.start_time).strftime('%H:%M ngày %d/%m/%Y')
        return _(f"Đề thi chưa mở. Thời gian mở đề: {st_str}")
    if exam.end_time and now > exam.end_time:
        et_str = timezone.localtime(exam.end_time).strftime('%H:%M ngày %d/%m/%Y')
        return _(f"Mã PIN / Đề thi này đã hết hạn vào lúc: {et_str}")
    if exam.require_login and not user.is_authenticated:
        return _("Bạn cần đăng nhập để làm bài thi này.")
    if exam.target_classes.exists():
        if not user.is_authenticated or not hasattr(user, 'profile'):
            return _("Bài thi này chỉ dành cho học sinh trong danh sách lớp được chỉ định.")
        user_class_ids = set(user.profile.classes.values_list('id', flat=True))
        target_ids = set(exam.target_classes.values_list('id', flat=True))
        if not (user_class_ids & target_ids):
            return _("Bạn không thuộc lớp được giao làm bài kiểm tra này.")
    if exam.is_organization_only:
        if not user.is_authenticated or not hasattr(user, 'profile'):
            return _("Bài thi chỉ dành cho thành viên của tổ chức/trường được chỉ định.")
        org_ids = list(exam.organizations.values_list('id', flat=True))
        if org_ids:
            user_org_ids = set(user.profile.organizations.values_list('id', flat=True))
            if not any(oid in user_org_ids for oid in org_ids):
                return _("Bạn không thuộc tổ chức/trường được chỉ định.")
    return None


class QuizJoinByPinView(View):
    """Students join an exam directly using a 6-digit PIN or direct link."""
    def get(self, request, pin_code=None):
        if not pin_code:
            pin_code = request.GET.get('pin', '').strip()

        exam = None
        error = None
        if pin_code:
            exam = QuizSource.objects.filter(access_code__iexact=pin_code).first()
            if not exam:
                error = _("Mã PIN không chính xác hoặc đề thi không tồn tại.")
            elif not can_access_exam(request.user, exam):
                error = get_exam_access_error_message(request.user, exam)

        context = {
            'pin_code': pin_code,
            'exam': exam,
            'error': error,
            'title': _("Tham gia thi bằng mã PIN"),
        }
        return render(request, 'quiz/join_pin.html', context)

    def post(self, request, pin_code=None):
        pin = request.POST.get('pin_code', '').strip().upper()
        if not pin:
            return render(request, 'quiz/join_pin.html', {
                'error': _('Vui lòng nhập mã PIN đề thi.'),
                'title': _('Tham gia thi bằng mã PIN'),
            })

        exam = QuizSource.objects.filter(access_code__iexact=pin).first()
        if not exam:
            return render(request, 'quiz/join_pin.html', {
                'pin_code': pin,
                'error': _('Mã PIN không chính xác hoặc đề thi không tồn tại.'),
                'title': _('Tham gia thi bằng mã PIN'),
            })

        if not can_access_exam(request.user, exam):
            err = get_exam_access_error_message(request.user, exam)
            return render(request, 'quiz/join_pin.html', {
                'pin_code': pin,
                'exam': exam,
                'error': err,
                'title': _('Tham gia thi bằng mã PIN'),
            })

        return redirect('quiz_start_exam', exam_id=exam.id)


class QuizHubView(View):
    """All-in-one Exam Hub & Classroom Management Center for Teachers & Students."""
    def get(self, request):
        user = request.user
        teacher_mode = is_teacher(user)

        from judge.models import Class, Organization

        context = {
            'is_teacher': teacher_mode,
            'title': _('Exam Hub & Classroom Center'),
        }

        if teacher_mode:
            # Teacher Stats & Dashboards (Class isolation: by default show only teacher's own classes)
            show_all = request.GET.get('all') == '1' and user.is_superuser
            if show_all:
                my_exams = QuizSource.objects.all().order_by('-created_at')
                my_classes = Class.objects.all().select_related('organization').order_by('name')
            elif hasattr(user, 'profile'):
                admin_org_ids = user.profile.admin_of.values_list('id', flat=True)
                my_classes = Class.objects.filter(
                    Q(admins=user.profile) | Q(organization_id__in=admin_org_ids)
                ).distinct().select_related('organization').order_by('name')

                my_exams = QuizSource.objects.filter(
                    Q(created_by=user) | Q(organizations__id__in=admin_org_ids) | Q(target_classes__in=my_classes)
                ).distinct().order_by('-created_at')
            else:
                my_classes = Class.objects.none()
                my_exams = QuizSource.objects.none()

            recent_attempts = QuizSession.objects.filter(
                completed=True,
                answers__has_key='__meta__'
            ).select_related('user__profile').order_by('-created_at')[:8]

            all_organizations = Organization.objects.all().order_by('name')

            # Build per-class metadata: pending joins + active exam count
            class_meta = {}
            for cl in my_classes:
                pending_cnt = 0
                try:
                    from judge.models import OrganizationRequest
                    pending_cnt = OrganizationRequest.objects.filter(
                        request_class=cl, state='P'
                    ).count()
                except Exception:
                    pass
                active_exam_cnt = QuizSource.objects.filter(
                    Q(target_classes=cl) | Q(organizations=cl.organization),
                    is_active=True
                ).distinct().count()
                class_meta[cl.id] = {
                    'pending': pending_cnt,
                    'active_exams': active_exam_cnt,
                }

            context.update({
                'my_exams': my_exams,
                'my_classes': my_classes,
                'class_meta': class_meta,
                'all_organizations': all_organizations,
                'recent_attempts': recent_attempts,
                'total_exams_count': my_exams.count(),
                'total_classes_count': my_classes.count(),
                'show_all': show_all,
                'is_superuser': user.is_superuser,
            })
        else:
            # Student Hub
            enrolled_classes = []
            assigned_exams_data = []
            if user.is_authenticated and hasattr(user, 'profile'):
                enrolled_classes = user.profile.classes.all().select_related('organization')
                user_orgs = user.profile.organizations.all()

                raw_assigned_exams = QuizSource.objects.filter(
                    Q(target_classes__in=enrolled_classes) | Q(organizations__in=user_orgs),
                    is_visible=True
                ).distinct().order_by('-created_at')

                user_sessions = QuizSession.objects.filter(
                    user=user,
                    completed=True,
                    answers__has_key='__meta__'
                ).order_by('-created_at')
                
                exam_session_map = {}
                for s in user_sessions:
                    meta = s.answers.get('__meta__', {}) if isinstance(s.answers, dict) else {}
                    src_id = meta.get('source_id')
                    if src_id:
                        try:
                            src_id_int = int(src_id)
                            if src_id_int not in exam_session_map:
                                score = meta.get('score', 0)
                                exam_session_map[src_id_int] = {
                                    'session_id': s.id,
                                    'score': score,
                                    'completed_at': s.created_at
                                }
                        except (ValueError, TypeError):
                            pass

                now = timezone.now()
                for ex in raw_assigned_exams:
                    hist = exam_session_map.get(ex.id)
                    is_completed = hist is not None
                    is_expired = bool(ex.end_time and now > ex.end_time and not is_completed)
                    
                    assigned_exams_data.append({
                        'exam': ex,
                        'is_completed': is_completed,
                        'is_expired': is_expired,
                        'score': hist['score'] if hist else None,
                        'session_id': hist['session_id'] if hist else None,
                        'completed_at': hist['completed_at'] if hist else None,
                    })

            my_history = []
            if user.is_authenticated:
                my_history = QuizSession.objects.filter(
                    user=user,
                    completed=True,
                    answers__has_key='__meta__'
                ).order_by('-created_at')[:10]

            context.update({
                'enrolled_classes': enrolled_classes,
                'assigned_exams': assigned_exams_data,
                'my_history': my_history,
            })

        return render(request, 'quiz/hub.html', context)


class QuizClassGradebookView(View):
    """Dedicated Classroom Gradebook for Teachers."""
    def get(self, request, class_id):
        from judge.models import Class
        class_obj = get_object_or_404(Class, id=class_id)

        # Check teacher permission
        teacher_mode = is_teacher(request.user)
        if not teacher_mode:
            return HttpResponseForbidden("Bạn không có quyền xem sổ điểm lớp này.")

        if not request.user.is_superuser:
            has_perm = (
                (hasattr(request.user, 'profile') and class_obj.admins.filter(id=request.user.profile.id).exists()) or
                (hasattr(request.user, 'profile') and request.user.profile.admin_of.filter(id=class_obj.organization_id).exists())
            )
            if not has_perm:
                return HttpResponseForbidden("Bạn không phải giáo viên phụ trách lớp này.")

        # Get all exams assigned to this class or its organization
        assigned_exams = QuizSource.objects.filter(
            Q(target_classes=class_obj) | Q(organizations=class_obj.organization),
            is_visible=True
        ).distinct().order_by('id')

        # Get all students in class
        students = class_obj.members.select_related('user').order_by('user__username')

        # Build matrix
        student_records = []
        exam_averages = {ex.id: [] for ex in assigned_exams}

        for member in students:
            u = member.user
            row = {
                'user': u,
                'profile': member,
                'scores': {},
                'total_score': 0.0,
                'completed_count': 0,
                'average_score': 0.0,
            }

            user_sessions = QuizSession.objects.filter(
                user=u,
                completed=True,
                answers__has_key='__meta__'
            ).order_by('-score')

            scores_list = []
            for ex in assigned_exams:
                # Find best attempt for this exam
                best_attempt = None
                for s in user_sessions:
                    if s.answers.get('__meta__', {}).get('source_id') == ex.id:
                        best_attempt = s
                        break

                if best_attempt:
                    row['scores'][ex.id] = {
                        'score': best_attempt.score,
                        'completed': True,
                        'session_id': best_attempt.id,
                        'violations': best_attempt.answers.get('__meta__', {}).get('violation_count', 0),
                        'date': best_attempt.created_at.strftime('%d/%m/%Y'),
                    }
                    scores_list.append(best_attempt.score)
                    exam_averages[ex.id].append(best_attempt.score)
                else:
                    row['scores'][ex.id] = {
                        'score': None,
                        'completed': False,
                        'session_id': None,
                        'violations': 0,
                        'date': '-',
                    }

            row['completed_count'] = len(scores_list)
            if scores_list:
                row['total_score'] = sum(scores_list)
                row['average_score'] = round(sum(scores_list) / len(scores_list), 2)

            student_records.append(row)

        # Calculate exam column averages
        exam_stats = []
        for ex in assigned_exams:
            scs = exam_averages.get(ex.id, [])
            avg = round(sum(scs) / len(scs), 2) if scs else None
            exam_stats.append({
                'exam': ex,
                'submitted_count': len(scs),
                'average_score': avg,
            })

        # Generate access code if missing
        if not class_obj.access_code:
            import string, random
            class_obj.access_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            class_obj.save(update_fields=['access_code'])

        # Pending join requests
        from judge.models import OrganizationRequest
        pending_requests = OrganizationRequest.objects.filter(
            request_class=class_obj,
            state='P'
        ).select_related('user__user')

        join_url = request.build_absolute_uri(reverse('quiz_class_join_direct', args=[class_obj.id])) + f"?code={class_obj.access_code}"

        all_available_exams = QuizSource.objects.filter(is_visible=True).exclude(id__in=[e.id for e in assigned_exams]).order_by('-created_at')[:40]

        context = {
            'class_obj': class_obj,
            'assigned_exams': assigned_exams,
            'all_available_exams': all_available_exams,
            'student_records': student_records,
            'exam_stats': exam_stats,
            'pending_requests': pending_requests,
            'access_code': class_obj.access_code,
            'join_url': join_url,
            'all_organizations': Organization.objects.all().order_by('name'),
            'title': f"Sổ điểm & Quản lý lớp {class_obj.name}",
        }
        return render(request, 'quiz/class_gradebook.html', context)


class QuizClassGradebookExportView(View):
    """Export Class Gradebook to Excel CSV."""
    def get(self, request, class_id):
        from judge.models import Class
        class_obj = get_object_or_404(Class, id=class_id)

        if not is_teacher(request.user):
            return HttpResponseForbidden("Forbidden")

        assigned_exams = list(QuizSource.objects.filter(
            Q(target_classes=class_obj) | Q(organizations=class_obj.organization),
            is_visible=True
        ).distinct().order_by('id'))

        students = class_obj.members.select_related('user').order_by('user__username')

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        safe_name = slugify(class_obj.name) or "class"
        response['Content-Disposition'] = f'attachment; filename="so_diem_lop_{safe_name}.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        headers = ['STT', 'Tên đăng nhập', 'Họ và tên'] + [ex.name for ex in assigned_exams] + ['Số bài đã làm', 'Điểm trung bình']
        writer.writerow(headers)

        for idx, member in enumerate(students, 1):
            u = member.user
            user_sessions = QuizSession.objects.filter(
                user=u,
                completed=True,
                answers__has_key='__meta__'
            ).order_by('-score')

            scores_row = []
            valid_scores = []
            for ex in assigned_exams:
                best_attempt = None
                for s in user_sessions:
                    if s.answers.get('__meta__', {}).get('source_id') == ex.id:
                        best_attempt = s
                        break
                if best_attempt is not None:
                    scores_row.append(best_attempt.score)
                    valid_scores.append(best_attempt.score)
                else:
                    scores_row.append('-')

            avg_str = f"{round(sum(valid_scores)/len(valid_scores), 2)}" if valid_scores else "-"
            writer.writerow([
                idx,
                u.username,
                member.display_name or u.username,
            ] + scores_row + [len(valid_scores), avg_str])

        return response


class QuizExamBuilderView(View):
    """Interactive Custom Exam Builder from Question Bank."""
    def get(self, request):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Bạn không có quyền tạo đề thi tùy biến.")

        tag_query = request.GET.get('tag', '')
        diff_query = request.GET.get('difficulty', '')
        type_query = request.GET.get('type', '')
        search_query = request.GET.get('q', '')

        questions = QuizQuestion.objects.all().prefetch_related('options', 'tags').order_by('-id')

        if tag_query:
            questions = questions.filter(tags__name__icontains=tag_query)
        if diff_query:
            questions = questions.filter(difficulty=diff_query)
        if type_query:
            questions = questions.filter(type=type_query)
        if search_query:
            questions = questions.filter(content__icontains=search_query)

        tags = QuizTag.objects.all().order_by('name')

        from judge.models import Class, Organization
        if request.user.is_superuser:
            teacher_classes = Class.objects.filter(is_active=True).order_by('name')
        else:
            teacher_classes = Class.objects.filter(created_by=request.user, is_active=True).order_by('name')
        
        organizations = Organization.objects.all().order_by('name')

        context = {
            'questions': questions,
            'total_questions_found': questions.count(),
            'tags': tags,
            'teacher_classes': teacher_classes,
            'organizations': organizations,
            'title': _('Trình Tạo Đề Thi Chuyên Môn (Exam Builder)'),
        }
        return render(request, 'quiz/exam_builder.html', context)

    def post(self, request):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Forbidden")

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        default_duration = request.POST.get('default_duration', '45')
        exam_type = request.POST.get('exam_type', 'in_class')
        access_code = request.POST.get('access_code', '').strip().upper()
        shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        shuffle_options = request.POST.get('shuffle_options') == 'on'
        is_strict_anti_cheat = request.POST.get('is_strict_anti_cheat') == 'on'
        is_visible = request.POST.get('is_visible') == 'on'
        target_class_ids = request.POST.getlist('target_classes')
        selected_qids = request.POST.getlist('selected_questions')

        if not name:
            name = f"Đề thi chuyên môn {timezone.now().strftime('%d/%m/%Y %H:%M')}"

        try:
            dur = int(default_duration)
        except ValueError:
            dur = 45

        with transaction.atomic():
            exam = QuizSource.objects.create(
                name=name,
                description=description,
                default_duration=dur,
                exam_type=exam_type,
                access_code=access_code if access_code else None,
                shuffle_questions=shuffle_questions,
                shuffle_options=shuffle_options,
                is_strict_anti_cheat=is_strict_anti_cheat,
                created_by=request.user,
                is_visible=is_visible,
                is_active=True,
                require_login=True,
            )

            if target_class_ids:
                from judge.models import Class
                classes = Class.objects.filter(id__in=target_class_ids)
                exam.target_classes.set(classes)

            if selected_qids:
                q_objs = QuizQuestion.objects.filter(id__in=selected_qids)
                for q in q_objs:
                    q.source = exam
                    q.save()

        messages.success(request, _('Đã tạo thành công đề thi "%s" với %d câu hỏi!') % (exam.name, len(selected_qids)))
        return redirect('quiz_exam_manage')


class QuizClassJoinDirectView(View):
    """Direct Class Join with Access Code / Link."""
    def get(self, request, class_id):
        from judge.models import Class, OrganizationRequest
        class_obj = get_object_or_404(Class, id=class_id)
        code = request.GET.get('code', '').strip().upper()

        if not request.user.is_authenticated:
            return redirect(f"{reverse('auth_login')}?next={request.get_full_path()}")

        profile = request.profile
        if class_obj.members.filter(id=profile.id).exists():
            messages.info(request, _('Bạn đã là thành viên của lớp học %s.') % class_obj.name)
            return redirect('quiz_hub')

        if code and class_obj.access_code and code == class_obj.access_code.upper():
            with transaction.atomic():
                class_obj.members.add(profile)
                class_obj.organization.members.add(profile)
                OrganizationRequest.objects.filter(user=profile, request_class=class_obj, state='P').update(state='A')
            messages.success(request, _('Tham gia lớp học %s thành công!') % class_obj.name)
            return redirect('quiz_hub')

        context = {
            'class_obj': class_obj,
            'code': code,
            'title': _('Tham gia lớp học %s') % class_obj.name,
        }
        return render(request, 'quiz/join_class.html', context)

    def post(self, request, class_id):
        from judge.models import Class, OrganizationRequest
        class_obj = get_object_or_404(Class, id=class_id)
        code = request.POST.get('code', '').strip().upper()

        if not request.user.is_authenticated:
            return redirect(f"{reverse('auth_login')}?next={request.get_full_path()}")

        profile = request.profile
        if class_obj.members.filter(id=profile.id).exists():
            messages.info(request, _('Bạn đã là thành viên của lớp học %s.') % class_obj.name)
            return redirect('quiz_hub')

        if class_obj.access_code and code == class_obj.access_code.upper():
            with transaction.atomic():
                class_obj.members.add(profile)
                class_obj.organization.members.add(profile)
                OrganizationRequest.objects.filter(user=profile, request_class=class_obj, state='P').update(state='A')
            messages.success(request, _('Tham gia lớp học %s thành công!') % class_obj.name)
            return redirect('quiz_hub')
        else:
            reason = request.POST.get('reason', 'Xin tham gia lớp học').strip()
            req, created = OrganizationRequest.objects.get_or_create(
                user=profile,
                organization=class_obj.organization,
                request_class=class_obj,
                defaults={'state': 'P', 'reason': reason}
            )
            if not created and req.state == 'P':
                messages.info(request, _('Yêu cầu tham gia lớp của bạn đang chờ giáo viên xét duyệt.'))
            else:
                req.state = 'P'
                req.reason = reason
                req.save()
                messages.success(request, _('Đã gửi yêu cầu tham gia lớp học tới giáo viên.'))
            return redirect('quiz_hub')


class QuizClassMemberActionView(View):
    """Teacher action to approve/reject join requests, add/remove students, regen code."""
    def post(self, request, class_id):
        from judge.models import Class, OrganizationRequest, Profile
        from django.contrib.auth.models import User
        class_obj = get_object_or_404(Class, id=class_id)

        if not is_teacher(request.user):
            return JsonResponse({'success': False, 'error': _('Không có quyền.')}, status=403)

        action = request.POST.get('action')

        if action == 'approve':
            req_id = request.POST.get('request_id')
            req = get_object_or_404(OrganizationRequest, id=req_id, request_class=class_obj)
            with transaction.atomic():
                req.state = 'A'
                req.save()
                class_obj.members.add(req.user)
                class_obj.organization.members.add(req.user)
            return JsonResponse({'success': True, 'message': _('Đã duyệt học sinh vào lớp.')})

        elif action == 'reject':
            req_id = request.POST.get('request_id')
            req = get_object_or_404(OrganizationRequest, id=req_id, request_class=class_obj)
            req.state = 'R'
            req.save()
            return JsonResponse({'success': True, 'message': _('Đã từ chối yêu cầu.')})

        elif action == 'approve_all':
            with transaction.atomic():
                pending = OrganizationRequest.objects.filter(request_class=class_obj, state='P')
                for req in pending:
                    req.state = 'A'
                    req.save()
                    class_obj.members.add(req.user)
                    class_obj.organization.members.add(req.user)
            return JsonResponse({'success': True, 'message': _('Đã duyệt tất cả yêu cầu tham gia lớp.')})

        elif action == 'add_students':
            raw_users = request.POST.get('usernames', '').strip()
            import re
            tokens = [t.strip() for t in re.split(r'[\s,;\n]+', raw_users) if t.strip()]
            added_count = 0
            not_found = []
            with transaction.atomic():
                for token in tokens:
                    user_match = User.objects.filter(Q(username__iexact=token) | Q(email__iexact=token)).first()
                    if user_match and hasattr(user_match, 'profile'):
                        class_obj.members.add(user_match.profile)
                        class_obj.organization.members.add(user_match.profile)
                        OrganizationRequest.objects.filter(user=user_match.profile, request_class=class_obj, state='P').update(state='A')
                        added_count += 1
                    else:
                        not_found.append(token)

            return JsonResponse({
                'success': True,
                'added_count': added_count,
                'not_found': not_found,
                'message': _('Đã thêm %d học sinh vào lớp.') % added_count
            })

        elif action == 'remove_student':
            user_id = request.POST.get('user_id')
            profile = get_object_or_404(Profile, id=user_id)
            class_obj.members.remove(profile)
            return JsonResponse({'success': True, 'message': _('Đã xóa học sinh khỏi lớp.')})

        elif action == 'regen_code':
            import string, random
            new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            class_obj.access_code = new_code
            class_obj.save(update_fields=['access_code'])
            join_url = request.build_absolute_uri(reverse('quiz_class_join_direct', args=[class_obj.id])) + f"?code={new_code}"
            return JsonResponse({
                'success': True,
                'access_code': new_code,
                'join_url': join_url,
                'message': _('Đã tạo mã vào lớp mới.')
            })

        elif action == 'assign_exam':
            exam_id = request.POST.get('exam_id')
            exam = get_object_or_404(QuizSource, id=exam_id)
            exam.target_classes.add(class_obj)

            # Optional deep customization updates
            exam_type = request.POST.get('exam_type')
            if exam_type in ('homework', 'in_class', 'official'):
                exam.exam_type = exam_type
                
            duration = request.POST.get('duration')
            if duration:
                try:
                    dur_int = int(duration)
                    if dur_int > 0:
                        exam.default_duration = dur_int
                except ValueError:
                    pass
                    
            start_time_raw = request.POST.get('start_time', '').strip()
            end_time_raw = request.POST.get('end_time', '').strip()
            from django.utils.dateparse import parse_datetime
            if start_time_raw:
                st = parse_datetime(start_time_raw)
                if st:
                    exam.start_time = timezone.make_aware(st) if timezone.is_naive(st) else st
            if end_time_raw:
                et = parse_datetime(end_time_raw)
                if et:
                    exam.end_time = timezone.make_aware(et) if timezone.is_naive(et) else et

            is_strict = request.POST.get('is_strict_anti_cheat')
            if is_strict is not None:
                exam.is_strict_anti_cheat = (is_strict == 'true' or is_strict == '1')
                
            shuffle_q = request.POST.get('shuffle_questions')
            if shuffle_q is not None:
                exam.shuffle_questions = (shuffle_q == 'true' or shuffle_q == '1')
                
            shuffle_opt = request.POST.get('shuffle_options')
            if shuffle_opt is not None:
                exam.shuffle_options = (shuffle_opt == 'true' or shuffle_opt == '1')
                
            max_viol = request.POST.get('max_violations')
            if max_viol:
                try:
                    exam.max_violations = int(max_viol)
                except ValueError:
                    pass

            exam.save()
            return JsonResponse({'success': True, 'message': _('Đã giao bài kiểm tra "%s" cho lớp với cấu hình tùy biến.') % exam.name})

        elif action == 'toggle_exam_status':
            exam_id = request.POST.get('exam_id')
            exam = get_object_or_404(QuizSource, id=exam_id)
            exam.is_active = not exam.is_active
            exam.save(update_fields=['is_active'])
            status_text = _('Đang mở') if exam.is_active else _('Đang đóng')
            return JsonResponse({
                'success': True,
                'is_active': exam.is_active,
                'status_text': str(status_text),
                'message': _('Đã chuyển trạng thái phòng thi sang: %s') % status_text
            })

        elif action == 'update_exam_pin':
            exam_id = request.POST.get('exam_id')
            exam = get_object_or_404(QuizSource, id=exam_id)
            new_pin = request.POST.get('pin', '').strip().upper()
            if not new_pin:
                new_pin = QuizSource.generate_unique_pin()
            exam.access_code = new_pin
            exam.save(update_fields=['access_code'])
            return JsonResponse({
                'success': True,
                'access_code': new_pin,
                'message': _('Đã cập nhật mã PIN vào thi: %s') % new_pin
            })

        elif action == 'get_unsubmitted_students':
            exam_id = request.POST.get('exam_id')
            exam = get_object_or_404(QuizSource, id=exam_id)
            members = class_obj.members.select_related('user').all()

            # Find users who completed a session for this exam
            all_sessions = QuizSession.objects.filter(
                completed=True,
                answers__has_key='__meta__',
                user__in=[m.user for m in members]
            ).values('user_id', 'answers')

            completed_user_ids = set()
            for s in all_sessions:
                if s.get('answers', {}).get('__meta__', {}).get('source_id') == exam.id:
                    completed_user_ids.add(s['user_id'])

            unsubmitted = []
            for m in members:
                if m.user_id not in completed_user_ids:
                    unsubmitted.append({
                        'id': m.id,
                        'user_id': m.user_id,
                        'username': m.user.username,
                        'display_name': m.display_name or m.user.username,
                        'email': m.user.email or ''
                    })

            return JsonResponse({
                'success': True,
                'exam_name': exam.name,
                'total_class_students': members.count(),
                'unsubmitted_count': len(unsubmitted),
                'unsubmitted_students': unsubmitted
            })

        elif action == 'unassign_exam':
            exam_id = request.POST.get('exam_id')
            exam = get_object_or_404(QuizSource, id=exam_id)
            exam.target_classes.remove(class_obj)
            return JsonResponse({'success': True, 'message': _('Đã hủy giao bài kiểm tra khỏi lớp.')})

        elif action == 'set_announcement':
            announcement = request.POST.get('announcement', '').strip()
            class_obj.description = announcement
            class_obj.save(update_fields=['description'])
            return JsonResponse({'success': True, 'message': _('Đã lưu thông báo mới cho lớp học.')})

        return JsonResponse({'success': False, 'error': _('Hành động không hợp lệ.')}, status=400)


class QuizClassCreateAjaxView(View):
    """Direct fast Class creation for teachers and admins with custom organization support."""
    def post(self, request):
        if not is_teacher(request.user):
            return JsonResponse({'success': False, 'error': _('Bạn không có quyền tạo lớp học.')}, status=403)

        from judge.models import Class, Organization
        from django.utils.text import slugify
        import string, random

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        org_id = request.POST.get('organization_id')
        org_name_new = request.POST.get('organization_name_new', '').strip()
        access_code = request.POST.get('access_code', '').strip().upper()

        if not name:
            return JsonResponse({'success': False, 'error': _('Vui lòng nhập tên lớp học.')}, status=400)

        # Resolve organization
        org = None
        if org_name_new:
            # Custom new school/org
            org_slug = slugify(org_name_new) or 'org'
            base_org_slug = org_slug
            count = 1
            while Organization.objects.filter(slug=org_slug).exists():
                org_slug = f"{base_org_slug}-{count}"
                count += 1
            org = Organization.objects.create(
                name=org_name_new,
                short_name=org_name_new[:20],
                slug=org_slug,
                is_open=True
            )
            if hasattr(request.user, 'profile'):
                org.admins.add(request.user.profile)
        elif org_id:
            try:
                org = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                return JsonResponse({'success': False, 'error': _('Tổ chức / Trường học không tồn tại.')}, status=404)
        else:
            if hasattr(request.user, 'profile') and request.user.profile.admin_of.exists():
                org = request.user.profile.admin_of.first()
            elif Organization.objects.exists():
                org = Organization.objects.first()
            else:
                org = Organization.objects.create(
                    name="Default School",
                    short_name="FPT",
                    slug="fpt",
                    is_open=True
                )

        if not access_code:
            access_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        base_slug = slugify(name) or 'class'
        slug = base_slug
        count = 1
        while Class.objects.filter(slug=slug, organization=org).exists():
            slug = f"{base_slug}-{count}"
            count += 1

        if Class.objects.filter(name=name, organization=org, is_active=True).exists():
            return JsonResponse({'success': False, 'error': _('Lớp học này đã tồn tại trong trường!')}, status=400)

        with transaction.atomic():
            class_obj = Class.objects.create(
                organization=org,
                name=name,
                slug=slug,
                description=description,
                access_code=access_code,
                is_active=True
            )
            if hasattr(request.user, 'profile'):
                class_obj.admins.add(request.user.profile)

        join_url = request.build_absolute_uri(reverse('quiz_class_join_direct', args=[class_obj.id])) + f"?code={class_obj.access_code}"

        return JsonResponse({
            'success': True,
            'class': {
                'id': class_obj.id,
                'name': class_obj.name,
                'organization_name': org.short_name or org.name,
                'access_code': class_obj.access_code,
                'join_url': join_url,
            }
        })


class QuizClassEditAjaxView(View):
    """Edit/Delete Class settings."""
    def get(self, request, class_id):
        from judge.models import Class, Organization
        class_obj = get_object_or_404(Class, id=class_id)
        if not is_teacher(request.user):
            return JsonResponse({'success': False, 'error': _('Không có quyền.')}, status=403)

        return JsonResponse({
            'success': True,
            'class': {
                'id': class_obj.id,
                'name': class_obj.name,
                'description': class_obj.description,
                'organization_id': class_obj.organization_id,
                'organization_name': class_obj.organization.short_name or class_obj.organization.name,
                'access_code': class_obj.access_code,
                'is_active': class_obj.is_active,
            }
        })

    def post(self, request, class_id):
        from judge.models import Class, Organization
        class_obj = get_object_or_404(Class, id=class_id)
        if not is_teacher(request.user):
            return JsonResponse({'success': False, 'error': _('Không có quyền.')}, status=403)

        # Check admin permission
        if not request.user.is_superuser:
            has_perm = (
                (hasattr(request.user, 'profile') and class_obj.admins.filter(id=request.user.profile.id).exists()) or
                (hasattr(request.user, 'profile') and request.user.profile.admin_of.filter(id=class_obj.organization_id).exists())
            )
            if not has_perm:
                return JsonResponse({'success': False, 'error': _('Bạn không có quyền quản lý lớp này.')}, status=403)

        action = request.POST.get('action', 'update')
        if action == 'delete':
            class_name = class_obj.name
            class_obj.delete()
            return JsonResponse({'success': True, 'deleted': True, 'message': _('Đã xóa lớp học %s.') % class_name})

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        access_code = request.POST.get('access_code', '').strip().upper()
        org_id = request.POST.get('organization_id')
        is_active = request.POST.get('is_active') in ('true', '1', True, 'on')

        if not name:
            return JsonResponse({'success': False, 'error': _('Tên lớp không được để trống.')}, status=400)

        class_obj.name = name
        class_obj.description = description
        if access_code:
            class_obj.access_code = access_code
        class_obj.is_active = is_active

        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
                class_obj.organization = org
            except Organization.DoesNotExist:
                pass

        class_obj.save()
        return JsonResponse({'success': True, 'message': _('Đã cập nhật thông tin lớp học thành công!')})



