import re
import json
import csv
import io

from django.db import models
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.validators import MaxValueValidator, validate_comma_separated_integer_list
from django.utils.timezone import now
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from model_utils.managers import InheritanceManager
from django.contrib.auth.models import User

from .signals import csv_uploaded
from .validators import csv_file_validator


class CategoryManager(models.Manager):
    def new_category(self, category):
        new_category = self.create(category=re.sub(r"\s+", "-", category).lower())
        new_category.save()
        return new_category


class Category(models.Model):
    category = models.CharField(_("Категория"), max_length=250, blank=True, unique=True, null=True)
    objects = CategoryManager()

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")

    def __str__(self):
        return self.category


class Quiz(models.Model):
    title = models.CharField(_("Заголовок"), max_length=60)
    description = models.TextField(_("Описание"), blank=True)
    url = models.SlugField(_("ЧПУ"), max_length=60)
    category = models.ForeignKey(Category, verbose_name=_("Категория"), blank=True, null=True, on_delete=models.CASCADE)
    random_order = models.BooleanField(_("Случайный порядок"), default=False)
    max_questions = models.PositiveIntegerField(_("Максимум вопросов"), blank=True, null=True)
    answers_at_end = models.BooleanField(_("Ответы в конце"), default=False)
    exam_paper = models.BooleanField(_("Экзамен"), default=False)
    single_attempt = models.BooleanField(_("Одна попытка"), default=False)
    pass_mark = models.SmallIntegerField(_("Проходной балл"), default=0, validators=[MaxValueValidator(100)])
    success_text = models.TextField(_("Текст успеха"), blank=True)
    fail_text = models.TextField(_("Текст неудачи"), blank=True)
    draft = models.BooleanField(_("Черновик"), default=False)

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        self.url = re.sub(r"\s+", "-", self.url).lower()
        self.url = "".join(ch for ch in self.url if ch.isalnum() or ch == "-")
        if self.single_attempt:
            self.exam_paper = True
        if self.pass_mark > 100:
            raise ValidationError(_("%s выше 100") % self.pass_mark)
        super().save(force_insert, force_update, *args, **kwargs)

    class Meta:
        verbose_name = _("Тест")
        verbose_name_plural = _("Тесты")

    def __str__(self):
        return self.title

    def get_questions(self):
        return self.question_set.all().select_subclasses()

    @property
    def get_max_score(self):
        return self.get_questions().count()


class ProgressManager(models.Manager):
    def new_progress(self, user):
        new_progress = self.create(user=user, score="")
        new_progress.save()
        return new_progress


