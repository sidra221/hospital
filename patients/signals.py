from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PatientProfile, MedicalRecord

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_patient_profile(sender, instance, created, **kwargs):
    if created and not instance.is_doctor:
        profile = PatientProfile.objects.create(user=instance)
        MedicalRecord.objects.create(patient=profile)
