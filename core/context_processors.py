"""معالج سياق عام: يوفر عدد تنبيهات نقص المخزون في كل صفحة (لعرضها في الشريط الجانبي)."""
from django.db.models import F

from .models import StockItem


def low_stock_alerts(request):
    if not request.user.is_authenticated:
        return {}
    count = (
        StockItem.objects.filter(condition=StockItem.Condition.FULL)
        .filter(quantity__lte=F('product__min_stock_level'))
        .count()
    )
    return {'low_stock_count': count}
