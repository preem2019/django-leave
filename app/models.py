from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ==============================================================================
# 1. Core Models: Department, Position, Role
# ==============================================================================

class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=255)

    def __str__(self):
        return self.department_name

class Position(models.Model):
    position_id = models.AutoField(primary_key=True)
    position_name = models.CharField(max_length=255)
    position_level = models.IntegerField() 

    def __str__(self):
        return self.position_name

class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=255)

    def __str__(self):
        return self.role_name

# ==============================================================================
# 2. Employee Model
# ==============================================================================

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    line_user_id = models.CharField(max_length=255, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, db_column='department_id')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, db_column='position_id')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role_id')

    def __str__(self):
        return self.name

# ==============================================================================
# 3. Leave Request & Approval Models
# ==============================================================================

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Info Requested', 'Info Requested'),
    ]
    DURATION_CHOICES = [('3 ชั่วโมง', '3 ชั่วโมง'), ('ครึ่งวัน', 'ครึ่งวัน'), ('เต็มวัน', 'เต็มวัน')]
    
    request_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    leave_date = models.DateField(default=timezone.now)
    leave_duration = models.CharField(max_length=10, choices=DURATION_CHOICES, default='3 ชั่วโมง')
    
    request_datetime = models.DateTimeField(default=timezone.now)
    current_approver_role = models.CharField(max_length=20, default='manager')

    info_request_comment = models.TextField(null=True, blank=True)
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)

    def __str__(self):
        return f"Request ID: {self.request_id} by {self.employee.name}"

    def get_detailed_status(self):
        if self.status == 'Approved':
            return {'text': 'อนุมัติแล้ว', 'color': 'success'}
        if self.status == 'Rejected':
            return {'text': 'ถูกปฏิเสธ', 'color': 'danger'}
        if self.status == 'Info Requested':
            return {'text': 'รอข้อมูลเพิ่มเติม', 'color': 'info'}

        if self.status == 'Pending':
            if self.current_approver_role == 'manager':
                return {'text': 'รอ Manager อนุมัติ', 'color': 'warning'}
            if self.current_approver_role == 'supervisor':
                return {'text': 'รอ Supervisor อนุมัติ', 'color': 'primary'}
            if self.current_approver_role == 'hr_safety':
                return {'text': 'รอ HR/Safety อนุมัติ', 'color': 'info'}
        
        return {'text': self.status, 'color': 'secondary'}

    @property
    def ordered_approval_history(self):
        return self.approvalhistory_set.order_by('approval_order', 'approval_date')

class ApprovalHistory(models.Model):
    STATUS_CHOICES = [('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Pending', 'Pending')]
    history_id = models.AutoField(primary_key=True)
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, db_column='request_id')
    approver = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='approver_id')
    approval_order = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    approval_date = models.DateField(null=True, blank=True)
    approval_time = models.TimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"History for Request ID: {self.request.request_id}"

# ==============================================================================
# 4. In-Out History Model (Updated)
# ==============================================================================

class InOutHistory(models.Model):
    STATUS_CHOICES = [
        ('OUT', 'อยู่ข้างนอก'), 
        ('COMPLETED', 'กลับมาแล้ว')
    ]

    history_id = models.AutoField(primary_key=True)
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, db_column='request_id')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='in_out_histories')
    time_out = models.DateTimeField(null=True, blank=True)
    time_in = models.DateTimeField(null=True, blank=True)
    
    guard = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='guard_histories',
        db_column='guard_id',
        limit_choices_to={'role__role_name__iexact': 'security'} 
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OUT', null=True)


    def __str__(self):
        return f"InOut for {self.employee.name} on request {self.request.request_id}"

