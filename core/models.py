"""
نماذج قاعدة البيانات لمنصة إمداد الرقمية
مبنية على تحليل الفصل الثالث (مخطط الفئات - Class Diagram) الوارد في وثيقة
البحث: فئة المستخدم، فئة خزان/صنف الغاز، فئة الأسطوانة (المخزون)، فئة الحركة،
بالإضافة إلى الجداول اللازمة لإدارة العملاء/الموردين والمبيعات والمشتريات
والفواتير المذكورة في تحليل قاعدة البيانات (3-18).
"""
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """فئة المستخدم - تمثل جميع مستخدمي النظام بمختلف صلاحياتهم."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'مدير النظام'
        WAREHOUSE = 'warehouse', 'أمين المخزن'
        SALES = 'sales', 'موظف المبيعات'
        ACCOUNTANT = 'accountant', 'محاسب'

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.SALES,
        verbose_name='الصلاحية',
    )
    phone = models.CharField(max_length=30, blank=True, verbose_name='رقم الهاتف')

    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'

    def __str__(self):
        return self.get_full_name() or self.username


class Account(models.Model):
    """
    دليل الحسابات: يمثل العملاء (وكلاء التوزيع / العملاء التجاريون)
    والموردين على حدٍ سواء، بحسب تصميم صفحة "العملاء والموردين".
    balance موجب = مبلغ مستحق لنا (دَين على الحساب).
    balance سالب = مبلغ مستحق علينا (نحن مدينون لهذا المورد).
    """

    class AccountType(models.TextChoices):
        SUPPLIER = 'supplier', 'مورد رئيسي'
        AGENT = 'agent', 'وكيل توزيع'
        CUSTOMER = 'customer', 'عميل تجاري'

    name = models.CharField(max_length=200, verbose_name='الاسم / الشركة')
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices,
        default=AccountType.CUSTOMER, verbose_name='التصنيف',
    )
    phone = models.CharField(max_length=30, blank=True, verbose_name='رقم الهاتف')
    region = models.CharField(max_length=150, blank=True, verbose_name='المنطقة / الموقع')
    balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0'),
        verbose_name='الرصيد المالي الحالي',
        help_text='موجب = مستحق لنا من الحساب، سالب = مستحق علينا لهذا المورد',
    )
    is_active = models.BooleanField(default=True, verbose_name='عقد نشط')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'حساب (عميل/مورد)'
        verbose_name_plural = 'دليل الحسابات (العملاء والموردون)'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_supplier(self):
        return self.account_type == self.AccountType.SUPPLIER

    @property
    def balance_abs(self):
        return abs(self.balance)


class Product(models.Model):
    """فئة الصنف (خزان/أسطوانة الغاز) - يمثل أنواع وأحجام أسطوانات الغاز المتداولة."""

    class Category(models.TextChoices):
        HOME = 'home', 'منزلية'
        COMMERCIAL = 'commercial', 'تجارية'
        CENTRAL = 'central', 'خزان مركزي'

    code = models.CharField(max_length=30, unique=True, verbose_name='رمز الصنف')
    name = models.CharField(max_length=150, verbose_name='اسم الصنف')
    size_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0'), verbose_name='الحجم (كجم)')
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.HOME, verbose_name='الفئة',
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name='سعر الوحدة')
    min_stock_level = models.PositiveIntegerField(default=0, verbose_name='الحد الأدنى للمخزون')
    is_sellable = models.BooleanField(default=True, verbose_name='قابل للبيع')
    is_active = models.BooleanField(default=True, verbose_name='صنف نشط')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'صنف / نوع أسطوانة'
        verbose_name_plural = 'المنتجات (أصناف الأسطوانات)'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'

    @property
    def total_quantity(self):
        return self.stock_items.aggregate(t=models.Sum('quantity'))['t'] or 0

    @property
    def total_available(self):
        """الكمية المتاحة للبيع فعلياً (الحالة: جاهز للبيع)."""
        return self.stock_items.filter(condition=StockItem.Condition.FULL).aggregate(
            t=models.Sum('quantity'))['t'] or 0


class StockItem(models.Model):
    """
    فئة الأسطوانة/المخزون: تمثل كمية صنف معين في حالة تشغيلية ومكان تخزين محددين
    (جاهز للبيع / فارغ بانتظار التعبئة / قيد الصيانة).
    """

    class Condition(models.TextChoices):
        FULL = 'full', 'جاهز للبيع (ممتلئ)'
        EMPTY = 'empty', 'فارغ (تحت التعبئة)'
        MAINTENANCE = 'maintenance', 'قيد الصيانة'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_items', verbose_name='الصنف')
    condition = models.CharField(
        max_length=20, choices=Condition.choices, default=Condition.FULL, verbose_name='الحالة التشغيلية',
    )
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='الكمية المتوفرة')
    location = models.CharField(max_length=150, default='المستودع الرئيسي (أ)', verbose_name='موقع التخزين')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'سجل مخزون'
        verbose_name_plural = 'جرد المخزون'
        unique_together = ('product', 'condition', 'location')
        ordering = ['product__code', 'condition']

    def __str__(self):
        return f'{self.product.code} / {self.get_condition_display()} ({self.quantity})'

    @property
    def status_label(self):
        """يُرجع (نص الحالة، لون Bootstrap) بحسب الكمية والحد الأدنى."""
        if self.condition == self.Condition.MAINTENANCE:
            return 'حرِج / يحتاج فحص', 'danger'
        if self.quantity <= 0:
            return 'نفاد المخزون', 'danger'
        if self.quantity <= self.product.min_stock_level:
            return 'دوران سريع / قريب من الحد الأدنى', 'warning'
        return 'مخزون آمن', 'success'


class Purchase(models.Model):
    """تسجيل شحنات الغاز الواردة من الموردين (عملية شراء/استلام)."""

    supplier = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchases', verbose_name='المورد',
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchases', verbose_name='الصنف')
    quantity = models.PositiveIntegerField(verbose_name='الكمية الواردة')
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name='تكلفة الوحدة')
    condition = models.CharField(
        max_length=20, choices=StockItem.Condition.choices, default=StockItem.Condition.FULL,
        verbose_name='حالة الوارد',
    )
    location = models.CharField(max_length=150, default='المستودع الرئيسي (أ)', verbose_name='موقع التخزين')
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='استلمها',
    )
    received_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الاستلام')

    class Meta:
        verbose_name = 'شحنة واردة'
        verbose_name_plural = 'المشتريات / الشحنات الواردة'
        ordering = ['-received_at']

    def __str__(self):
        return f'شحنة {self.product.code} × {self.quantity}'

    @property
    def total_cost(self):
        return self.unit_cost * self.quantity


class Sale(models.Model):
    """فاتورة بيع لعميل/وكيل، تحتوي على بند واحد أو أكثر (SaleItem)."""

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'نقدي / كاش'
        BANK = 'bank', 'تطبيق بنكي'
        CREDIT = 'credit', 'آجل / ديون مستحقة'

    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales', verbose_name='الوكيل / العميل',
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH, verbose_name='طريقة الدفع',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='أصدرها',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الفاتورة')

    class Meta:
        verbose_name = 'فاتورة بيع'
        verbose_name_plural = 'المبيعات والفواتير'
        ordering = ['-created_at']

    def __str__(self):
        return self.invoice_no

    @property
    def invoice_no(self):
        return f'INV-{1000 + self.pk}' if self.pk else 'INV-جديدة'

    @property
    def total(self):
        return sum((item.subtotal for item in self.items.all()), Decimal('0'))

    @property
    def is_paid(self):
        return self.payment_method != self.PaymentMethod.CREDIT

    @property
    def status_label(self):
        return ('مدفوع', 'success') if self.is_paid else ('آجل (دين)', 'warning')


class SaleItem(models.Model):
    """بند داخل فاتورة بيع: صنف + كمية + سعر وقت البيع (لضمان دقة السجل التاريخي)."""

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items', verbose_name='الفاتورة')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items', verbose_name='الصنف')
    quantity = models.PositiveIntegerField(default=1, verbose_name='الكمية')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='سعر الوحدة وقت البيع')

    class Meta:
        verbose_name = 'بند فاتورة'
        verbose_name_plural = 'بنود الفواتير'

    def __str__(self):
        return f'{self.product.code} × {self.quantity}'

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class StockMovement(models.Model):
    """
    فئة الحركة: سجل كامل لكل عملية تمس المخزون (وارد/صادر/صيانة/تسوية) -
    يُستخدم لعرض "آخر التحركات بالمجمع" في لوحة التحكم ولتوثيق تاريخ كل عملية.
    """

    class MovementType(models.TextChoices):
        IN = 'in', 'شحنة واردة'
        OUT = 'out', 'صرف / توزيع'
        MAINTENANCE = 'maintenance', 'فرز للصيانة'
        ADJUST = 'adjust', 'تسوية جرد'

    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, related_name='movements', verbose_name='الصنف',
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, verbose_name='نوع الحركة')
    quantity = models.IntegerField(verbose_name='الكمية (موجب للوارد، سالب للصادر)')
    related_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الحساب المرتبط',
    )
    note = models.CharField(max_length=255, blank=True, verbose_name='البيان')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='نفذها',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='التوقيت')

    class Meta:
        verbose_name = 'حركة مخزون'
        verbose_name_plural = 'سجل التحركات'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_movement_type_display()} ({self.quantity})'

    @property
    def badge_class(self):
        return {
            self.MovementType.IN: 'success',
            self.MovementType.OUT: 'danger',
            self.MovementType.MAINTENANCE: 'warning',
            self.MovementType.ADJUST: 'secondary',
        }.get(self.movement_type, 'secondary')
