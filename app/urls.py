from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm

app_name = 'app'

urlpatterns = [
    # --- หน้าหลัก ---
    path('', views.dashboard, name='dashboard'),

    # --- URL สำหรับการจัดการคำขอ (สำหรับพนักงาน) ---
    path('request/new/', views.create_leave_request, name='create-request'),
    path('requests/pending/', views.pending_requests_view, name='requests-pending'),
    path('requests/approved/', views.approved_requests_view, name='requests-approved'),
    path('requests/rejected/', views.rejected_requests_view, name='requests-rejected'),
    path('request/<int:request_id>/provide-info/', views.provide_info_view, name='provide-info'),

    # --- URL สำหรับผู้อนุมัติ ---
    path('approval-inbox/', views.approval_inbox, name='approval-inbox'),
    path('approval/process/<int:history_id>/', views.process_approval, name='process-approval'),
    
    # --- URL สำหรับ รปภ. ---
    path('security/dashboard/', views.security_dashboard, name='security-dashboard'),
    path('security/record-out/<int:request_id>/', views.record_time_out, name='record-time-out'),
    path('security/record-in/<int:history_id>/', views.record_time_in, name='record-time-in'),

    # --- URL สำหรับรายงาน (HR/Admin) ---
    path('reports/in-out-history/', views.in_out_history_report, name='in-out-history-report'),
    # --- START: บรรทัดที่เพิ่มเข้ามาเพื่อแก้ Error ---
    path('reports/in-out-history/export/', views.export_in_out_history_excel, name='export-in-out-history-excel'),
    # --- END ---

    # --- URL สำหรับการจัดการพนักงาน (สำหรับ HR/Admin) ---
    path('users/', views.employee_list_view, name='employee-list'),
    path('user/create/', views.create_user_view, name='create-user'),
    path('user/edit/<int:employee_id>/', views.edit_employee_view, name='edit-employee'),
    path('user/delete/<int:employee_id>/', views.delete_employee_view, name='delete-employee'),
    # ===== START: บรรทัดที่เพิ่มใหม่สำหรับหน้าตั้งค่า =====
    path('settings/', views.site_settings_view, name='site-settings'),
    # ===== END =====

    # --- URL สำหรับการยืนยันตัวตน (Login/Logout) ---
    path('login/', auth_views.LoginView.as_view(
        template_name='app/login.html', 
        authentication_form=CustomAuthenticationForm
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- URL สำหรับทดสอบอีเมล ---
    path('test-email/<int:request_id>/', views.test_email_view, name='test-email'),
]

