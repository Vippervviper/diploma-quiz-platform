from django.urls import path
from .views import (
    QuizListView,
    CategoriesListView,
    ViewQuizListByCategory,
    QuizUserProgressView,
    QuizMarkingList,
    QuizMarkingDetail,
    QuizDetailView,
    QuizTake,
    index,
    login_user,
    register_user,
    quiz_result,
)
from django.contrib.auth import views as auth_views

app_name = 'quiz'

urlpatterns = [
    path('', index, name='index'),
    path('login/', login_user, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', register_user, name='register'),

    path('quizzes/', QuizListView.as_view(), name='quiz_index'),

    path('category/', CategoriesListView.as_view(), name='quiz_category_list_all'),
    path('category/<str:category_name>/', ViewQuizListByCategory.as_view(), name='quiz_category_list_matching'),

    path('progress/', QuizUserProgressView.as_view(), name='quiz_progress'),

    path('marking/', QuizMarkingList.as_view(), name='quiz_marking'),
    path('marking/<int:pk>/', QuizMarkingDetail.as_view(), name='quiz_marking_detail'),

    path('<slug:slug>/', QuizDetailView.as_view(), name='quiz_start_page'),
    path('<slug:quiz_name>/take/', QuizTake.as_view(), name='quiz_question'),

    # Добавлен маршрут отображения результатов
    path('<slug:quiz_name>/result/<int:sitting_id>/', quiz_result, name='quiz_result'),
]

