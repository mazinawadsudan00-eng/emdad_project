"""
منطق الأعمال (Business Logic) لمنصة إمداد الرقمية - مجمع نابلس للغاز.
"""

import datetime
import os
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import role_required
from .forms import (
    AccountForm,
    PurchaseForm,
    SaleForm,
    SettleForm,
    StockItemForm,
    StyledAuthenticationForm,
)
from .models import (
    Account,
    Product,
    Purchase,
    Sale,
    SaleItem,
    StockItem,
    StockMovement,
)


# ============================================================
# دعم PDF واللغة العربية
# ============================================================

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )

    import arabic_reshaper
    from bidi.algorithm import get_display

    PDF_AVAILABLE = True

except ImportError:
    PDF_AVAILABLE = False


def _arabic_text(text):
    """
    تجهيز النص العربي ليظهر بشكل صحيح داخل ReportLab.
    """
    if text is None:
        return ""

    text = str(text)

    if not text:
        return ""

    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def _find_arabic_font():
    """
    البحث عن خط يدعم العربية.
    يمكنك أيضًا وضع Cairo-Regular.ttf داخل static/fonts/.
    """

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    possible_fonts = [
        # داخل المشروع
        os.path.join(base_dir, "static", "fonts", "Cairo-Regular.ttf"),
        os.path.join(base_dir, "static", "fonts", "Cairo.ttf"),
        os.path.join(base_dir, "static", "fonts", "DejaVuSans.ttf"),

        # Windows
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",

        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",

        # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return font_path

    return None


def _register_pdf_font():
    """
    تسجيل الخط العربي مرة واحدة.
    """

    if not PDF_AVAILABLE:
        return None

    font_path = _find_arabic_font()

    if not font_path:
        return None

    font_name = "EmdadArabic"

    try:
        pdfmetrics.getFont(font_name)
        return font_name
    except Exception:
        pass

    try:
        pdfmetrics.registerFont(
            TTFont(font_name, font_path)
        )
        return font_name
    except Exception:
        return None


# ============================================================
# تسجيل الدخول
# ============================================================

class EmdadLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


# ============================================================
# لوحة التحكم الرئيسية
# ============================================================

def _exponential_smoothing(values, alpha=0.5):
    """تنبؤ بسيط بالطلب باستخدام المتوسط المتحرك الأسي."""

    if not values:
        return []

    smoothed = [float(values[0])]

    for v in values[1:]:
        smoothed.append(
            alpha * float(v) +
            (1 - alpha) * smoothed[-1]
        )

    return [round(v) for v in smoothed]


@login_required
def dashboard(request):

    full_qs = StockItem.objects.filter(
        condition=StockItem.Condition.FULL
    )

    ready_qty = full_qs.aggregate(
        t=Sum('quantity')
    )['t'] or 0

    empty_qty = StockItem.objects.filter(
        condition=StockItem.Condition.EMPTY
    ).aggregate(
        t=Sum('quantity')
    )['t'] or 0

    maintenance_qty = StockItem.objects.filter(
        condition=StockItem.Condition.MAINTENANCE
    ).aggregate(
        t=Sum('quantity')
    )['t'] or 0

    # ============================================================
    # تجميع الكميات حسب نوع/اسم المنتج لكل حالة أسطوانات
    # ============================================================

    ready_by_product = (
        StockItem.objects.filter(condition=StockItem.Condition.FULL)
        .values('product__name')
        .annotate(total=Sum('quantity'))
        .order_by('-total')
    )

    empty_by_product = (
        StockItem.objects.filter(condition=StockItem.Condition.EMPTY)
        .values('product__name')
        .annotate(total=Sum('quantity'))
        .order_by('-total')
    )

    maintenance_by_product = (
        StockItem.objects.filter(condition=StockItem.Condition.MAINTENANCE)
        .values('product__name')
        .annotate(total=Sum('quantity'))
        .order_by('-total')
    )

    today = timezone.localdate()

    # 1. إيرادات اليوم
    today_revenue = SaleItem.objects.filter(
        sale__created_at__date=today
    ).aggregate(
        t=Sum(F('quantity') * F('unit_price'))
    )['t'] or Decimal('0')

    # 2. تكلفة مبيعات اليوم (لحساب صافي الربح)
    today_items = SaleItem.objects.filter(sale__created_at__date=today)
    today_cost = Decimal('0')

    for item in today_items:
        cost = getattr(item.product, 'cost_price', None)
        if cost is None:

            last_purchase = Purchase.objects.filter(
                product=item.product
            ).order_by('-received_at').first()

            cost = last_purchase.unit_cost if last_purchase else Decimal('0')

        today_cost += item.quantity * cost

    # 3. صافي ربح اليوم
    net_profit = today_revenue - today_cost

    start_day = today - datetime.timedelta(days=5)

    daily = (
        SaleItem.objects
        .filter(
            sale__created_at__date__gte=start_day
        )
        .annotate(
            day=TruncDate('sale__created_at')
        )
        .values('day')
        .annotate(
            qty=Sum('quantity')
        )
        .order_by('day')
    )

    by_day = {
        row['day']: row['qty']
        for row in daily
    }

    labels = []
    actual = []

    weekday_names = [
        'الإثنين',
        'الثلاثاء',
        'الأربعاء',
        'الخميس',
        'الجمعة',
        'السبت',
        'الأحد'
    ]

    for i in range(6):
        d = start_day + datetime.timedelta(days=i)

        labels.append(
            weekday_names[d.weekday()]
        )

        actual.append(
            by_day.get(d, 0)
        )

    forecast = _exponential_smoothing(
        actual,
        alpha=0.5
    )

    recent_movements = (
        StockMovement.objects
        .select_related(
            'product',
            'created_by',
            'related_account'
        )
        .order_by('-created_at')[:8]
    )

    context = {
        'ready_qty': ready_qty,
        'empty_qty': empty_qty,
        'maintenance_qty': maintenance_qty,
        'today_revenue': today_revenue,
        'net_profit': net_profit,
        'ready_by_product': ready_by_product,
        'empty_by_product': empty_by_product,
        'maintenance_by_product': maintenance_by_product,
        'chart_labels': labels,
        'chart_actual': actual,
        'chart_forecast': forecast,
        'recent_movements': recent_movements,
        'low_stock_items': (
            full_qs
            .filter(
                quantity__lte=F(
                    'product__min_stock_level'
                )
            )
            .select_related('product')[:5]
        ),
    }

    return render(
        request,
        'dashboard/dashboard.html',
        context
    )


# ============================================================
# إدارة المخزون
# ============================================================

@login_required
def inventory_list(request):

    items = (
        StockItem.objects
        .select_related('product')
        .order_by(
            'product__code',
            'condition'
        )
    )

    q = request.GET.get('q', '').strip()

    if q:
        items = items.filter(
            Q(product__code__icontains=q)
            |
            Q(product__name__icontains=q)
        ).distinct()

    category = request.GET.get(
        'category',
        ''
    )

    if category:
        items = items.filter(
            product__category=category
        )

    condition = request.GET.get(
        'condition',
        ''
    )

    if condition:
        items = items.filter(
            condition=condition
        )

    purchase_form = PurchaseForm()

    context = {
        'items': items,
        'purchase_form': purchase_form,
        'categories': Product.Category.choices,
        'conditions': StockItem.Condition.choices,
        'q': q,
        'selected_category': category,
        'selected_condition': condition,
    }

    return render(
        request,
        'inventory/inventory.html',
        context
    )


@role_required('admin', 'warehouse')
def add_stock(request):

    if request.method == 'POST':

        form = PurchaseForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                purchase = form.save(
                    commit=False
                )

                purchase.received_by = request.user
                purchase.save()

                stock_item, _ = (
                    StockItem.objects.get_or_create(
                        product=purchase.product,
                        condition=purchase.condition,
                        location=purchase.location,
                        defaults={'quantity': 0},
                    )
                )

                stock_item.quantity = (
                    F('quantity') +
                    purchase.quantity
                )

                stock_item.save(
                    update_fields=[
                        'quantity',
                        'updated_at'
                    ]
                )

                StockMovement.objects.create(
                    product=purchase.product,
                    movement_type=(
                        StockMovement
                        .MovementType
                        .IN
                    ),
                    quantity=purchase.quantity,
                    related_account=purchase.supplier,
                    note=(
                        f'شحنة واردة'
                        f'{" من " + purchase.supplier.name if purchase.supplier else ""}'
                    ),
                    created_by=request.user,
                )

            messages.success(
                request,
                'تم تسجيل الشحنة وتحديث المخزون بنجاح.'
            )

        else:

            messages.error(
                request,
                'تعذر تسجيل الشحنة، يرجى مراجعة البيانات المدخلة.'
            )

    return redirect(
        'inventory_list'
    )


@role_required('admin', 'warehouse')
def edit_stock_item(request, pk):

    item = get_object_or_404(
        StockItem,
        pk=pk
    )

    if request.method == 'POST':

        form = StockItemForm(
            request.POST,
            instance=item
        )

        if form.is_valid():

            try:

                form.save()

                messages.success(
                    request,
                    'تم تحديث سجل المخزون بنجاح.'
                )

            except IntegrityError:

                messages.error(
                    request,
                    'يوجد سجل آخر لنفس الصنف بنفس الحالة والموقع.'
                )

        else:

            messages.error(
                request,
                'تعذر حفظ التعديلات، يرجى مراجعة البيانات.'
            )

    return redirect(
        'inventory_list'
    )


@role_required('admin', 'warehouse')
def delete_stock_item(request, pk):

    item = get_object_or_404(
        StockItem,
        pk=pk
    )

    if item.quantity > 0:

        messages.error(
            request,
            'لا يمكن حذف سجل مخزون لا يزال يحتوي على كمية. صفّر الكمية أولاً.'
        )

    else:

        item.delete()

        messages.success(
            request,
            'تم حذف سجل المخزون.'
        )

    return redirect(
        'inventory_list'
    )


@role_required('admin', 'warehouse')
def send_to_maintenance(request, pk):

    source = get_object_or_404(
        StockItem,
        pk=pk
    )

    if request.method == 'POST':

        try:
            qty = int(
                request.POST.get(
                    'qty',
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):
            qty = 0

        if qty <= 0 or qty > source.quantity:

            messages.error(
                request,
                'الكمية المدخلة غير صحيحة أو أكبر من الكمية المتوفرة.'
            )

        else:

            with transaction.atomic():

                source.quantity = (
                    F('quantity') - qty
                )

                source.save(
                    update_fields=[
                        'quantity',
                        'updated_at'
                    ]
                )

                dest, _ = (
                    StockItem.objects.get_or_create(
                        product=source.product,
                        condition=(
                            StockItem
                            .Condition
                            .MAINTENANCE
                        ),
                        location='ورشة الصيانة الهندسية',
                        defaults={'quantity': 0},
                    )
                )

                dest.quantity = (
                    F('quantity') + qty
                )

                dest.save(
                    update_fields=[
                        'quantity',
                        'updated_at'
                    ]
                )

                StockMovement.objects.create(
                    product=source.product,
                    movement_type=(
                        StockMovement
                        .MovementType
                        .MAINTENANCE
                    ),
                    quantity=qty,
                    note='فرز أسطوانات للصيانة',
                    created_by=request.user,
                )

            messages.success(
                request,
                f'تم نقل {qty} وحدة إلى قيد الصيانة.'
            )

    return redirect(
        'inventory_list'
    )


# ============================================================
# المبيعات والفواتير
# ============================================================

@login_required
def sales_page(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)

        if form.is_valid():

            product = form.cleaned_data['product']
            qty = form.cleaned_data['quantity']
            account = form.cleaned_data.get('account')
            new_customer_name = (
                form.cleaned_data.get('new_customer_name') or ''
            ).strip()
            payment_method = form.cleaned_data['payment_method']

            if not account and new_customer_name:

                account = Account.objects.create(
                    name=new_customer_name,
                    account_type=Account.AccountType.CUSTOMER,
                    is_active=True,
                )

            available = product.total_available

            if qty > available:

                messages.error(
                    request,
                    f'الكمية المطلوبة ({qty}) غير متوفرة في المخزون. '
                    f'المتاح حالياً: {available}.',
                )

            else:

                with transaction.atomic():

                    sale = Sale.objects.create(
                        account=account,
                        payment_method=payment_method,
                        created_by=request.user,
                    )

                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=qty,
                        unit_price=product.unit_price,
                    )

                    remaining = qty

                    stock_items = StockItem.objects.filter(
                        product=product,
                        condition=StockItem.Condition.FULL,
                        quantity__gt=0,
                    ).order_by('-quantity')

                    for stock_item in stock_items:

                        if remaining <= 0:
                            break

                        deduct = min(
                            stock_item.quantity,
                            remaining
                        )

                        stock_item.quantity = F('quantity') - deduct

                        stock_item.save(
                            update_fields=[
                                'quantity',
                                'updated_at'
                            ]
                        )

                        remaining -= deduct

                        empty_stock, _ = StockItem.objects.get_or_create(
                            product=product,
                            condition=StockItem.Condition.EMPTY,
                            location='المستودع الرئيسي (أ)',
                            defaults={'quantity': 0},
                        )

                        empty_stock.quantity = F('quantity') + qty

                        empty_stock.save(
                            update_fields=[
                                'quantity',
                                'updated_at'
                            ]
                        )

                    customer_display = (
                        account.name
                        if account
                        else 'عميل نقدي'
                    )

                    StockMovement.objects.create(
                        product=product,
                        movement_type=StockMovement.MovementType.OUT,
                        quantity=-qty,
                        related_account=account,
                        note=f'توزيع/بيع لـ ({customer_display})',
                        created_by=request.user,
                    )

                    if (
                        account
                        and payment_method == Sale.PaymentMethod.CREDIT
                    ):

                        account.balance = F('balance') + sale.total

                        account.save(
                            update_fields=['balance']
                        )

                messages.success(
                    request,
                    f'تم إصدار الفاتورة {sale.invoice_no} بنجاح.'
                )

                return redirect('sales_page')

        else:

            messages.error(
                request,
                'تعذر إصدار الفاتورة، يرجى مراجعة بيانات النموذج.'
            )

    else:

        form = SaleForm()

    recent_sales = (
        Sale.objects
        .select_related('account')
        .prefetch_related('items__product')
        .order_by('-created_at')[:15]
    )

    products = Product.objects.filter(
        is_active=True,
        is_sellable=True
    )

    context = {
        'form': form,
        'recent_sales': recent_sales,
        'products': products,
    }

    return render(
        request,
        'sales/sales.html',
        context
    )


# ============================================================
# العملاء والموردون
# ============================================================

@login_required
def customers_page(request):

    if request.method == 'POST':

        form = AccountForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'تم إنشاء الحساب بنجاح.'
            )

            return redirect(
                'customers_page'
            )

        messages.error(
            request,
            'تعذر حفظ الحساب، يرجى مراجعة البيانات المدخلة.'
        )

    else:

        form = AccountForm()

    accounts = Account.objects.all().order_by(
        'name'
    )

    customer_debt = (
        Account.objects
        .filter(balance__gt=0)
        .aggregate(
            t=Sum('balance')
        )['t']
        or Decimal('0')
    )

    supplier_payable = (
        Account.objects
        .filter(balance__lt=0)
        .aggregate(
            t=Sum('balance')
        )['t']
        or Decimal('0')
    )

    active_contracts = (
        Account.objects
        .filter(is_active=True)
        .count()
    )

    context = {
        'accounts': accounts,
        'form': form,
        'customer_debt': customer_debt,
        'supplier_payable': abs(
            supplier_payable
        ),
        'active_contracts': active_contracts,
        'settle_form': SettleForm(),
    }

    return render(
        request,
        'partners/customers.html',
        context
    )


