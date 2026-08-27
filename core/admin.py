from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Account, Product, Purchase, Sale, SaleItem, StockItem, StockMovement, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """إدارة المستخدمين وصلاحياتهم (متطلب 'إدارة صلاحيات المستخدمين' - للمدير فقط)."""
    fieldsets = BaseUserAdmin.fieldsets + (
        ('صلاحية النظام', {'fields': ('role', 'phone')}),
    )
    list_display = ('username', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'phone', 'region', 'balance', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('name', 'phone', 'region')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'size_kg', 'unit_price', 'min_stock_level', 'is_sellable', 'is_active')
    list_filter = ('category', 'is_sellable', 'is_active')
    search_fields = ('code', 'name')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'account', 'payment_method', 'created_by', 'created_at', 'total')
    list_filter = ('payment_method',)
    inlines = [SaleItemInline]
    readonly_fields = ()


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'condition', 'quantity', 'location', 'updated_at')
    list_filter = ('condition',)
    search_fields = ('product__code', 'product__name')


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'quantity', 'unit_cost', 'condition', 'received_at', 'received_by')
    list_filter = ('condition',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('movement_type', 'product', 'quantity', 'related_account', 'created_by', 'created_at')
    list_filter = ('movement_type',)
