from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Account, Product, Purchase, Sale, StockItem, Warehouse


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
        fields = ['product', 'supplier', 'quantity', 'unit_cost', 'condition', 'warehouse']
        labels = {
            'product': 'الصنف',
            'supplier': 'المورد (اختياري)',
            'quantity': 'الكمية الواردة',
            'unit_cost': 'تكلفة الوحدة',
            'condition': 'حالة الوارد',
            'warehouse': 'موقع التخزين / المستودع',
        }
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Account.objects.filter(account_type=Account.AccountType.SUPPLIER)
        self.fields['supplier'].required = False
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        if 'warehouse' in self.fields:
            self.fields['warehouse'].queryset = Warehouse.objects.filter(is_active=True)


class StockItemForm(forms.ModelForm):
    """نموذج تعديل سجل مخزون قائم (زر التعديل بالقلم في صفحة المخزون)."""

    class Meta:
        model = StockItem
        fields = ['quantity', 'warehouse', 'condition']
        labels = {
            'quantity': 'الكمية المتوفرة',
            'warehouse': 'موقع التخزين / المستودع',
            'condition': 'الحالة التشغيلية',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'warehouse' in self.fields:
            self.fields['warehouse'].queryset = Warehouse.objects.filter(is_active=True)


class SaleForm(forms.Form):
    """نموذج فاتورة بيع جديدة مع البحث عن العميل وإمكانية إنشاء عميل جديد."""

    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label='العميل',
        widget=forms.Select(
            attrs={
                'class': 'form-select',
                'id': 'accountSelect',
            }
        ),
    )

    new_customer_name = forms.CharField(
        required=False,
        max_length=200,
        label='اسم العميل الجديد',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'newCustomerName',
                'placeholder': 'اكتب اسم العميل الجديد',
            }
        ),
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(
            is_active=True,
            is_sellable=True
        ),
        label='الصنف المراد بيعه',
        widget=forms.Select(
            attrs={
                'class': 'form-select',
                'id': 'itemSelect',
            }
        ),
    )

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label='الكمية (عدد الأسطوانات)',
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'id': 'itemQuantity',
                'min': '1',
            }
        ),
    )

    payment_method = forms.ChoiceField(
        choices=Sale.PaymentMethod.choices,
        label='طريقة الدفع',
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        account = cleaned_data.get('account')
        new_customer_name = (
            cleaned_data.get('new_customer_name') or ''
        ).strip()

        payment_method = cleaned_data.get('payment_method')

        # إذا كتب المستخدم اسم عميل جديد فلا يسمح باختيار عميل موجود معه
        if account and new_customer_name:
            raise forms.ValidationError(
                'اختر عميلاً موجوداً أو أضف عميلاً جديداً، وليس الاثنين معاً.'
            )

        # البيع الآجل يحتاج حساباً مسجلاً
        if (
            payment_method == Sale.PaymentMethod.CREDIT
            and not account
            and not new_customer_name
        ):
            raise forms.ValidationError(
                'البيع الآجل يتطلب اختيار عميل أو إنشاء عميل جديد.'
            )

        return cleaned_data


class SettleForm(forms.Form):
    """نموذج تسوية مالية سريعة (دفع مستحقات / تحصيل دَين) لحساب عميل أو مورد."""

    amount = forms.DecimalField(
        min_value=0, max_digits=14, decimal_places=2, label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
    )