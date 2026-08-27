"""
منطق الأعمال (Business Logic) لمنصة إمداد الرقمية - مجمع نابلس للغاز.
يطبّق العمليات الموصوفة في الفصل الثالث من وثيقة البحث: تسجيل الدخول،
إدارة المخزون، تنفيذ عمليات البيع، إدارة العملاء/الموردين، التقارير ولوحة المعلومات.
"""
import csv
import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import role_required
from .forms import (
    AccountForm, PurchaseForm, SaleForm, SettleForm, StockItemForm,
    StyledAuthenticationForm,
)
from .models import Account, Product, Purchase, Sale, SaleItem, StockItem, StockMovement


class EmdadLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


# ============================================================
# لوحة التحكم الرئيسية (Dashboard)
# ============================================================

def _exponential_smoothing(values, alpha=0.5):
    """تنبؤ بسيط بالطلب باستخدام المتوسط المتحرك الأسي (Simple Exponential Smoothing)."""
    if not values:
        return []
    smoothed = [float(values[0])]
    for v in values[1:]:
        smoothed.append(alpha * float(v) + (1 - alpha) * smoothed[-1])
    return [round(v) for v in smoothed]


@login_required
def dashboard(request):
    full_qs = StockItem.objects.filter(condition=StockItem.Condition.FULL)
    ready_qty = full_qs.aggregate(t=Sum('quantity'))['t'] or 0
    empty_qty = StockItem.objects.filter(condition=StockItem.Condition.EMPTY).aggregate(
        t=Sum('quantity'))['t'] or 0
    maintenance_qty = StockItem.objects.filter(condition=StockItem.Condition.MAINTENANCE).aggregate(
        t=Sum('quantity'))['t'] or 0

    today = timezone.localdate()
    today_revenue = SaleItem.objects.filter(sale__created_at__date=today).aggregate(
        t=Sum(F('quantity') * F('unit_price')))['t'] or Decimal('0')

    # بيانات آخر 6 أيام لمخطط المبيعات الفعلية مقابل الطلب المتوقع
    start_day = today - datetime.timedelta(days=5)
    daily = (
        SaleItem.objects.filter(sale__created_at__date__gte=start_day)
        .annotate(day=TruncDate('sale__created_at'))
        .values('day')
        .annotate(qty=Sum('quantity'))
        .order_by('day')
    )
    by_day = {row['day']: row['qty'] for row in daily}
    labels, actual = [], []
    weekday_names = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    for i in range(6):
        d = start_day + datetime.timedelta(days=i)
        labels.append(weekday_names[d.weekday()])
        actual.append(by_day.get(d, 0))
    forecast = _exponential_smoothing(actual, alpha=0.5)

    recent_movements = (
        StockMovement.objects.select_related('product', 'created_by', 'related_account')
        .order_by('-created_at')[:8]
    )

    context = {
        'ready_qty': ready_qty,
        'empty_qty': empty_qty,
        'maintenance_qty': maintenance_qty,
        'today_revenue': today_revenue,
        'chart_labels': labels,
        'chart_actual': actual,
        'chart_forecast': forecast,
        'recent_movements': recent_movements,
        'low_stock_items': full_qs.filter(quantity__lte=F('product__min_stock_level')).select_related('product')[:5],
    }
    return render(request, 'dashboard/dashboard.html', context)


# ============================================================
# إدارة المخزون (Inventory)
# ============================================================

@login_required
def inventory_list(request):
    items = StockItem.objects.select_related('product').order_by('product__code', 'condition')

    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(
            Q(product__code__icontains=q) | Q(product__name__icontains=q)
        ).distinct()

    category = request.GET.get('category', '')
    if category:
        items = items.filter(product__category=category)

    condition = request.GET.get('condition', '')
    if condition:
        items = items.filter(condition=condition)

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
    return render(request, 'inventory/inventory.html', context)


@role_required('admin', 'warehouse')
def add_stock(request):
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.received_by = request.user
                purchase.save()

                stock_item, _ = StockItem.objects.get_or_create(
                    product=purchase.product,
                    condition=purchase.condition,
                    location=purchase.location,
                    defaults={'quantity': 0},
                )
                stock_item.quantity = F('quantity') + purchase.quantity
                stock_item.save(update_fields=['quantity', 'updated_at'])

                StockMovement.objects.create(
                    product=purchase.product,
                    movement_type=StockMovement.MovementType.IN,
                    quantity=purchase.quantity,
                    related_account=purchase.supplier,
                    note=f'شحنة واردة{" من " + purchase.supplier.name if purchase.supplier else ""}',
                    created_by=request.user,
                )
            messages.success(request, 'تم تسجيل الشحنة وتحديث المخزون بنجاح.')
        else:
            messages.error(request, 'تعذر تسجيل الشحنة، يرجى مراجعة البيانات المدخلة.')
    return redirect('inventory_list')


