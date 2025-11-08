from rest_framework import generics, permissions
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from .models import User
from .Serializers import UserSerializer, DoctorProfileUpdateSerializer, DoctorProfileSerializer


# تسجيل مستخدم جديد
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(id=response.data['id'])
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'is_doctor': user.is_doctor
        })


# تسجيل الدخول
class LoginView(ObtainAuthToken):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'is_doctor': user.is_doctor
        })


# تحديث ملف الطبيب (الطبيب يعدل ملفه فقط)
class DoctorProfileUpdateView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DoctorProfileUpdateSerializer

    def get_object(self):
        user = self.request.user
        if not user.is_doctor:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("هذا المسار مخصص للأطباء فقط.")
        profile = getattr(user, 'doctor_profile', None)
        if profile is None:
            from .models import DoctorProfile
            profile = DoctorProfile.objects.create(user=user)
        return profile


class DoctorListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DoctorProfileSerializer

    def get_queryset(self):
        from .models import DoctorProfile
        return DoctorProfile.objects.select_related('user').all()


class DoctorDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DoctorProfileSerializer
    lookup_field = 'user_id'

    def get_queryset(self):
        from .models import DoctorProfile
        return DoctorProfile.objects.select_related('user').all()
