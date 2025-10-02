from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    # Main Dashboard URL
    path('', views.dashboard, name='dashboard'),
    
    # URLs for employees to create requests
    path('request/new/', views.create_leave_request, name='create-request'),
    
    # URLs for viewing requests filtered by status
    path('requests/pending/', views.pending_requests_view, name='requests-pending'),
    path('requests/approved/', views.approved_requests_view, name='requests-approved'),
    path('requests/rejected/', views.rejected_requests_view, name='requests-rejected'),

    # URLs for approvers
    path('approval-inbox/', views.approval_inbox, name='approval-inbox'),
    path('approval/process/<int:history_id>/', views.process_approval, name='process-approval'),
]