class Progress(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name=_("Пользователь"), on_delete=models.CASCADE)
    score = models.CharField(_("Баллы"), max_length=1024, validators=[validate_comma_separated_integer_list])
    correct_answer = models.CharField(_("Правильные ответы"), max_length=10)
    wrong_answer = models.CharField(_("Неправильные ответы"), max_length=10)

    objects = ProgressManager()

    class Meta:
        verbose_name = _("Прогресс")
        verbose_name_plural = _("Прогрессы")

    def __str__(self):
        return f"{self.user.username} — {self.score}"

    @property
    def list_all_cat_scores(self):
        score_before = self.score
        output = {}
        for cat in Category.objects.all():
            to_find = re.escape(cat.category) + r",(\d+),(\d+),"
            match = re.search(to_find, self.score, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                possible = int(match.group(2))
                try:
                    percent = int(round((score / possible) * 100))
                except ZeroDivisionError:
                    percent = 0
                output[cat.category] = [score, possible, percent]
            else:
                self.score += f"{cat.category},0,0,"
                output[cat.category] = [0, 0, 0]
        if len(self.score) > len(score_before):
            self.save()
        return output

    def show_exams(self):
        return Sitting.objects.filter(user=self.user, complete=True)

    def update_score(self, quiz, score, possible):
        cat = quiz.category.category
        updated = False
        score_list = self.score.split(",")
        new_score = ""

        for i in range(0, len(score_list)-1, 3):
            if score_list[i] == cat:
                current = int(score_list[i+1]) + score
                max_score = int(score_list[i+2]) + possible
                new_score += f"{cat},{current},{max_score},"
                updated = True
            else:
                new_score += f"{score_list[i]},{score_list[i+1]},{score_list[i+2]},"

        if not updated:
            new_score += f"{cat},{score},{possible},"

        self.score = new_score
        self.save()


class SittingManager(models.Manager):
    def new_sitting(self, user, quiz):
        questions = quiz.question_set.all().select_subclasses()
        if quiz.random_order:
            questions = questions.order_by("?")
        q_ids = [q.id for q in questions]
        if quiz.max_questions and len(q_ids) > quiz.max_questions:
            q_ids = q_ids[: quiz.max_questions]
        if not q_ids:
            raise ImproperlyConfigured(_("Нет вопросов для теста"))
        order = ",".join(map(str, q_ids)) + ","
        return self.create(
            user=user,
            quiz=quiz,
            question_order=order,
            question_list=order,
            incorrect_questions="",
            current_score=0,
            complete=False,
            user_answers="{}",
        )

    def user_sitting(self, user, quiz):
        if quiz.single_attempt and self.filter(user=user, quiz=quiz, complete=True).exists():
            return False
        sitter = self.filter(user=user, quiz=quiz, complete=False).first()
        return sitter if sitter else self.new_sitting(user, quiz)


class Sitting(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Пользователь"), on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, verbose_name=_("Тест"), on_delete=models.CASCADE)
    question_order = models.CharField(_("Порядок вопросов"), max_length=1024, validators=[validate_comma_separated_integer_list])
    question_list = models.CharField(_("Список вопросов"), max_length=1024, validators=[validate_comma_separated_integer_list])
    incorrect_questions = models.CharField(_("Неправильные вопросы"), max_length=1024, blank=True, validators=[validate_comma_separated_integer_list])
    current_score = models.IntegerField(_("Текущий счёт"))
    complete = models.BooleanField(_("Завершено"), default=False)
    user_answers = models.TextField(_("Ответы пользователя"), default="{}", blank=True)
    start = models.DateTimeField(_("Начало"), auto_now_add=True)
    end = models.DateTimeField(_("Окончание"), blank=True, null=True)

    objects = SittingManager()

    class Meta:
        verbose_name = _("Сессия")
        verbose_name_plural = _("Сессии")

    def get_first_question(self):
        if not self.question_list:
            return None
        question_ids = [x for x in self.question_list.split(",") if x.strip()]
        if not question_ids:
            return None
        try:
            return Question.objects.get_subclass(id=int(question_ids[0]))
        except Question.DoesNotExist:
            return None

    def remove_first_question(self):
        if not self.question_list:
            return
        self.question_list = ",".join(self.question_list.split(",")[1:])
        self.save()

    def add_user_answer(self, question, guess):
        data = json.loads(self.user_answers)
        data[str(question.id)] = guess
        self.user_answers = json.dumps(data)
        self.save()

    def add_incorrect_question(self, question):
        if self.incorrect_questions:
            self.incorrect_questions += ","
        self.incorrect_questions += str(question.id)
        self.save()

    def add_to_score(self, points):
        self.current_score += int(points)
        self.save()

    def progress(self):
        answered = len(json.loads(self.user_answers))
        total = len([x for x in self.question_order.split(",") if x])
        return answered, total


class Question(models.Model):
    quiz = models.ManyToManyField(Quiz, verbose_name=_("Тесты"), blank=True)
    category = models.ForeignKey(Category, verbose_name=_("Категория"), blank=True, null=True, on_delete=models.CASCADE)
    figure = models.ImageField(_("Изображение"), upload_to="uploads/%Y/%m/%d", blank=True, null=True)
    content = models.CharField(_("Вопрос"), max_length=1000, help_text=_("Текст вопроса"), blank=False)
    explanation = models.TextField(_("Пояснение"), max_length=2000, help_text=_("Пояснение после ответа"), blank=True)

    objects = InheritanceManager()

    class Meta:
        verbose_name = _("Вопрос")
        verbose_name_plural = _("Вопросы")
        ordering = ["category"]

    def __str__(self):
        return self.content


def upload_csv_file(instance, filename):
    qs = instance.__class__.objects.filter(user=instance.user)
    num = qs.last().id + 1 if qs.exists() else 1
    return f"csv/{num}/{instance.user.username}/{filename}"


class CSVUpload(models.Model):
    title = models.CharField(_("Загрузка CSV"), max_length=100, blank=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Пользователь"), on_delete=models.CASCADE)
    file = models.FileField(_("Файл CSV"), upload_to=upload_csv_file, validators=[csv_file_validator])
    completed = models.BooleanField(_("Завершено"), default=False)

    class Meta:
        verbose_name = _("Загрузка CSV")
        verbose_name_plural = _("Загрузки CSV")

    def __str__(self):
        return f"{self.user.username} — {self.title}"


def create_user(data):
    user = User.objects.create_user(
        username=data.get("username"),
        email=data.get("email"),
        password=data.get("password"),
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
    )
    user.is_staff = False
    user.is_superuser = False
    user.save()


def convert_header(csvHeader):
    header = csvHeader[0]
    return [x.replace(" ", "_").lower() for x in header.split(",")]


def csv_upload_post_save(sender, instance, created, **kwargs):
    if not instance.completed:
        decoded = instance.file.read().decode("utf-8")
        reader = csv.reader(io.StringIO(decoded), delimiter=";", quotechar="|")
        header = next(reader)
        cols = convert_header([header])
        parsed = []
        for row in reader:
            parts = row[0].split(",")
            data = {cols[i]: parts[i] for i in range(len(parts))}
            create_user(data)
            parsed.append(data)
        csv_uploaded.send(sender=sender, user=instance.user, csv_file_list=parsed)
        instance.completed = True
        instance.save()


post_save.connect(csv_upload_post_save, sender=CSVUpload)

