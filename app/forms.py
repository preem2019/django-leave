from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Employee, Department, Position, Role

# 1. ฟอร์มสำหรับปรับแต่งหน้า Login
class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'ชื่อผู้ใช้งาน'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'รหัสผ่าน'}))

# 2. ฟอร์มสำหรับหน้า "สร้างพนักงานใหม่"
class EmployeeCreationForm(forms.ModelForm):
    username = forms.CharField(max_length=100, required=True, label='ชื่อผู้ใช้ (สำหรับ Login)')
    password = forms.CharField(widget=forms.PasswordInput, required=True, label='รหัสผ่าน')
    first_name = forms.CharField(max_length=150, required=True, label='ชื่อจริง')
    last_name = forms.CharField(max_length=150, required=True, label='นามสกุล')
    department = forms.ModelChoiceField(queryset=Department.objects.all(), label='แผนก')
    position = forms.ModelChoiceField(queryset=Position.objects.all(), label='ตำแหน่ง')
    role = forms.ModelChoiceField(queryset=Role.objects.all(), label='บทบาท (Role)')

    class Meta:
        model = Employee
        fields = ['phone', 'email','line_user_id'] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select form-select-lg'})
            else:
                field.widget.attrs.update({'class': 'form-control form-control-lg', 'placeholder': field.label})

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data.get('email', '')
        )
        employee = super().save(commit=False)
        employee.user = user
        employee.name = f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}"
        employee.department = self.cleaned_data['department']
        employee.position = self.cleaned_data['position']
        employee.role = self.cleaned_data['role']
        if commit:
            employee.save()
        return employee

# 3. ฟอร์มสำหรับหน้า "แก้ไขข้อมูลพนักงาน" (เพิ่มใหม่)
class EmployeeUpdateForm(forms.ModelForm):
    # Fields from User model
    first_name = forms.CharField(max_length=150, required=True, label='ชื่อจริง')
    last_name = forms.CharField(max_length=150, required=True, label='นามสกุล')
    
    # Fields from Employee model
    department = forms.ModelChoiceField(queryset=Department.objects.all(), label='แผนก')
    position = forms.ModelChoiceField(queryset=Position.objects.all(), label='ตำแหน่ง')
    role = forms.ModelChoiceField(queryset=Role.objects.all(), label='บทบาท (Role)')

    class Meta:
        model = Employee
        fields = ['phone', 'email', 'department', 'position', 'role', 'line_user_id']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate form with current user data
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
        
        # Apply Bootstrap classes
        for field_name, field in self.fields.items():
            css_class = 'form-select form-select-lg' if isinstance(field.widget, forms.Select) else 'form-control form-control-lg'
            field.widget.attrs.update({'class': css_class})

    def save(self, commit=True):
        employee = super().save(commit=False)
        user = employee.user

        # Update User model
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        # Update Employee model
        employee.name = f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}"
        employee.department = self.cleaned_data['department']
        employee.position = self.cleaned_data['position']
        employee.role = self.cleaned_data['role']
        
        if commit:
            user.save()
            employee.save()
            
        return employee

# 4. ฟอร์มสำหรับหน้า "ตั้งค่าเว็บไซต์" (แบบไฟล์ JSON)
class SiteConfigurationForm(forms.Form):
    brand_name = forms.CharField(label='ชื่อแบรนด์ (ที่แสดงบน Navbar)', max_length=50)
    footer_text = forms.CharField(label='ข้อความท้ายเว็บ (Footer Text)', widget=forms.TextInput)
    color_primary = forms.CharField(label='สีหลัก (Navbar, Footer, ปุ่ม Login)', widget=forms.TextInput(attrs={'type': 'color'}), max_length=7)
    color_success = forms.CharField(label='สีสำเร็จ (อนุมัติ, บันทึก)', widget=forms.TextInput(attrs={'type': 'color'}), max_length=7)
    color_warning = forms.CharField(label='สีรอ/เตือน (รออนุมัติ)', widget=forms.TextInput(attrs={'type': 'color'}), max_length=7)
    color_danger = forms.CharField(label='สีอันตราย (ปฏิเสธ, ลบ)', widget=forms.TextInput(attrs={'type': 'color'}), max_length=7)

# ===== ⬇️ 5. (เพิ่มใหม่) ฟอร์มสำหรับ "แก้ไขข้อมูลส่วนตัว" (สำหรับพนักงานทั่วไป) =====
class UserProfileForm(forms.ModelForm):
    # เพิ่ม field email จาก Model 'User'
    email = forms.EmailField(
        label="อีเมล (สำหรับรับการแจ้งเตือน)",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-lg'})
    )

    class Meta:
        model = Employee
        # ระบุ field จาก Model 'Employee' ที่อนุญาตให้แก้ไข
        fields = ['phone', 'line_user_id']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'เช่น 081xxxxxxx'}),
            'line_user_id': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Line User ID (สำหรับรับแจ้งเตือน)'}),
        }
        labels = {
            'phone': 'เบอร์โทรศัพท์ (ไม่บังคับ)',
            'line_user_id': 'Line User ID (ไม่บังคับ)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ดึงค่า email ปัจจุบันจาก User model มาแสดงในฟอร์ม
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        # บันทึก field 'phone' และ 'line_user_id' ลง Model 'Employee'
        employee = super().save(commit=False)

        # บันทึก field 'email' ลง Model 'User'
        if self.instance and self.instance.user:
            user = self.instance.user
            user.email = self.cleaned_data['email']
            # อัปเดต email ใน Employee ให้ตรงกันด้วย (เพื่อความสอดคล้อง)
            employee.email = self.cleaned_data['email']
            if commit:
                user.save()

        if commit:
            employee.save()
        return employee
    
# ===== ⬇️ 6. ฟอร์มสำหรับ "เปลี่ยนรหัสผ่าน" =====
class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # กำหนดสไตล์กรอบสีดำและ Bootstrap
        common_attrs = {
            'class': 'form-control form-control-lg',
            'style': 'border-color: #000;'
        }

        self.fields['old_password'].widget = forms.PasswordInput(attrs={**common_attrs, 'placeholder': 'กรอกรหัสผ่านปัจจุบัน'})
        self.fields['old_password'].label = "รหัสผ่านปัจจุบัน"
        
        self.fields['new_password1'].widget = forms.PasswordInput(attrs={**common_attrs, 'placeholder': 'กรอกรหัสผ่านใหม่'})
        self.fields['new_password1'].label = "รหัสผ่านใหม่"

        self.fields['new_password2'].widget = forms.PasswordInput(attrs={**common_attrs, 'placeholder': 'ยืนยันรหัสผ่านใหม่'})
        self.fields['new_password2'].label = "ยืนยันรหัสผ่านใหม่"