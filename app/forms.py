from django import forms
from django.contrib.auth.forms import AuthenticationForm
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