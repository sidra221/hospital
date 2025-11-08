from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # حقل إضافي لتحديد ما إذا المستخدم طبيب
    is_doctor = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class DoctorProfile(models.Model):
    """ملف الطبيب ببيانات واقعية"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=120, blank=True)  # مثال: قلبية، عظمية
    years_of_experience = models.PositiveIntegerField(default=0)
    clinic_address = models.CharField(max_length=255, blank=True)
    clinic_city = models.CharField(max_length=120, blank=True)
    clinic_phone = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)
    certifications = models.TextField(blank=True)  # قائمة نصية أو روابط شهادات
    certificate_image = models.ImageField(upload_to='doctors/certificates/', blank=True, null=True)

    def __str__(self):
        return f"DoctorProfile({self.user.username})"