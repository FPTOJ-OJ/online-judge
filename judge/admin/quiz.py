from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, path
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
import json
from django import forms
from django.urls import reverse_lazy
from django.db import models
from django.forms import Textarea, CheckboxSelectMultiple
from judge.widgets import AdminMartorWidget

from judge.models.quiz import QuizTag, QuizSource, QuizQuestion, QuizOption, QuizSession
from judge.models.profile import Organization

class QuizOptionInline(admin.TabularInline):
    model = QuizOption
    extra = 4
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'style': 'width: 100%; min-width: 350px; font-family: monospace;'})},
    }

class QuizQuestionAdminForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = '__all__'
        widgets = {
            'content': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('problem_preview')}),
            'explanation': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('problem_preview')}),
        }

@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    form = QuizQuestionAdminForm
    list_display = ('id', 'content_preview', 'type', 'difficulty', 'option_summary', 'source', 'tag_list', 'created_by', 'created_at')
    list_filter = ('type', 'difficulty', 'tags', 'source')
    list_editable = ('type', 'difficulty')
    search_fields = ('content', 'explanation', 'tags__name', 'source__name')
    inlines = [QuizOptionInline]
    raw_id_fields = ('created_by',)
    autocomplete_fields = ('source',)
    actions = ['export_to_json']

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = _('Question Content')

    def tag_list(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    tag_list.short_description = _('Tags')

    def option_summary(self, obj):
        total = obj.options.count()
        correct = obj.options.filter(is_correct=True).count()
        return f"{correct}/{total} đúng"
    option_summary.short_description = _('Options (Correct/Total)')

    @admin.action(description=_('Export selected questions to JSON'))
    def export_to_json(self, request, queryset):
        data = []
        for q in queryset.prefetch_related('options', 'tags').select_related('source'):
            options_data = []
            for opt in q.options.all():
                options_data.append({
                    'label': opt.label,
                    'content': opt.content,
                    'is_correct': opt.is_correct
                })
            
            data.append({
                'content': q.content,
                'type': q.type,
                'difficulty': q.difficulty,
                'explanation': q.explanation,
                'source': q.source.name if q.source else '',
                'tags': [t.name for t in q.tags.all()],
                'options': options_data
            })
        
        response = HttpResponse(json.dumps(data, indent=2, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="exported_questions.json"'
        return response

@admin.register(QuizTag)
class QuizTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'question_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = _('Questions Count')

class QuizSourceAdminForm(forms.ModelForm):
    class Meta:
        model = QuizSource
        fields = '__all__'
        widgets = {
            'organizations': CheckboxSelectMultiple(),
        }

@admin.register(QuizSource)
class QuizSourceAdmin(admin.ModelAdmin):
    form = QuizSourceAdminForm
    list_display = ('name', 'question_count', 'is_visible', 'is_featured', 'require_login', 'is_locked', 'is_organization_only', 'default_duration', 'created_by', 'created_at')
    list_filter = ('is_visible', 'is_featured', 'require_login', 'is_locked', 'is_organization_only', 'organizations')
    search_fields = ('name', 'description')
    list_editable = ('is_visible', 'is_featured', 'require_login', 'is_locked', 'is_organization_only')
    filter_horizontal = ('organizations',)
    actions = ['mark_visible', 'mark_hidden', 'mark_featured', 'mark_locked', 'mark_unlocked']

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'default_duration')
        }),
        (_('Visibility & Access'), {
            'fields': ('is_visible', 'is_featured', 'require_login', 'is_locked', 'is_organization_only', 'organizations'),
            'description': _('Control who can see and access this exam.'),
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = _('Questions Count')

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description=_('Mark selected exams as visible'))
    def mark_visible(self, request, queryset):
        updated = queryset.update(is_visible=True)
        self.message_user(request, f"Đã hiện {updated} đề thi.")

    @admin.action(description=_('Mark selected exams as hidden'))
    def mark_hidden(self, request, queryset):
        updated = queryset.update(is_visible=False)
        self.message_user(request, f"Đã ẩn {updated} đề thi.")

    @admin.action(description=_('Mark selected exams as featured'))
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"Đã gắn dấu nổi bật cho {updated} đề thi.")

    @admin.action(description=_('Lock selected exams'))
    def mark_locked(self, request, queryset):
        updated = queryset.update(is_locked=True)
        self.message_user(request, f"Đã khóa {updated} đề thi.")

    @admin.action(description=_('Unlock selected exams'))
    def mark_unlocked(self, request, queryset):
        updated = queryset.update(is_locked=False)
        self.message_user(request, f"Đã mở khóa {updated} đề thi.")

@admin.register(QuizOption)
class QuizOptionAdmin(admin.ModelAdmin):
    list_display = ('question', 'label', 'content', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('content',)

@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'current_index', 'completed', 'score', 'created_at')
    list_filter = ('completed', 'created_at')
    search_fields = ('user__username', 'session_key')
    actions = ['mark_completed', 'recalculate_score']

    @admin.action(description=_('Mark selected sessions as completed'))
    def mark_completed(self, request, queryset):
        updated = queryset.update(completed=True)
        self.message_user(request, f"Đã đánh dấu hoàn thành cho {updated} phiên làm bài.")

    @admin.action(description=_('Recalculate scores for selected sessions'))
    def recalculate_score(self, request, queryset):
        from judge.models.quiz import QuizQuestion
        updated_count = 0
        for session in queryset:
            questions = QuizQuestion.objects.filter(id__in=session.questions).prefetch_related('options', 'tags')
            q_map = {q.id: q for q in questions}
            
            meta = session.answers.get('__meta__', {})
            is_exam = 'orientation' in meta
            orientation = meta.get('orientation', 'KHMT')
            
            if is_exam:
                graded_part1 = []
                graded_part2 = []
                for q_id in session.questions:
                    q = q_map.get(q_id)
                    if not q:
                        continue
                    q_tags = [t.name.lower() for t in q.tags.all()]
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
                session.score = min(10.0, part1_score + part2_score)
            else:
                total_score = 0.0
                for q_id in session.questions:
                    q = q_map.get(q_id)
                    if not q:
                        continue
                    ans = session.answers.get(str(q_id))
                    if q.type == 'choice':
                        correct_opt = q.options.filter(is_correct=True).first()
                        correct_label = correct_opt.label if correct_opt else 'A'
                        if ans == correct_label:
                            total_score += 1.0
                    elif q.type == 'tf':
                        if not isinstance(ans, dict):
                            continue
                        correct_map = {opt.label: opt.is_correct for opt in q.options.all()}
                        correct_count = 0
                        for lbl, correct_val in correct_map.items():
                            if ans.get(lbl) == correct_val:
                                correct_count += 1
                        if correct_count == 1:
                            total_score += 0.1
                        elif correct_count == 2:
                            total_score += 0.25
                        elif correct_count == 3:
                            total_score += 0.5
                        elif correct_count == 4:
                            total_score += 1.0
                session.score = total_score
                
            session.save()
            updated_count += 1
            
        self.message_user(request, f"Đã tính toán lại điểm số cho {updated_count} phiên làm bài.")

