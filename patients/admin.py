from django.contrib import admin
from .models import PatientProfile

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'national_id', 'phone_number', 'date_of_birth')
    search_fields = ('user__username', 'national_id', 'phone_number')
