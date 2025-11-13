from django.urls import path

from tea import views

urlpatterns = [
    path("", views.published_tea_list, name="published_tea_list"),
    path("teas/<int:tea_id>/", views.published_tea_detail, name="published_tea_detail"),
    path('signup/', views.signup_view, name='signup'),
    path('signin/', views.signin_view, name='signin'),
    path('signout/', views.signout_view, name='signout'),
    path('home/', views.home_view, name='home'),
]
