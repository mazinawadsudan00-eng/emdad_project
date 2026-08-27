from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Account, Product, Purchase, Sale, StockItem


class StyledAuthenticationForm(AuthenticationForm):
    """نموذج تسجيل الدخول، بنفس تنسيق حقول Bootstrap المستخدمة في login.html الأصلي."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control border-start-0',
            'placeholder': 'أدخل اسم المستخدم',
            'autofocus': True,
        })
        self.fields['username'].label = 'اسم المستخدم / البريد الإلكتروني'
        self.fields['password'].widget.attrs.update({
            'class': 'form-control border-start-0',
            'placeholder': 'أدخل كلمة المرور',
        })
        self.fields['password'].label = 'كلمة المرور'

    error_messages = {
        'invalid_login': 'اسم المستخدم أو كلمة المرور غير صحيحة. يرجى المحاولة مرة أخرى.',
        'inactive': 'هذا الحساب غير مُفعّل، يرجى مراجعة مدير النظام.',
    }


class AccountForm(forms.ModelForm):
    """نموذج إضافة/تعديل جهة اتصال (عميل أو مورد) - يطابق نافذة addContactModal."""

    class Meta:
        model = Account
        fields = ['name', 'account_type', 'phone', 'region', 'balance', 'is_active']
        labels = {
            'name': 'الاسم الكامل / اسم المنشأة أو الشركة',
            'account_type': 'نوع الحساب (التصنيف)',
            'phone': 'رقم الهاتف',
            'region': 'المنطقة / الموقع',
            'balance': 'الرصيد الافتتاحي (إن وُجد)',
            'is_active': 'عقد نشط',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: شركة غاز النيلين'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09xxxxxxx'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: بحري - المظلات'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PurchaseForm(forms.ModelForm):
    """نموذج تسجيل شحنة/مخزون جديد - يطابق نافذة addStockModal في صفحة المخزون."""

    class Meta:
        model = Purchase
        fields = ['product', 'supplier', 'quantity', 'unit_cost', 'condition', 'location']
        labels = {
            'product': 'الصنف',
            'supplier': 'المورد (اختياري)',
            'quantity': 'الكمية الواردة',
            'unit_cost': 'تكلفة الوحدة',
            'condition': 'حالة الوارد',
            'location': 'موقع التخزين',
        }
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Account.objects.filter(account_type=Account.AccountType.SUPPLIER)
        self.fields['supplier'].required = False
        self.fields['product'].queryset = Product.objects.filter(is_active=True)


class StockItemForm(forms.ModelForm):
    """نموذج تعديل سجل مخزون قائم (زر التعديل بالقلم في صفحة المخزون)."""

    class Meta:
        model = StockItem
        fields = ['quantity', 'location', 'condition']
        labels = {
            'quantity': 'الكمية المتوفرة',
            'location': 'موقع التخزين',
            'condition': 'الحالة التشغيلية',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
        }


class SaleForm(forms.Form):
    """نموذج فاتورة بيع جديدة - يطابق نموذج "فاتورة بيع جديدة" في sales.html الأصلي."""

    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True), required=False, label='الوكيل / العميل',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True, is_sellable=True), label='الصنف المراد بيعه',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'itemSelect'}),
    )
    quantity = forms.IntegerField(
        min_value=1, initial=1, label='الكمية (عدد الأسطوانات)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'itemQuantity'}),
    )
    payment_method = forms.ChoiceField(
        choices=Sale.PaymentMethod.choices, label='طريقة الدفع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class SettleForm(forms.Form):
    """نموذج تسوية مالية سريعة (دفع مستحقات / تحصيل دَين) لحساب عميل أو مورد."""

    amount = forms.DecimalField(
        min_value=0, max_digits=14, decimal_places=2, label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
    )
