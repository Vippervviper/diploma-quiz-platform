from django import forms
from .models import Question, Answer

class QuestionForm(forms.Form):
    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        choices = [(answer.id, answer.text) for answer in question.get_answers_list()]
        self.fields[f"question-{question.id}"] = forms.ChoiceField(
            choices=choices,
            widget=forms.RadioSelect,
            label=question.content
        )


