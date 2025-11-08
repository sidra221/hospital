from django.urls import path
from .views import (
    PatientListView,
    PatientDetailView,
    PatientUpdateView,
    MedicalRecordUpdateView,
    PatientAppointmentListCreateView,
    DoctorAppointmentListView,
    DoctorAppointmentStatusUpdateView,
    PatientAppointmentCancelView,
    DashboardStatsView,
)

urlpatterns = [
    path('', PatientListView.as_view(), name='patients-list'),
    path('<int:pk>/', PatientDetailView.as_view(), name='patient-detail'),
    path('update/', PatientUpdateView.as_view(), name='patient-update'),
    path('<int:pk>/medical/', MedicalRecordUpdateView.as_view(), name='patient-medical-update'),
    path('appointments/', PatientAppointmentListCreateView.as_view(), name='patient-appointments'),
    path('appointments/doctor/', DoctorAppointmentListView.as_view(), name='doctor-appointments'),
    path('appointments/<int:pk>/doctor-status/', DoctorAppointmentStatusUpdateView.as_view(), name='doctor-appointment-status'),
    path('appointments/<int:pk>/cancel/', PatientAppointmentCancelView.as_view(), name='patient-appointment-cancel'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
]
