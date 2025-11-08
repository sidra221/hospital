from django.conf import settings
from django.db import models

class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile'
    )
    national_id = models.CharField(max_length=30, unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    medical_record_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.national_id}"


class MedicalRecord(models.Model):
    """المعلومات المرضية للمريض - يعدلها الطبيب فقط"""
    patient = models.OneToOneField(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='medical_record'
    )
    past_diseases = models.TextField(blank=True)
    lab_tests = models.TextField(blank=True)
    imaging_reports = models.TextField(blank=True)
    chronic_diseases = models.TextField(blank=True)
    medications = models.TextField(blank=True, help_text="الأدوية التي يتناولها المريض")

    def __str__(self):
        return f"MedicalRecord for {self.patient.user.username}"


class Appointment(models.Model):
    """موعد معاينة بين مريض وطبيب"""
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    appointment_datetime = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_datetime']

    def __str__(self):
        return f"Appt {self.patient.user.username} -> {getattr(self.doctor, 'username', self.doctor_id)} at {self.appointment_datetime}"
