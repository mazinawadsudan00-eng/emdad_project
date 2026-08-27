from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path, include

from core.views import EmdadLoginView , custom_logout

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', EmdadLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('', include('core.urls')),
]
