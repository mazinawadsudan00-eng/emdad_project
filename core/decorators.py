"""
ديكوريتور بسيط لتقييد الوصول لبعض الصفحات/الإجراءات حسب صلاحية المستخدم (role)،
بحسب "تحليل احتياجات المستخدمين" في الفصل الثالث (3-6) من وثيقة البحث.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    """
    يسمح بالوصول فقط للمستخدمين الذين تكون صلاحيتهم (user.role) ضمن roles،
    أو لمستخدم مدير النظام (superuser/staff) دائماً.
    الاستخدام:
        @role_required('admin', 'warehouse')
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.is_staff or user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'ليست لديك صلاحية الوصول لهذه العملية.')
            return redirect('dashboard')
        return _wrapped
    return decorator
