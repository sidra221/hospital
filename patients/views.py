from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from .models import PatientProfile, MedicalRecord, Appointment
from .serializers import (
    PatientProfileSerializer,
    PatientProfileUpdateSerializer,
    MedicalRecordSerializer,
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentStatusUpdateSerializer,
)

class IsDoctorPermission(permissions.BasePermission):
    """يسمح فقط للأطباء برؤية قائمة المرضى"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_doctor)

# عرض جميع المرضى (للطبيب فقط)
class PatientListView(generics.ListAPIView):
    queryset = PatientProfile.objects.select_related('user').all()
    serializer_class = PatientProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctorPermission]

# عرض مريض محدد (المريض يشوف نفسه والطبيب يشوف الكل)
class PatientDetailView(generics.RetrieveAPIView):
    queryset = PatientProfile.objects.select_related('user').all()
    serializer_class = PatientProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user and not self.request.user.is_doctor:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("ليس لديك صلاحية لعرض بيانات هذا المريض.")
        return obj

# تحديث بيانات المريض (المريض يحدث بياناته فقط)
class PatientUpdateView(generics.UpdateAPIView):
    serializer_class = PatientProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """يحصل على ملف المريض للمستخدم الحالي"""
        try:
            return PatientProfile.objects.get(user=self.request.user)
        except PatientProfile.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("لم يتم العثور على ملف المريض.")

    def update(self, request, *args, **kwargs):
        """تحديث بيانات المريض"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # إرجاع البيانات المحدثة مع معلومات المستخدم
        response_data = PatientProfileSerializer(instance).data
        return Response(response_data, status=status.HTTP_200_OK)