@role_required('admin', 'accountant')
def settle_account(request, pk):

    account = get_object_or_404(
        Account,
        pk=pk
    )

    if request.method == 'POST':

        form = SettleForm(
            request.POST
        )

        if form.is_valid():

            amount = form.cleaned_data[
                'amount'
            ]

            if account.balance > 0:

                account.balance = max(
                    Decimal('0'),
                    account.balance - amount
                )

                messages.success(
                    request,
                    f'تم تسجيل تحصيل {amount} ج.س من حساب {account.name}.'
                )

            elif account.balance < 0:

                account.balance = min(
                    Decimal('0'),
                    account.balance + amount
                )

                messages.success(
                    request,
                    f'تم تسجيل دفع {amount} ج.س لحساب {account.name}.'
                )

            else:

                messages.info(
                    request,
                    'رصيد هذا الحساب صفر بالفعل، لا توجد مستحقات.'
                )

            account.save(
                update_fields=['balance']
            )

        else:

            messages.error(
                request,
                'المبلغ المدخل غير صحيح.'
            )

    return redirect(
        'customers_page'
    )


# ============================================================
# التقارير
# ============================================================

def _parse_report_range(request):

    today = timezone.localdate()

    default_start = (
        today -
        datetime.timedelta(days=30)
    )

    try:

        start = datetime.date.fromisoformat(
            request.GET.get(
                'start',
                ''
            )
        )

    except (
        ValueError,
        TypeError
    ):

        start = default_start

    try:

        end = datetime.date.fromisoformat(
            request.GET.get(
                'end',
                ''
            )
        )

    except (
        ValueError,
        TypeError
    ):

        end = today

    if start > end:
        start, end = end, start

    return start, end


