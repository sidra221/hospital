from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import PatientProfile, MedicalRecord, Appointment

class PatientProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    medical_record = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PatientProfile
        fields = [
            'id', 'username', 'email',
            'national_id', 'phone_number',
            'date_of_birth', 'address', 'medical_record_number',
            'medical_record'
        ]

    def get_medical_record(self, obj):
        if hasattr(obj, 'medical_record') and obj.medical_record:
            return MedicalRecordSerializer(obj.medical_record).data
        return None

class PatientProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer لتحديث بيانات المريض من قبله"""
    class Meta:
        model = PatientProfile
        fields = [
            'national_id', 'phone_number',
            'date_of_birth', 'address', 'medical_record_number'
        ]
        extra_kwargs = {
            'national_id': {'required': False},
            'phone_number': {'required': False},
            'date_of_birth': {'required': False},
            'address': {'required': False},
            'medical_record_number': {'required': False}
        }


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ['past_diseases', 'lab_tests', 'imaging_reports', 'chronic_diseases', 'medications']


class AppointmentSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(source='patient.id', read_only=True)
    patient_username = serializers.CharField(source='patient.user.username', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    doctor_username = serializers.CharField(source='doctor.username', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient_id', 'patient_username', 'doctor_id', 'doctor_username',
            'appointment_datetime', 'reason', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']

    def validate(self, attrs):
        appt_dt = attrs.get('appointment_datetime') or getattr(self.instance, 'appointment_datetime', None)
        if appt_dt and appt_dt <= timezone.now():
            raise serializers.ValidationError({'appointment_datetime': 'يجب أن يكون الموعد في المستقبل.'})
        return attrs


class AppointmentCreateSerializer(serializers.ModelSerializer):
    doctor = serializers.IntegerField(write_only=True)

    class Meta:
        model = Appointment
        fields = ['doctor', 'appointment_datetime', 'reason']

    def validate_doctor(self, value):
        from users.models import User
        try:
            doctor = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('الطبيب غير موجود.')
        if not doctor.is_doctor:
            raise serializers.ValidationError('المعرّف المحدد ليس حساب طبيب.')
        return value

    def validate_appointment_datetime(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('يجب أن يكون الموعد في المستقبل.')
        return value

    def create(self, validated_data):
        request = self.context['request']
        try:
            patient = PatientProfile.objects.get(user=request.user)
        except PatientProfile.DoesNotExist:
            raise serializers.ValidationError('لا يوجد ملف مريض لهذا المستخدم.')
        doctor_id = validated_data.pop('doctor')
        from users.models import User
        doctor = User.objects.get(id=doctor_id)
        
        appt_dt = validated_data['appointment_datetime']
        appt_end = appt_dt + timedelta(hours=1)
        
        # التحقق من التعارض مع المواعيد الموجودة (مدة الموعد ساعة واحدة)
        # نحتاج للتحقق من المواعيد التي لا تكون ملغاة
        # موعدين يتداخلان إذا: start1 < end2 AND start2 < end1
        # حيث end = start + 1h
        conflicting_appointments = Appointment.objects.filter(
            doctor=doctor,
            status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]
        ).filter(
            # الموعد الموجود يبدأ قبل نهاية الموعد المطلوب
            Q(appointment_datetime__lt=appt_end) &
            # الموعد الموجود يبدأ بعد بداية الموعد المطلوب - ساعة (أي ينتهي بعد بداية المطلوب)
            Q(appointment_datetime__gt=appt_dt - timedelta(hours=1))
        )
        
        if conflicting_appointments.exists():
            # البحث عن أقرب وقت متاح (بعد نهاية آخر موعد متعارض)
            # نجد آخر موعد متعارض ونبدأ البحث من بعد نهايته
            latest_conflicting = conflicting_appointments.order_by('-appointment_datetime').first()
            latest_conflicting_end = latest_conflicting.appointment_datetime + timedelta(hours=1)
            
            # نبدأ البحث من بعد نهاية آخر موعد متعارض أو من وقت الحجز المطلوب، أيهما أكبر
            start_search_time = max(appt_dt, latest_conflicting_end)
            
            next_check_time = start_search_time
            max_attempts = 24  # نبحث لمدة 24 ساعة قادمة
            found_available = False
            nearest_available = None
            
            for _ in range(max_attempts):
                next_check_end = next_check_time + timedelta(hours=1)
                
                # التحقق إذا كان هذا الوقت متاحاً
                overlapping = Appointment.objects.filter(
                    doctor=doctor,
                    status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]
                ).filter(
                    # الموعد الموجود يبدأ قبل نهاية الوقت المتاح
                    Q(appointment_datetime__lt=next_check_end) &
                    # الموعد الموجود يبدأ بعد بداية الوقت المتاح - ساعة
                    Q(appointment_datetime__gt=next_check_time - timedelta(hours=1))
                )
                
                if not overlapping.exists():
                    found_available = True
                    nearest_available = next_check_time
                    break
                
                # الانتقال للساعة التالية
                next_check_time = next_check_time + timedelta(hours=1)
            
            error_message = {
                'appointment_datetime': ['هذا الوقت محجوز. الطبيب لديه موعد في هذا الوقت.']
            }
            if found_available:
                nearest_str = nearest_available.strftime('%Y-%m-%d %H:%M:%S')
                error_message['nearest_available'] = [f'أقرب وقت متاح: {nearest_str}']
            else:
                error_message['nearest_available'] = ['لا يوجد وقت متاح خلال الـ 24 ساعة القادمة.']
            
            raise serializers.ValidationError(error_message)
        
        return Appointment.objects.create(patient=patient, doctor=doctor, **validated_data)


class AppointmentStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['status']
        extra_kwargs = {
            'status': {'required': True}
        }

    def validate_status(self, value):
        if value not in [Appointment.STATUS_CONFIRMED, Appointment.STATUS_CANCELLED, Appointment.STATUS_COMPLETED]:
            raise serializers.ValidationError('حالة غير مسموحة. استخدم confirmed/cancelled/completed.')
        return value