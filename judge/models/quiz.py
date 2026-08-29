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
    EXAM_TYPE_CHOICES = (
        ('in_class', _('Kiểm tra tại lớp')),
        ('homework', _('Bài tập về nhà')),
        ('practice', _('Luyện tập tự do')),
    )

    name = models.CharField(max_length=200, verbose_name=_('source name'), unique=True)
    is_visible = models.BooleanField(default=True, verbose_name=_('visible to users'),
                                     help_text=_('Whether this exam appears in the exam list.'))
    require_login = models.BooleanField(default=False, verbose_name=_('require login'),
                                        help_text=_('Users must be logged in to view and start this exam.'))
    is_locked = models.BooleanField(default=False, verbose_name=_('locked'),
                                    help_text=_('Exam is locked and cannot be started by users.'))
    is_featured = models.BooleanField(default=False, verbose_name=_('featured'),
                                      help_text=_('Show as featured exam.'))
    is_organization_only = models.BooleanField(default=False, verbose_name=_('organization only'),
                                               help_text=_('Only members of selected organizations or classes can view and start this exam.'))
    organizations = models.ManyToManyField('Organization', verbose_name=_('organizations'), blank=True,
                                           help_text=_('Organizations that can access this exam (empty = all if unchecked).'))
    target_classes = models.ManyToManyField('Class', verbose_name=_('target classes'), blank=True,
                                            related_name='assigned_quiz_sources',
                                            help_text=_('Specific classes assigned to take this exam.'))
    access_code = models.CharField(max_length=20, verbose_name=_('access code / PIN'), blank=True, null=True, unique=True,
                                   help_text=_('6-character PIN code for quick student join.'))
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='in_class', verbose_name=_('exam type'))
    start_time = models.DateTimeField(verbose_name=_('start time'), null=True, blank=True,
                                      help_text=_('Exam becomes accessible from this time.'))
    end_time = models.DateTimeField(verbose_name=_('end time'), null=True, blank=True,
                                    help_text=_('Exam closes after this time.'))
    is_active = models.BooleanField(default=True, verbose_name=_('is active / open for submission'),
                                    help_text=_('Teacher can toggle this to open or close the exam room anytime.'))
    shuffle_questions = models.BooleanField(default=False, verbose_name=_('shuffle questions'),
                                            help_text=_('Randomize question order for each student attempt.'))
    shuffle_options = models.BooleanField(default=False, verbose_name=_('shuffle options'),
                                          help_text=_('Randomize choice options (A,B,C,D) order.'))
    description = models.TextField(verbose_name=_('description'), blank=True, default='')
    default_duration = models.IntegerField(default=45, verbose_name=_('default duration (minutes)'))
    is_strict_anti_cheat = models.BooleanField(default=False, verbose_name=_('strict anti-cheat mode'),
                                              help_text=_('Require fullscreen, detect tab switching, and log violations realtime.'))
    max_violations = models.IntegerField(default=5, verbose_name=_('max violations'),
                                         help_text=_('Maximum violations before auto submit (0 = warning only).'))
    created_by = models.ForeignKey(User, verbose_name=_('created by'), on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name=_('updated at'), auto_now=True)

    @classmethod
    def generate_unique_pin(cls):
        import random
        for _ in range(20):
            pin = f"{random.randint(100000, 999999)}"
            if not cls.objects.filter(access_code=pin).exists():
                return pin
        import uuid
        return str(uuid.uuid4())[:8].upper()

    def is_currently_open(self):
        from django.utils import timezone
        if not self.is_active or self.is_locked:
            return False
        now = timezone.now()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('quiz source / exam')
        verbose_name_plural = _('quiz sources / exams')


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