@role_required('admin', 'warehouse')
def edit_stock_item(request, pk):
    item = get_object_or_404(StockItem, pk=pk)
    if request.method == 'POST':
        form = StockItemForm(request.POST, instance=item)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'تم تحديث سجل المخزون بنجاح.')
            except IntegrityError:
                messages.error(request, 'يوجد سجل آخر لنفس الصنف بنفس الحالة والموقع.')
        else:
            messages.error(request, 'تعذر حفظ التعديلات، يرجى مراجعة البيانات.')
    return redirect('inventory_list')


@role_required('admin', 'warehouse')
def delete_stock_item(request, pk):
    item = get_object_or_404(StockItem, pk=pk)
    if item.quantity > 0:
        messages.error(request, 'لا يمكن حذف سجل مخزون لا يزال يحتوي على كمية. صفّر الكمية أولاً.')
    else:
        item.delete()
        messages.success(request, 'تم حذف سجل المخزون.')
    return redirect('inventory_list')


@role_required('admin', 'warehouse')
def send_to_maintenance(request, pk):
    source = get_object_or_404(StockItem, pk=pk)
    if request.method == 'POST':
        try:
            qty = int(request.POST.get('qty', 0))
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0 or qty > source.quantity:
            messages.error(request, 'الكمية المدخلة غير صحيحة أو أكبر من الكمية المتوفرة.')
        else:
            with transaction.atomic():
                source.quantity = F('quantity') - qty
                source.save(update_fields=['quantity', 'updated_at'])
                dest, _ = StockItem.objects.get_or_create(
                    product=source.product,
                    condition=StockItem.Condition.MAINTENANCE,
                    location='ورشة الصيانة الهندسية',
                    defaults={'quantity': 0},
                )
                dest.quantity = F('quantity') + qty
                dest.save(update_fields=['quantity', 'updated_at'])
                StockMovement.objects.create(
                    product=source.product,
                    movement_type=StockMovement.MovementType.MAINTENANCE,
                    quantity=qty,
                    note='فرز أسطوانات للصيانة',
                    created_by=request.user,
                )
            messages.success(request, f'تم نقل {qty} وحدة إلى قيد الصيانة.')
    return redirect('inventory_list')


# ============================================================
# المبيعات والفواتير (Sales)
# ============================================================

