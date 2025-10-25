from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # حقل إضافي لتحديد ما إذا المستخدم طبيب
    is_doctor = models.BooleanField(default=False)

    def __str__(self):
        return self.username