class MedicalRecordUpdateView(generics.UpdateAPIView):
    """تحديث المعلومات المرضية - للطبيب فقط"""
    serializer_class = MedicalRecordSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctorPermission]

    def get_object(self):
        """يجلب السجل المرضي لمريض محدد عبر pk لملف المريض"""
        patient_pk = self.kwargs.get('pk')
        patient = generics.get_object_or_404(PatientProfile, pk=patient_pk)
        # أنشئ سجل طبي إذا لم يكن موجوداً
        medical_record, _ = MedicalRecord.objects.get_or_create(patient=patient)
        return medical_record

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PatientAppointmentListCreateView(generics.ListCreateAPIView):
    """المريض: عرض مواعيده وحجز موعد جديد مع طبيب"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            patient = PatientProfile.objects.get(user=self.request.user)
        except PatientProfile.DoesNotExist:
            return Appointment.objects.none()
        return Appointment.objects.select_related('patient__user', 'doctor').filter(patient=patient)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def perform_create(self, serializer):
        serializer.save()


class DoctorAppointmentListView(generics.ListAPIView):
    """الطبيب: عرض مواعيده"""
    permission_classes = [permissions.IsAuthenticated, IsDoctorPermission]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.select_related('patient__user', 'doctor').filter(doctor=self.request.user)


class DoctorAppointmentStatusUpdateView(generics.UpdateAPIView):
    """الطبيب: تأكيد/إلغاء/إنهاء موعده"""
    permission_classes = [permissions.IsAuthenticated, IsDoctorPermission]
    serializer_class = AppointmentStatusUpdateSerializer
    queryset = Appointment.objects.all()

    def get_object(self):
        obj = super().get_object()
        if obj.doctor != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('لا يمكنك تعديل موعد ليس لك.')
        return obj


class PatientAppointmentCancelView(generics.UpdateAPIView):
    """المريض: إلغاء موعده فقط"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentStatusUpdateSerializer
    queryset = Appointment.objects.all()

    def get_object(self):
        obj = super().get_object()
        try:
            patient = PatientProfile.objects.get(user=self.request.user)
        except PatientProfile.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('لا تملك ملف مريض.')
        if obj.patient != patient:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('لا يمكنك إلغاء موعد ليس لك.')
        return obj

    def update(self, request, *args, **kwargs):
        # Force status to cancelled regardless of input
        request.data._mutable = True if hasattr(request.data, '_mutable') else False
        data = {**request.data, 'status': Appointment.STATUS_CANCELLED}
        serializer = self.get_serializer(self.get_object(), data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DashboardStatsView(APIView):
    """الداشبورد: إحصائيات المرضى مع إمكانية الفلترة حسب المرض أو الدواء"""
    permission_classes = [permissions.IsAuthenticated, IsDoctorPermission]

    def get(self, request):
        # الحصول على معاملات الفلترة من query parameters
        disease_filter = request.query_params.get('disease', None)
        medication_filter = request.query_params.get('medication', None)

        # استعلام أساسي للحصول على المرضى الذين لديهم سجلات طبية
        queryset = PatientProfile.objects.select_related('user').prefetch_related('medical_record').all()

        # فلترة حسب المرض (في chronic_diseases أو past_diseases)
        if disease_filter:
            queryset = queryset.filter(
                Q(medical_record__chronic_diseases__icontains=disease_filter) |
                Q(medical_record__past_diseases__icontains=disease_filter)
            )

        # فلترة حسب الدواء (في medications)
        if medication_filter:
            queryset = queryset.filter(
                medical_record__medications__icontains=medication_filter
            )

        # الحصول على عدد المرضى بعد الفلترة
        total_patients = queryset.count()

        # إحصائيات عامة (من جميع المرضى، بدون فلترة)
        all_patients_with_records = PatientProfile.objects.select_related('medical_record').filter(
            medical_record__isnull=False
        )

        # إحصائيات الأمراض الشائعة
        common_diseases = {}
        for patient in all_patients_with_records:
            if hasattr(patient, 'medical_record') and patient.medical_record:
                # تقسيم الأمراض المزمنة
                if patient.medical_record.chronic_diseases:
                    diseases = [d.strip() for d in patient.medical_record.chronic_diseases.split(',') if d.strip()]
                    for disease in diseases:
                        disease_lower = disease.lower()
                        if disease_lower not in common_diseases:
                            common_diseases[disease_lower] = 0
                        common_diseases[disease_lower] += 1

                # تقسيم الأمراض السابقة
                if patient.medical_record.past_diseases:
                    diseases = [d.strip() for d in patient.medical_record.past_diseases.split(',') if d.strip()]
                    for disease in diseases:
                        disease_lower = disease.lower()
                        if disease_lower not in common_diseases:
                            common_diseases[disease_lower] = 0
                        common_diseases[disease_lower] += 1

        # إحصائيات الأدوية الشائعة
        common_medications = {}
        for patient in all_patients_with_records:
            if hasattr(patient, 'medical_record') and patient.medical_record:
                if patient.medical_record.medications:
                    medications = [m.strip() for m in patient.medical_record.medications.split(',') if m.strip()]
                    for medication in medications:
                        med_lower = medication.lower()
                        if med_lower not in common_medications:
                            common_medications[med_lower] = 0
                        common_medications[med_lower] += 1

        # ترتيب الأمراض والأدوية حسب التكرار
        top_diseases = sorted(
            [{'name': name, 'count': count} for name, count in common_diseases.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]

        top_medications = sorted(
            [{'name': name, 'count': count} for name, count in common_medications.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]

        # إحصائيات المواعيد
        appointments_stats = {
            'total': Appointment.objects.count(),
            'pending': Appointment.objects.filter(status=Appointment.STATUS_PENDING).count(),
            'confirmed': Appointment.objects.filter(status=Appointment.STATUS_CONFIRMED).count(),
            'completed': Appointment.objects.filter(status=Appointment.STATUS_COMPLETED).count(),
            'cancelled': Appointment.objects.filter(status=Appointment.STATUS_CANCELLED).count(),
        }

        # إحصائيات عامة
        User = get_user_model()
        general_stats = {
            'total_patients': PatientProfile.objects.count(),
            'total_doctors': User.objects.filter(is_doctor=True).count(),
        }

        # قائمة المرضى بعد الفلترة (معلومات مختصرة)
        filtered_patients = []
        for patient in queryset[:50]:  # حد أقصى 50 مريض
            patient_data = {
                'id': patient.id,
                'username': patient.user.username,
                'email': patient.user.email,
                'national_id': patient.national_id,
            }
            if hasattr(patient, 'medical_record') and patient.medical_record:
                patient_data['chronic_diseases'] = patient.medical_record.chronic_diseases
                patient_data['past_diseases'] = patient.medical_record.past_diseases
                patient_data['medications'] = patient.medical_record.medications
            filtered_patients.append(patient_data)

        response_data = {
            'filters_applied': {
                'disease': disease_filter,
                'medication': medication_filter,
            },
            'filtered_results': {
                'total_patients_count': total_patients,
                'patients': filtered_patients,
            },
            'statistics': {
                'general': general_stats,
                'appointments': appointments_stats,
                'common_diseases': top_diseases,
                'common_medications': top_medications,
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)
