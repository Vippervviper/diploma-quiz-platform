from django.conf.urls import url
from .views import QuizListView, CategoriesListView, \
    ViewQuizListByCategory, QuizUserProgressView, QuizMarkingList, \
    QuizMarkingDetail, QuizDetailView, QuizTake, index, \
    login_user, register_user
from django.contrib.auth import views as auth_views

urlpatterns = [
    url(regex=r'^$', view=index, name='index'),
    url(regex=r'^login/$', view=login_user, name='login'),
    # Теперь при выходе — редирект на страницу входа
    url(
        regex=r'^logout/$',
        view=auth_views.LogoutView.as_view(next_page='/login/'),
        name='logout'
    ),
    url(regex=r'^register/$', view=register_user, name='register'),

    url(regex=r'^quizzes/$',
        view=QuizListView.as_view(),
        name='quiz_index'),

    url(regex=r'^category/$',
        view=CategoriesListView.as_view(),
        name='quiz_category_list_all'),

    url(regex=r'^category/(?P<category_name>[\w|\W-]+)/$',
        view=ViewQuizListByCategory.as_view(),
        name='quiz_category_list_matching'),

    url(regex=r'^progress/$',
        view=QuizUserProgressView.as_view(),
        name='quiz_progress'),

    url(regex=r'^marking/$',
        view=QuizMarkingList.as_view(),
        name='quiz_marking'),

    url(regex=r'^marking/(?P<pk>[\d.]+)/$',
        view=QuizMarkingDetail.as_view(),
        name='quiz_marking_detail'),

    url(regex=r'^(?P<slug>[\w-]+)/$',
        view=QuizDetailView.as_view(),
        name='quiz_start_page'),

    url(regex=r'^(?P<quiz_name>[\w-]+)/take/$',
        view=QuizTake.as_view(),
        name='quiz_question'),
]

