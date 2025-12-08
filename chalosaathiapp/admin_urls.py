# admin_urls.py
from django.urls import path
from . import views
from .views import admin_login, admin_logout, add_admin, admin_view_bookings, admin_view_feedback, delete_feedback
urlpatterns = [
    path('admin_login',views.admin_login, name='admin_login'),
    path('admin_panel',views.admin_panel, name='admin_panel'),
    path("users/", views.admin_user_list, name="admin_user_list"),
    path("users/<int:user_id>/", views.admin_user_detail, name="admin_user_detail"),
    path("users/<int:user_id>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("users/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),
    path("search-users-by-city/", views.search_users_by_city, name="search_users_by_city"),
    path('', admin_login, name='admin_login'),
    path('logout/', admin_logout, name='admin_logout'),
    path('add-admin/', add_admin, name='add_admin'),
    path('admin-bookings/', admin_view_bookings, name='admin_view_bookings'),
    path('admin-feedback/', admin_view_feedback, name='admin_view_feedback'),
    path('delete-feedback/<int:id>/', delete_feedback, name='delete_feedback'),
]
