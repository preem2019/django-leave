from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm

app_name = 'app'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Leave Request URLs
    path('request/new/', views.create_leave_request, name='create-request'),
    path('requests/pending/', views.pending_requests_view, name='requests-pending'),
    path('requests/approved/', views.approved_requests_view, name='requests-approved'),
    path('requests/rejected/', views.rejected_requests_view, name='requests-rejected'),
    path('request/provide-info/<int:request_id>/', views.provide_info_view, name='provide-info'),

    # Approval URLs
    path('approval-inbox/', views.approval_inbox, name='approval-inbox'),
    path('approval/process/<int:history_id>/', views.process_approval, name='process-approval'),
    
    # Employee Management URLs
    path('users/', views.employee_list_view, name='employee-list'),
    path('user/create/', views.create_user_view, name='create-user'),
    path('user/edit/<int:employee_id>/', views.edit_employee_view, name='edit-employee'),
    path('user/delete/<int:employee_id>/', views.delete_employee_view, name='delete-employee'),

    # Auth URLs
    path('login/', auth_views.LoginView.as_view(
        template_name='app/login.html', 
        authentication_form=CustomAuthenticationForm
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

