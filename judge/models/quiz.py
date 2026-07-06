from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class QuizTag(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('tag name'), unique=True)
    slug = models.SlugField(max_length=100, verbose_name=_('slug'), unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('quiz tag')
        verbose_name_plural = _('quiz tags')


class QuizSource(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('source name'), unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('quiz source')
        verbose_name_plural = _('quiz sources')


class QuizQuestion(models.Model):
    QUESTION_TYPES = (
        ('choice', _('Trắc nghiệm')),
        ('tf', _('Chùm Đúng/Sai')),
    )
    DIFFICULTY_CHOICES = (
        ('easy', _('Nhận biết')),
        ('medium', _('Thông hiểu')),
        ('hard', _('Vận dụng')),
        ('very_hard', _('Vận dụng cao')),
    )

    content = models.TextField(verbose_name=_('question content'))
    type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='choice', verbose_name=_('question type'))
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='easy', verbose_name=_('difficulty'))
    explanation = models.TextField(verbose_name=_('explanation'), blank=True, null=True)
    tags = models.ManyToManyField(QuizTag, verbose_name=_('tags'), blank=True, related_name='questions')
    source = models.ForeignKey(QuizSource, verbose_name=_('source'), on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    created_by = models.ForeignKey(User, verbose_name=_('created by'), on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True)

    def __str__(self):
        return f"#{self.id} - {self.get_type_display()} - {self.get_difficulty_display()}"

    class Meta:
        verbose_name = _('quiz question')
        verbose_name_plural = _('quiz questions')


class QuizOption(models.Model):
    question = models.ForeignKey(QuizQuestion, verbose_name=_('question'), on_delete=models.CASCADE, related_name='options')
    label = models.CharField(max_length=10, verbose_name=_('label'))  # A, B, C, D or a, b, c, d
    content = models.TextField(verbose_name=_('option content'))
    is_correct = models.BooleanField(default=False, verbose_name=_('is correct'))

    def __str__(self):
        return f"{self.question.id} - {self.label}: {self.content[:30]}"

    class Meta:
        verbose_name = _('quiz option')
        verbose_name_plural = _('quiz options')
        ordering = ['label']


class QuizSession(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'), on_delete=models.CASCADE, null=True, blank=True, related_name='quiz_sessions')
    session_key = models.CharField(max_length=100, verbose_name=_('session key'), null=True, blank=True)
    questions = models.JSONField(verbose_name=_('questions ordered list'), default=list) # List of question IDs
    answers = models.JSONField(verbose_name=_('user answers'), default=dict) # Dict matching index/id to answered value
    current_index = models.IntegerField(default=0, verbose_name=_('current index'))
    completed = models.BooleanField(default=False, verbose_name=_('completed'))
    score = models.FloatField(default=0.0, verbose_name=_('score'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('updated at'))

    def __str__(self):
        user_str = self.user.username if self.user else f"Guest ({self.session_key})"
        return f"Session {self.id} by {user_str} at {self.created_at}"

    @classmethod
    def get_incorrect_questions_for_user(cls, user=None, session_key=None):
        if user and user.is_authenticated:
            sessions = cls.objects.filter(user=user)
        elif session_key:
            sessions = cls.objects.filter(session_key=session_key)
        else:
            return []
        
        completed_sessions = sessions.filter(completed=True)
        q_ids = []
        for s in completed_sessions:
            q_ids.extend(s.questions)
        q_ids = list(set(q_ids))
        if not q_ids:
            return []
        
        from judge.models.quiz import QuizQuestion
        questions = QuizQuestion.objects.filter(id__in=q_ids).prefetch_related('options')
        correct_map = {}
        for q in questions:
            if q.type == 'choice':
                correct_opt = q.options.filter(is_correct=True).first()
                correct_map[q.id] = ('choice', correct_opt.label if correct_opt else 'A')
            else:
                correct_map[q.id] = ('tf', {opt.label: opt.is_correct for opt in q.options.all()})
        
        incorrect_ids = set()
        for s in completed_sessions:
            for q_id_str, ans in s.answers.items():
                try:
                    q_id = int(q_id_str)
                except ValueError:
                    continue
                if q_id not in correct_map:
                    continue
                
                q_type, correct_ans = correct_map[q_id]
                if ans == '__skipped__':
                    incorrect_ids.add(q_id)
                elif q_type == 'choice':
                    if ans != correct_ans:
                        incorrect_ids.add(q_id)
                elif q_type == 'tf':
                    if not isinstance(ans, dict):
                        incorrect_ids.add(q_id)
                        continue
                    is_all_correct = True
                    for label, correct_val in correct_ans.items():
                        if ans.get(label) != correct_val:
                            is_all_correct = False
                            break
                    if not is_all_correct:
                        incorrect_ids.add(q_id)
        
        return list(incorrect_ids)

    class Meta:
        verbose_name = _('quiz session')
        verbose_name_plural = _('quiz sessions')