def _get_report_data(start, end):

    sales = (
        Sale.objects
        .filter(
            created_at__date__range=(
                start,
                end
            )
        )
        .select_related(
            'account',
            'created_by'
        )
        .prefetch_related(
            'items__product'
        )
        .order_by('-created_at')
    )

    purchases = (
        Purchase.objects
        .filter(
            received_at__date__range=(
                start,
                end
            )
        )
        .select_related(
            'product',
            'supplier',
            'received_by'
        )
        .order_by('-received_at')
    )

    total_sales = Decimal('0')
    total_sold_qty = 0

    cash_sales = Decimal('0')
    bank_sales = Decimal('0')
    credit_sales = Decimal('0')

    for sale in sales:

        sale_total = sale.total

        total_sales += sale_total

        if (
            sale.payment_method ==
            Sale.PaymentMethod.CASH
        ):
            cash_sales += sale_total

        elif (
            sale.payment_method ==
            Sale.PaymentMethod.BANK
        ):
            bank_sales += sale_total

        elif (
            sale.payment_method ==
            Sale.PaymentMethod.CREDIT
        ):
            credit_sales += sale_total

        for item in sale.items.all():
            total_sold_qty += item.quantity

    total_purchases = sum(
        (
            purchase.total_cost
            for purchase in purchases
        ),
        Decimal('0')
    )

    total_purchase_qty = sum(
        (
            purchase.quantity
            for purchase in purchases
        ),
        0
    )

    top_products = (
        SaleItem.objects
        .filter(
            sale__created_at__date__range=(
                start,
                end
            )
        )
        .values(
            'product__code',
            'product__name'
        )
        .annotate(
            total_qty=Sum('quantity'),
            total_value=Sum(
                F('quantity') *
                F('unit_price')
            )
        )
        .order_by('-total_qty')[:10]
    )

    daily_sales = (
        SaleItem.objects
        .filter(
            sale__created_at__date__range=(
                start,
                end
            )
        )
        .annotate(
            day=TruncDate(
                'sale__created_at'
            )
        )
        .values('day')
        .annotate(
            total=Sum(
                F('quantity') *
                F('unit_price')
            ),
            quantity=Sum('quantity')
        )
        .order_by('day')
    )

    stock_summary = (
        StockItem.objects
        .select_related('product')
        .values(
            'product__code',
            'product__name',
            'product__size_kg',
            'condition'
        )
        .annotate(
            quantity=Sum('quantity')
        )
        .order_by(
            'product__code',
            'condition'
        )
    )

    context = {
        'sales': sales,
        'purchases': purchases,

        'total_sales': total_sales,
        'total_purchases': total_purchases,

        'sales_count': sales.count(),
        'purchase_count': purchases.count(),

        'total_sold_qty': total_sold_qty,
        'total_purchase_qty': total_purchase_qty,

        'cash_sales': cash_sales,
        'bank_sales': bank_sales,
        'credit_sales': credit_sales,

        'top_products': top_products,
        'daily_sales': daily_sales,
        'stock_summary': stock_summary,
    }

    return context


