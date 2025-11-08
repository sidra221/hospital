import django
import os
import random
from datetime import datetime, timedelta
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import DoctorProfile
from patients.models import PatientProfile, MedicalRecord, Appointment

User = get_user_model()
fake = Faker('ar_EG')  # بيانات عربية

# --- إنشاء أطباء ---
def create_doctors(num=10):
    for i in range(num):
        username = f"doctor{i+1}"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "is_doctor": True,
                "email": f"{username}@example.com",
            }
        )
        if created:
            user.set_password("123456")
            user.save()

        DoctorProfile.objects.get_or_create(
            user=user,
            defaults={
                "specialty": random.choice(["قلبية", "عظمية", "باطنية", "جلدية", "أطفال", "عيون", "أسنان"]),
                "years_of_experience": random.randint(2, 25),
                "clinic_address": fake.address(),
                "clinic_city": fake.city(),
                "clinic_phone": fake.phone_number(),
                "bio": fake.text(max_nb_chars=200),
                "certifications": fake.text(max_nb_chars=150),
            }
        )
    print(f"✅ تم إنشاء {num} طبيب بنجاح.")

# --- إنشاء مرضى ---
def create_patients(num=50):
    for i in range(num):
        username = f"patient{i+1}"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_doctor": False, "email": f"{username}@example.com"}
        )
        if created:
            user.set_password("123456")
            user.save()

        patient_profile, _ = PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                "national_id": str(fake.unique.random_int(min=1000000000, max=9999999999)),
                "phone_number": fake.phone_number(),
                "date_of_birth": fake.date_of_birth(minimum_age=10, maximum_age=80),
                "address": fake.address(),
                "medical_record_number": f"MRN-{random.randint(1000, 9999)}",
            }
        )

        # سجل طبي للمريض
        MedicalRecord.objects.get_or_create(
            patient=patient_profile,
            defaults={
                "past_diseases": fake.sentence(),
                "lab_tests": fake.sentence(),
                "imaging_reports": fake.sentence(),
                "chronic_diseases": random.choice(["سكري", "ضغط", "لا يوجد", "ربو", "أمراض قلبية"]),
            }
        )
    print(f"✅ تم إنشاء {num} مريض وسجلاتهم الطبية.")

# --- إنشاء مواعيد ---
def create_appointments(num=60):
    doctors = list(User.objects.filter(is_doctor=True))
    patients = list(PatientProfile.objects.all())

    for _ in range(num):
        doctor = random.choice(doctors)
        patient = random.choice(patients)
        appointment_date = datetime.now() + timedelta(days=random.randint(-30, 30))
        Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_datetime=appointment_date,
            reason=random.choice([
                "فحص دوري", "ألم صدري", "سعال", "متابعة علاج", "استشارة عامة", "تطعيم"
            ]),
            status=random.choice(["pending", "confirmed", "completed", "cancelled"]),
        )
    print(f"✅ تم إنشاء {num} موعد بنجاح.")

# --- التنفيذ ---
if __name__ == "__main__":
    create_doctors()
    create_patients()
    create_appointments()
    print("done!")
