"""
أمر إدارة Django لتعبئة بيانات تجريبية تحاكي الأرقام الظاهرة في تصاميم الواجهات
الأصلية (login/mainboard/sales/customer/inventory)، بحيث تعمل المنصة فور التشغيل
بعرض واقعي بدلاً من قاعدة بيانات فارغة.

الاستخدام:
    python manage.py seed_demo
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Account, Product, Purchase, Sale, SaleItem, StockItem, StockMovement

User = get_user_model()


class Command(BaseCommand):
    help = 'يعبئ قاعدة البيانات ببيانات تجريبية أولية لمنصة إمداد (مستخدمون، أصناف، مخزون، عملاء، فواتير).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush-users', action='store_true',
            help='إعادة تعيين كلمات مرور المستخدمين التجريبيين إذا كانوا موجودين مسبقاً.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('جاري إنشاء المستخدمين التجريبيين...')
        demo_users = [
            ('admin', 'Admin@2026', User.Role.ADMIN, 'مدير النظام', True, True),
            ('warehouse1', 'Warehouse@2026', User.Role.WAREHOUSE, 'أمين المخزن', False, False),
            ('sales1', 'Sales@2026', User.Role.SALES, 'موظف المبيعات', False, False),
            ('accountant1', 'Account@2026', User.Role.ACCOUNTANT, 'المحاسب', False, False),
        ]
        created_users = {}
        for username, password, role, full_name, is_staff, is_superuser in demo_users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'role': role, 'first_name': full_name,
                    'is_staff': is_staff, 'is_superuser': is_superuser,
                },
            )
            if created or options['flush_users']:
                user.set_password(password)
                user.role = role
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save()
            created_users[username] = user
        self.stdout.write(self.style.SUCCESS(
            'تم إنشاء المستخدمين. بيانات الدخول: admin/Admin@2026، warehouse1/Warehouse@2026، '
            'sales1/Sales@2026، accountant1/Account@2026'
        ))

        self.stdout.write('جاري إنشاء الأصناف (المنتجات)...')
        home, _ = Product.objects.get_or_create(
            code='GAS-12KG', defaults={
                'name': 'أسطوانة منزلية (12.5 كجم)', 'size_kg': Decimal('12.5'),
                'category': Product.Category.HOME, 'unit_price': Decimal('2500'),
                'min_stock_level': 500,
            },
        )
        commercial, _ = Product.objects.get_or_create(
            code='GAS-25KG', defaults={
                'name': 'أسطوانة تجارية للمطاعم (25 كجم)', 'size_kg': Decimal('25'),
                'category': Product.Category.COMMERCIAL, 'unit_price': Decimal('5000'),
                'min_stock_level': 300,
            },
        )

        self.stdout.write('جاري إنشاء سجلات المخزون...')
        StockItem.objects.get_or_create(
            product=home, condition=StockItem.Condition.FULL,
            location='المستودع الرئيسي (أ)', defaults={'quantity': 2150},
        )
        StockItem.objects.get_or_create(
            product=commercial, condition=StockItem.Condition.FULL,
            location='المستودع الرئيسي (أ)', defaults={'quantity': 1300},
        )
        StockItem.objects.get_or_create(
            product=home, condition=StockItem.Condition.EMPTY,
            location='ساحة التعبئة الخارجية', defaults={'quantity': 1120},
        )
        StockItem.objects.get_or_create(
            product=home, condition=StockItem.Condition.MAINTENANCE,
            location='ورشة الصيانة الهندسية', defaults={'quantity': 45},
        )

        self.stdout.write('جاري إنشاء حسابات العملاء والموردين...')
        refinery, _ = Account.objects.get_or_create(
            name='مصفاة الجيلي للبترول', defaults={
                'account_type': Account.AccountType.SUPPLIER, 'phone': '0123456789',
                'region': 'الجيلي', 'balance': Decimal('-3400000'),
            },
        )
        bahri_agent, _ = Account.objects.get_or_create(
            name='موزع بحري المعتمد (أحمد علي)', defaults={
                'account_type': Account.AccountType.AGENT, 'phone': '0912345678',
                'region': 'الخرطوم بحري', 'balance': Decimal('450000'),
            },
        )
        omdurman_agent, _ = Account.objects.get_or_create(
            name='وكيل أمدرمان الرئيسي', defaults={
                'account_type': Account.AccountType.AGENT, 'phone': '0922223344',
                'region': 'أمدرمان', 'balance': Decimal('800000'),
            },
        )
        nile_company, _ = Account.objects.get_or_create(
            name='شركة النيل للخدمات الغذائية', defaults={
                'account_type': Account.AccountType.CUSTOMER, 'phone': '0111222333',
                'region': 'الخرطوم (العمارات)', 'balance': Decimal('0'), 'is_active': False,
            },
        )

        self.stdout.write('جاري إنشاء فواتير مبيعات تجريبية (آخر 6 أيام)...')
        sales_pattern = [320, 450, 410, 580, 690, 820]
        today = timezone.localdate()
        start_day = today - datetime.timedelta(days=5)
        sales_user = created_users['sales1']
        for i, qty in enumerate(sales_pattern):
            day = start_day + datetime.timedelta(days=i)
            sale_dt = timezone.make_aware(datetime.datetime.combine(day, datetime.time(12, 0)))
            sale = Sale.objects.create(
                account=omdurman_agent if i % 2 == 0 else bahri_agent,
                payment_method=Sale.PaymentMethod.CREDIT if i % 3 == 0 else Sale.PaymentMethod.CASH,
                created_by=sales_user,
                created_at=sale_dt,
            )
            SaleItem.objects.create(sale=sale, product=home, quantity=qty, unit_price=home.unit_price)
            StockMovement.objects.create(
                product=home, movement_type=StockMovement.MovementType.OUT, quantity=-qty,
                related_account=sale.account, note=f'توزيع لـ ({sale.account.name})',
                created_by=sales_user, created_at=sale_dt,
            )

        self.stdout.write('جاري إنشاء حركات مخزون إضافية...')
        StockMovement.objects.get_or_create(
            product=home, movement_type=StockMovement.MovementType.IN, quantity=450,
            note='شحنة واردة من المصفاة', defaults={'created_by': created_users['warehouse1']},
        )
        Purchase.objects.get_or_create(
            product=home, supplier=refinery, quantity=450, unit_cost=Decimal('1800'),
            condition=StockItem.Condition.FULL, defaults={'received_by': created_users['warehouse1']},
        )

        self.stdout.write(self.style.SUCCESS('تم تعبئة البيانات التجريبية بنجاح.'))