@login_required
def reports_page(request):

    start, end = _parse_report_range(
        request
    )

    data = _get_report_data(
        start,
        end
    )

    context = {
        'start': start,
        'end': end,
        **data,
    }

    return render(
        request,
        'dashboard/reports.html',
        context
    )


# ============================================================
# تصدير التقرير PDF
# ============================================================

@login_required
def export_sales_pdf(request):

    if not PDF_AVAILABLE:

        return HttpResponse(
            """
            <h3>خطأ</h3>
            <p>
            يجب تثبيت مكتبات PDF أولاً:
            </p>
            <pre>
            pip install reportlab arabic-reshaper python-bidi
            </pre>
            """,
            content_type='text/html; charset=utf-8',
            status=500
        )

    start, end = _parse_report_range(
        request
    )

    data = _get_report_data(
        start,
        end
    )

    font_name = _register_pdf_font()

    if not font_name:

        return HttpResponse(
            """
            <h3>خطأ في الخط العربي</h3>
            <p>
            لم يتم العثور على خط عربي مناسب.
            ضع ملف Cairo-Regular.ttf داخل:
            </p>
            <pre>
            static/fonts/Cairo-Regular.ttf
            </pre>
            """,
            content_type='text/html; charset=utf-8',
            status=500
        )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename="report_{start}_{end}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title='تقرير إمداد',
        author='منصة إمداد الرقمية',
    )

    title_style = ParagraphStyle(
        'ArabicTitle',
        fontName=font_name,
        fontSize=18,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor(
            '#17365D'
        ),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        'ArabicSubtitle',
        fontName=font_name,
        fontSize=10,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor(
            '#666666'
        ),
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        'ArabicHeading',
        fontName=font_name,
        fontSize=12,
        leading=18,
        alignment=TA_RIGHT,
        textColor=colors.HexColor(
            '#17365D'
        ),
        spaceBefore=8,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        'ArabicNormal',
        fontName=font_name,
        fontSize=8,
        leading=13,
        alignment=TA_RIGHT,
    )

    center_style = ParagraphStyle(
        'ArabicCenter',
        fontName=font_name,
        fontSize=8,
        leading=13,
        alignment=TA_CENTER,
    )

    story = []

    story.append(
        Paragraph(
            _arabic_text(
                'منصة إمداد الرقمية'
            ),
            title_style
        )
    )

    story.append(
        Paragraph(
            _arabic_text(
                'تقرير المبيعات والمشتريات والتحليلات'
            ),
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            _arabic_text(
                f'الفترة من {start.strftime("%Y-%m-%d")} '
                f'إلى {end.strftime("%Y-%m-%d")}'
            ),
            subtitle_style
        )
    )

    story.append(
        Spacer(
            1,
            5
        )
    )

    summary_data = [
        [
            Paragraph(
                _arabic_text('إجمالي المبيعات'),
                center_style
            ),
            Paragraph(
                _arabic_text('إجمالي المشتريات'),
                center_style
            ),
            Paragraph(
                _arabic_text('عدد الفواتير'),
                center_style
            ),
            Paragraph(
                _arabic_text('عدد الشحنات'),
                center_style
            ),
        ],
        [
            Paragraph(
                _arabic_text(
                    f'{data["total_sales"]:,.0f} ج.س'
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{data["total_purchases"]:,.0f} ج.س'
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    str(data['sales_count'])
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    str(data['purchase_count'])
                ),
                center_style
            ),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            45 * mm,
            45 * mm,
            40 * mm,
            40 * mm,
        ],
        repeatRows=1,
    )

    summary_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#EAF2F8')
            ),
            (
                'BACKGROUND',
                (0, 1),
                (-1, 1),
                colors.white
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#D5D8DC')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
        ])
    )

    story.append(
        summary_table
    )

    story.append(
        Spacer(
            1,
            8
        )
    )

    story.append(
        Paragraph(
            _arabic_text(
                'تحليل المبيعات حسب طريقة الدفع'
            ),
            heading_style
        )
    )

    payment_data = [
        [
            Paragraph(
                _arabic_text('طريقة الدفع'),
                center_style
            ),
            Paragraph(
                _arabic_text('القيمة'),
                center_style
            ),
        ],
        [
            Paragraph(
                _arabic_text('نقدي / كاش'),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{data["cash_sales"]:,.0f} ج.س'
                ),
                center_style
            ),
        ],
        [
            Paragraph(
                _arabic_text('تطبيق بنكي'),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{data["bank_sales"]:,.0f} ج.س'
                ),
                center_style
            ),
        ],
        [
            Paragraph(
                _arabic_text('آجل / ديون'),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{data["credit_sales"]:,.0f} ج.س'
                ),
                center_style
            ),
        ],
    ]

    payment_table = Table(
        payment_data,
        colWidths=[
            90 * mm,
            80 * mm
        ],
    )

    payment_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#D5F5E3')
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#D5D8DC')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'ALIGN',
                (0, 0),
                (-1, -1),
                'CENTER'
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                6
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                6
            ),
        ])
    )

    story.append(
        payment_table
    )

    story.append(
        Paragraph(
            _arabic_text(
                'أكثر الأصناف مبيعًا'
            ),
            heading_style
        )
    )

    top_products_data = [
        [
            Paragraph(
                _arabic_text('الصنف'),
                center_style
            ),
            Paragraph(
                _arabic_text('الرمز'),
                center_style
            ),
            Paragraph(
                _arabic_text('الكمية'),
                center_style
            ),
            Paragraph(
                _arabic_text('قيمة المبيعات'),
                center_style
            ),
        ]
    ]

    for item in data['top_products']:

        top_products_data.append([
            Paragraph(
                _arabic_text(
                    item['product__name']
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    item['product__code']
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    str(item['total_qty'])
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{item["total_value"]:,.0f} ج.س'
                ),
                center_style
            ),
        ])

    if len(top_products_data) == 1:

        top_products_data.append([
            Paragraph(
                _arabic_text(
                    'لا توجد مبيعات ضمن الفترة المحددة'
                ),
                center_style
            ),
            '',
            '',
            '',
        ])

    top_table = Table(
        top_products_data,
        colWidths=[
            65 * mm,
            35 * mm,
            30 * mm,
            50 * mm,
        ],
        repeatRows=1,
    )

    top_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#EAF2F8')
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#D5D8DC')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                5
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                5
            ),
        ])
    )

    story.append(
        top_table
    )

    story.append(
        Paragraph(
            _arabic_text(
                'المبيعات اليومية'
            ),
            heading_style
        )
    )

    daily_data = [
        [
            Paragraph(
                _arabic_text('التاريخ'),
                center_style
            ),
            Paragraph(
                _arabic_text('الكمية'),
                center_style
            ),
            Paragraph(
                _arabic_text('قيمة المبيعات'),
                center_style
            ),
        ]
    ]

    for row in data['daily_sales']:

        daily_data.append([
            Paragraph(
                _arabic_text(
                    row['day'].strftime(
                        '%Y-%m-%d'
                    )
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    str(row['quantity'])
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{row["total"]:,.0f} ج.س'
                ),
                center_style
            ),
        ])

    if len(daily_data) == 1:

        daily_data.append([
            Paragraph(
                _arabic_text(
                    'لا توجد مبيعات ضمن الفترة'
                ),
                center_style
            ),
            '',
            '',
        ])

    daily_table = Table(
        daily_data,
        colWidths=[
            60 * mm,
            50 * mm,
            70 * mm,
        ],
        repeatRows=1,
    )

    daily_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#D5F5E3')
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#D5D8DC')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                5
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                5
            ),
        ])
    )

    story.append(
        daily_table
    )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            _arabic_text(
                'تفاصيل فواتير المبيعات'
            ),
            heading_style
        )
    )

    sales_data = [
        [
            Paragraph(
                _arabic_text('الفاتورة'),
                center_style
            ),
            Paragraph(
                _arabic_text('التاريخ'),
                center_style
            ),
            Paragraph(
                _arabic_text('العميل'),
                center_style
            ),
            Paragraph(
                _arabic_text('الصنف'),
                center_style
            ),
            Paragraph(
                _arabic_text('الكمية'),
                center_style
            ),
            Paragraph(
                _arabic_text('الإجمالي'),
                center_style
            ),
        ]
    ]

    for sale in data['sales']:

        for item in sale.items.all():

            sales_data.append([
                Paragraph(
                    _arabic_text(
                        sale.invoice_no
                    ),
                    center_style
                ),
                Paragraph(
                    _arabic_text(
                        sale.created_at.strftime(
                            '%Y-%m-%d'
                        )
                    ),
                    center_style
                ),
                Paragraph(
                    _arabic_text(
                        sale.account.name
                        if sale.account
                        else 'عميل نقدي'
                    ),
                    center_style
                ),
                Paragraph(
                    _arabic_text(
                        item.product.name
                    ),
                    center_style
                ),
                Paragraph(
                    _arabic_text(
                        str(item.quantity)
                    ),
                    center_style
                ),
                Paragraph(
                    _arabic_text(
                        f'{item.subtotal:,.0f}'
                    ),
                    center_style
                ),
            ])

    if len(sales_data) == 1:

        sales_data.append([
            Paragraph(
                _arabic_text(
                    'لا توجد فواتير ضمن الفترة المحددة'
                ),
                center_style
            ),
            '',
            '',
            '',
            '',
            '',
        ])

    sales_table = Table(
        sales_data,
        colWidths=[
            27 * mm,
            28 * mm,
            43 * mm,
            40 * mm,
            20 * mm,
            30 * mm,
        ],
        repeatRows=1,
    )

    sales_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#D5F5E3')
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor('#D5D8DC')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'FONTSIZE',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                4
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                4
            ),
        ])
    )

    story.append(
        sales_table
    )

    story.append(
        Paragraph(
            _arabic_text(
                'تفاصيل المشتريات والشحنات الواردة'
            ),
            heading_style
        )
    )

    purchase_data = [
        [
            Paragraph(
                _arabic_text('التاريخ'),
                center_style
            ),
            Paragraph(
                _arabic_text('الصنف'),
                center_style
            ),
            Paragraph(
                _arabic_text('المورد'),
                center_style
            ),
            Paragraph(
                _arabic_text('الكمية'),
                center_style
            ),
            Paragraph(
                _arabic_text('تكلفة الوحدة'),
                center_style
            ),
            Paragraph(
                _arabic_text('الإجمالي'),
                center_style
            ),
        ]
    ]

    for purchase in data['purchases']:

        purchase_data.append([
            Paragraph(
                _arabic_text(
                    purchase.received_at.strftime(
                        '%Y-%m-%d'
                    )
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    purchase.product.name
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    purchase.supplier.name
                    if purchase.supplier
                    else 'غير محدد'
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    str(purchase.quantity)
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{purchase.unit_cost:,.0f}'
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    f'{purchase.total_cost:,.0f}'
                ),
                center_style
            ),
        ])

    if len(purchase_data) == 1:

        purchase_data.append([
            Paragraph(
                _arabic_text(
                    'لا توجد مشتريات ضمن الفترة المحددة'
                ),
                center_style
            ),
            '',
            '',
            '',
            '',
            '',
        ])

    purchase_table = Table(
        purchase_data,
        colWidths=[
            28 * mm,
            42 * mm,
            42 * mm,
            20 * mm,
            30 * mm,
            30 * mm,
        ],
        repeatRows=1,
    )

    purchase_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#EAF2F8')
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor('#D5D8DC')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'FONTSIZE',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                4
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                4
            ),
        ])
    )

    story.append(
        purchase_table
    )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            _arabic_text(
                'ملخص المخزون الحالي'
            ),
            heading_style
        )
    )

    stock_data = [
        [
            Paragraph(
                _arabic_text('الصنف'),
                center_style
            ),
            Paragraph(
                _arabic_text('الرمز'),
                center_style
            ),
            Paragraph(
                _arabic_text('الحالة'),
                center_style
            ),
            Paragraph(
                _arabic_text('الكمية'),
                center_style
            ),
        ]
    ]

    for item in data['stock_summary']:

        condition_labels = dict(
            StockItem.Condition.choices
        )

        condition_label = condition_labels.get(
            item['condition'],
            item['condition']
        )

        stock_data.append([
            Paragraph(
                _arabic_text(
                    item['product__name']
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    item['product__code']
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    condition_label
                ),
                center_style
            ),
            Paragraph(
                _arabic_text(
                    str(item['quantity'])
                ),
                center_style
            ),
        ])

    if len(stock_data) == 1:

        stock_data.append([
            Paragraph(
                _arabic_text(
                    'لا توجد بيانات مخزون'
                ),
                center_style
            ),
            '',
            '',
            '',
        ])

    stock_table = Table(
        stock_data,
        colWidths=[
            65 * mm,
            35 * mm,
            55 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    stock_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#FDEBD0')
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor('#D5D8DC')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                5
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                5
            ),
        ])
    )

    story.append(
        stock_table
    )

    story.append(
        Spacer(
            1,
            12
        )
    )

    story.append(
        Paragraph(
            _arabic_text(
                'ملاحظة: إجمالي المشتريات يمثل قيمة الشحنات '
                'المستلمة خلال الفترة، ولا يمثل تكلفة البضاعة '
                'المباعة.'
            ),
            normal_style
        )
    )

    def add_page_number(canvas, doc):

        canvas.saveState()

        canvas.setFont(
            font_name,
            7
        )

        canvas.drawCentredString(
            A4[0] / 2,
            8 * mm,
            _arabic_text(
                f'منصة إمداد الرقمية - صفحة {doc.page}'
            )
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return response


# ============================================================
# تسجيل الخروج
# ============================================================

def custom_logout(request):

    logout(request)

    return redirect(
        'login'
    )