@login_required
def sales_page(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            qty = form.cleaned_data['quantity']
            account = form.cleaned_data['account']
            payment_method = form.cleaned_data['payment_method']

            available = product.total_available
            if qty > available:
                messages.error(
                    request,
                    f'الكمية المطلوبة ({qty}) غير متوفرة في المخزون. المتاح حالياً: {available}.',
                )
            else:
                with transaction.atomic():
                    sale = Sale.objects.create(
                        account=account, payment_method=payment_method, created_by=request.user,
                    )
                    SaleItem.objects.create(
                        sale=sale, product=product, quantity=qty, unit_price=product.unit_price,
                    )
                    remaining = qty
                    for stock_item in StockItem.objects.filter(
                        product=product, condition=StockItem.Condition.FULL, quantity__gt=0,
                    ).order_by('-quantity'):
                        if remaining <= 0:
                            break
                        deduct = min(stock_item.quantity, remaining)
                        stock_item.quantity = F('quantity') - deduct
                        stock_item.save(update_fields=['quantity', 'updated_at'])
                        remaining -= deduct

                    StockMovement.objects.create(
                        product=product,
                        movement_type=StockMovement.MovementType.OUT,
                        quantity=-qty,
                        related_account=account,
                        note=f'توزيع/بيع لـ ({account.name if account else "عميل نقدي"})',
                        created_by=request.user,
                    )

                    if account and payment_method == Sale.PaymentMethod.CREDIT:
                        account.balance = F('balance') + sale.total
                        account.save(update_fields=['balance'])

                messages.success(request, f'تم إصدار الفاتورة {sale.invoice_no} بنجاح.')
                return redirect('sales_page')
        else:
            messages.error(request, 'تعذر إصدار الفاتورة، يرجى مراجعة بيانات النموذج.')
    else:
        form = SaleForm()

    recent_sales = (
        Sale.objects.select_related('account').prefetch_related('items__product')
        .order_by('-created_at')[:15]
    )
    products = Product.objects.filter(is_active=True, is_sellable=True)
    context = {'form': form, 'recent_sales': recent_sales, 'products': products}
    return render(request, 'sales/sales.html', context)


# ============================================================
# العملاء والموردون (Partners)
# ============================================================

@login_required
def customers_page(request):
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء الحساب بنجاح.')
            return redirect('customers_page')
        messages.error(request, 'تعذر حفظ الحساب، يرجى مراجعة البيانات المدخلة.')
    else:
        form = AccountForm()

    accounts = Account.objects.all().order_by('name')
    customer_debt = Account.objects.filter(balance__gt=0).aggregate(t=Sum('balance'))['t'] or Decimal('0')
    supplier_payable = Account.objects.filter(balance__lt=0).aggregate(t=Sum('balance'))['t'] or Decimal('0')
    active_contracts = Account.objects.filter(is_active=True).count()

    context = {
        'accounts': accounts,
        'form': form,
        'customer_debt': customer_debt,
        'supplier_payable': abs(supplier_payable),
        'active_contracts': active_contracts,
        'settle_form': SettleForm(),
    }
    return render(request, 'partners/customers.html', context)


@role_required('admin', 'accountant')
def settle_account(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        form = SettleForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            if account.balance > 0:
                account.balance = max(Decimal('0'), account.balance - amount)
                messages.success(request, f'تم تسجيل تحصيل {amount} ج.س من حساب {account.name}.')
            elif account.balance < 0:
                account.balance = min(Decimal('0'), account.balance + amount)
                messages.success(request, f'تم تسجيل دفع {amount} ج.س لحساب {account.name}.')
            else:
                messages.info(request, 'رصيد هذا الحساب صفر بالفعل، لا توجد مستحقات.')
            account.save(update_fields=['balance'])
        else:
            messages.error(request, 'المبلغ المدخل غير صحيح.')
    return redirect('customers_page')


# ============================================================
# التقارير والتحليلات (Reports)
# ============================================================

def _parse_report_range(request):
    today = timezone.localdate()
    default_start = today - datetime.timedelta(days=30)
    try:
        start = datetime.date.fromisoformat(request.GET.get('start', ''))
    except (ValueError, TypeError):
        start = default_start
    try:
        end = datetime.date.fromisoformat(request.GET.get('end', ''))
    except (ValueError, TypeError):
        end = today
    return start, end


@login_required
def reports_page(request):
    start, end = _parse_report_range(request)

    sales = (
        Sale.objects.filter(created_at__date__range=(start, end))
        .select_related('account').prefetch_related('items__product')
        .order_by('-created_at')
    )
    purchases = (
        Purchase.objects.filter(received_at__date__range=(start, end))
        .select_related('product', 'supplier')
        .order_by('-received_at')
    )

    total_sales = sum((s.total for s in sales), Decimal('0'))
    total_purchases = sum((p.total_cost for p in purchases), Decimal('0'))

    context = {
        'start': start, 'end': end,
        'sales': sales, 'purchases': purchases,
        'total_sales': total_sales, 'total_purchases': total_purchases,
    }
    return render(request, 'dashboard/reports.html', context)


@login_required
def export_sales_csv(request):
    start, end = _parse_report_range(request)
    sales = (
        Sale.objects.filter(created_at__date__range=(start, end))
        .select_related('account').prefetch_related('items__product')
        .order_by('-created_at')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sales_{start}_{end}.csv"'
    response.write('\ufeff')  # BOM لضمان عرض صحيح للعربية في Excel
    writer = csv.writer(response)
    writer.writerow(['رقم الفاتورة', 'التاريخ', 'العميل/الوكيل', 'الصنف', 'الكمية', 'الإجمالي', 'طريقة الدفع'])
    for sale in sales:
        for item in sale.items.all():
            writer.writerow([
                sale.invoice_no,
                sale.created_at.strftime('%Y-%m-%d %H:%M'),
                sale.account.name if sale.account else 'عميل نقدي',
                item.product.code,
                item.quantity,
                item.subtotal,
                sale.get_payment_method_display(),
            ])
    return response
from django.contrib.auth import logout 
def custom_logout(request):
    logout(request)
    return redirect('login')