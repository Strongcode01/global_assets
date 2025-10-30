from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Main Pages
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("career/", views.career, name="career"),
    path("contact/", views.contact, name="contact"),
    path("mission/", views.mission, name="mission"),
    path("wallet/", views.wallet, name="wallet"),
    path("blank/", views.blank, name="blank"),

    # Blog
    path("blog/", views.blog, name="blog"),
    path("blog/detail/", views.blog_detail, name="blog_detail"),
]
