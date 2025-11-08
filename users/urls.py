from django.urls import path
from .views import RegisterView, LoginView, DoctorProfileUpdateView, DoctorListView, DoctorDetailView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('doctors/', DoctorListView.as_view(), name='doctors-list'),
    path('doctors/<int:user_id>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('doctor/profile/', DoctorProfileUpdateView.as_view(), name='doctor-profile-update'),
]
