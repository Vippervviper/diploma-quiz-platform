from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class McqConfig(AppConfig):
    name = 'mcq'
    verbose_name = _('Вопросы и ответы')

