from django.contrib import admin
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import ugettext_lazy as _

from .models import Quiz, Category, Question, Progress, CSVUpload, Sitting
from mcq.models import MCQQuestion, Answer


# — Русскоязычные заголовки админки
admin.site.site_header = _("Панель управления ТестПлатформа")
admin.site.site_title  = _("Админка ТестПлатформа")
admin.site.index_title = _("Добро пожаловать")


# — Переводим метки моделей
Sitting._meta.verbose_name = _('Сессия')
Sitting._meta.verbose_name_plural = _('Сессии')

Category._meta.verbose_name = _('Категория')
Category._meta.verbose_name_plural = _('Категории')
Category._meta.get_field('category').verbose_name = _('Название')

Quiz._meta.verbose_name = _('Тест')
Quiz._meta.verbose_name_plural = _('Тесты')
Quiz._meta.get_field('title').verbose_name = _('Заголовок')

Question._meta.verbose_name = _('Вопрос')
Question._meta.verbose_name_plural = _('Вопросы')
Question._meta.get_field('content').verbose_name = _('Вопрос')

Progress._meta.verbose_name = _('Прогресс')
Progress._meta.verbose_name_plural = _('Прогрессы')

CSVUpload._meta.verbose_name = _('Загрузка CSV')
CSVUpload._meta.verbose_name_plural = _('Загрузки CSV')

MCQQuestion._meta.verbose_name = _('Вопрос')
MCQQuestion._meta.verbose_name_plural = _('Вопросы')

Answer._meta.verbose_name = _('Ответ')
Answer._meta.verbose_name_plural = _('Ответы')


# — Inline для ответов
class AnswerInline(admin.TabularInline):
    model = Answer


# — Форма для Quiz с русскоязычной меткой поля вопросов
class QuizAdminForm(forms.ModelForm):
    class Meta:
        model = Quiz
        exclude = []

    questions = forms.ModelMultipleChoiceField(
        queryset=Question.objects.all().select_subclasses(),
        required=False,
        label=_("Вопросы"),
        widget=FilteredSelectMultiple(
            verbose_name=_("Вопросы"),
            is_stacked=False
        )
    )

    def __init__(self, *args, **kwargs):
        super(QuizAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['questions'].initial = \
                self.instance.question_set.all().select_subclasses()

    def save(self, commit=True):
        quiz = super(QuizAdminForm, self).save(commit=False)
        quiz.save()
        quiz.question_set.set(self.cleaned_data['questions'])
        self.save_m2m()
        return quiz


# — Регистрация моделей в админке
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    form = QuizAdminForm
    list_display = ('title', 'category',)
    list_filter  = ('category',)
    search_fields = ('description', 'category',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ('category',)


@admin.register(MCQQuestion)
class MCQuestionAdmin(admin.ModelAdmin):
    list_display      = ('content', 'category',)
    list_filter       = ('category',)
    fields            = ('content', 'category',
                         'figure', 'quiz', 'explanation', 'answer_order')
    search_fields     = ('content', 'explanation')
    filter_horizontal = ('quiz',)
    inlines           = [AnswerInline]


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    search_fields = ('user', 'score',)


@admin.register(Sitting)
class SittingAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'complete', 'score_display')

    def score_display(self, obj):
        return obj.get_percent_correct
    score_display.short_description = _('Результат (%)')



