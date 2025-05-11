from django import forms
from django.forms.widgets import RadioSelect


class QuestionForm(forms.Form):
    def __init__(self, question=None, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        if question is not None:
            choice_list = [x for x in question.get_answers_list()]
            self.fields["answers"] = forms.ChoiceField(choices=choice_list, widget=RadioSelect)


