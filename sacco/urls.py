from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('apply_loan/', views.apply_for_loan, name='apply_for_loan'),
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('approve_loan/<int:loan_id>/', views.approve_loan, name='approve_loan'),
    path('reject_loan/<int:loan_id>/', views.reject_loan, name='reject_loan'),
    path('record_saving/', views.record_saving, name='record_saving'),
    path('record_repayment/', views.record_repayment, name='record_repayment'),
    path('approve_member/<int:member_id>/', views.approve_member, name='approve_member'),
    path('user_loans/<int:member_id>/', views.user_loans_view, name='user_loans'),
]
