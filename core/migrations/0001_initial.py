import decimal

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('role', models.CharField(choices=[('admin', 'مدير النظام'), ('warehouse', 'أمين المخزن'), ('sales', 'موظف المبيعات'), ('accountant', 'محاسب')], default='sales', max_length=20, verbose_name='الصلاحية')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='رقم الهاتف')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'مستخدم',
                'verbose_name_plural': 'المستخدمون',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='الاسم / الشركة')),
                ('account_type', models.CharField(choices=[('supplier', 'مورد رئيسي'), ('agent', 'وكيل توزيع'), ('customer', 'عميل تجاري')], default='customer', max_length=20, verbose_name='التصنيف')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='رقم الهاتف')),
                ('region', models.CharField(blank=True, max_length=150, verbose_name='المنطقة / الموقع')),
                ('balance', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), help_text='موجب = مستحق لنا من الحساب، سالب = مستحق علينا لهذا المورد', max_digits=14, verbose_name='الرصيد المالي الحالي')),
                ('is_active', models.BooleanField(default=True, verbose_name='عقد نشط')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'حساب (عميل/مورد)',
                'verbose_name_plural': 'دليل الحسابات (العملاء والموردون)',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=30, unique=True, verbose_name='رمز الصنف')),
                ('name', models.CharField(max_length=150, verbose_name='اسم الصنف')),
                ('size_kg', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=6, verbose_name='الحجم (كجم)')),
                ('category', models.CharField(choices=[('home', 'منزلية'), ('commercial', 'تجارية'), ('central', 'خزان مركزي')], default='home', max_length=20, verbose_name='الفئة')),
                ('unit_price', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=12, verbose_name='سعر الوحدة')),
                ('min_stock_level', models.PositiveIntegerField(default=0, verbose_name='الحد الأدنى للمخزون')),
                ('is_sellable', models.BooleanField(default=True, verbose_name='قابل للبيع')),
                ('is_active', models.BooleanField(default=True, verbose_name='صنف نشط')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'صنف / نوع أسطوانة',
                'verbose_name_plural': 'المنتجات (أصناف الأسطوانات)',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='StockItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('condition', models.CharField(choices=[('full', 'جاهز للبيع (ممتلئ)'), ('empty', 'فارغ (تحت التعبئة)'), ('maintenance', 'قيد الصيانة')], default='full', max_length=20, verbose_name='الحالة التشغيلية')),
                ('quantity', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='الكمية المتوفرة')),
                ('location', models.CharField(default='المستودع الرئيسي (أ)', max_length=150, verbose_name='موقع التخزين')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_items', to='core.product', verbose_name='الصنف')),
            ],
            options={
                'verbose_name': 'سجل مخزون',
                'verbose_name_plural': 'جرد المخزون',
                'ordering': ['product__code', 'condition'],
                'unique_together': {('product', 'condition', 'location')},
            },
        ),
        migrations.CreateModel(
            name='Purchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(verbose_name='الكمية الواردة')),
                ('unit_cost', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=12, verbose_name='تكلفة الوحدة')),
                ('condition', models.CharField(choices=[('full', 'جاهز للبيع (ممتلئ)'), ('empty', 'فارغ (تحت التعبئة)'), ('maintenance', 'قيد الصيانة')], default='full', max_length=20, verbose_name='حالة الوارد')),
                ('location', models.CharField(default='المستودع الرئيسي (أ)', max_length=150, verbose_name='موقع التخزين')),
                ('received_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='تاريخ الاستلام')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchases', to='core.product', verbose_name='الصنف')),
                ('received_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='استلمها')),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchases', to='core.account', verbose_name='المورد')),
            ],
            options={
                'verbose_name': 'شحنة واردة',
                'verbose_name_plural': 'المشتريات / الشحنات الواردة',
                'ordering': ['-received_at'],
            },
        ),
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_method', models.CharField(choices=[('cash', 'نقدي / كاش'), ('bank', 'تطبيق بنكي'), ('credit', 'آجل / ديون مستحقة')], default='cash', max_length=20, verbose_name='طريقة الدفع')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='تاريخ الفاتورة')),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sales', to='core.account', verbose_name='الوكيل / العميل')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='أصدرها')),
            ],
            options={
                'verbose_name': 'فاتورة بيع',
                'verbose_name_plural': 'المبيعات والفواتير',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='الكمية')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='سعر الوحدة وقت البيع')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sale_items', to='core.product', verbose_name='الصنف')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='core.sale', verbose_name='الفاتورة')),
            ],
            options={
                'verbose_name': 'بند فاتورة',
                'verbose_name_plural': 'بنود الفواتير',
            },
        ),
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('in', 'شحنة واردة'), ('out', 'صرف / توزيع'), ('maintenance', 'فرز للصيانة'), ('adjust', 'تسوية جرد')], max_length=20, verbose_name='نوع الحركة')),
                ('quantity', models.IntegerField(verbose_name='الكمية (موجب للوارد، سالب للصادر)')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='البيان')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='التوقيت')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='نفذها')),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movements', to='core.product', verbose_name='الصنف')),
                ('related_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.account', verbose_name='الحساب المرتبط')),
            ],
            options={
                'verbose_name': 'حركة مخزون',
                'verbose_name_plural': 'سجل التحركات',
                'ordering': ['-created_at'],
            },
        ),
    ]
