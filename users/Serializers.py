from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User, DoctorProfile

class UserSerializer(serializers.ModelSerializer):
    doctor_profile = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_doctor', 'doctor_profile']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        user = super().create(validated_data)
        # إنشاء ملف طبيب تلقائياً إذا كان طبيباً
        if user.is_doctor and not hasattr(user, 'doctor_profile'):
            DoctorProfile.objects.create(user=user)
        return user

    def get_doctor_profile(self, obj):
        if obj.is_doctor and hasattr(obj, 'doctor_profile') and obj.doctor_profile:
            return DoctorProfileSerializer(obj.doctor_profile).data
        return None


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = [
            'specialty', 'years_of_experience', 'clinic_address', 'clinic_city',
            'clinic_phone', 'bio', 'certifications', 'certificate_image'
        ]


class DoctorProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = [
            'specialty', 'years_of_experience', 'clinic_address', 'clinic_city',
            'clinic_phone', 'bio', 'certifications', 'certificate_image'
        ]
