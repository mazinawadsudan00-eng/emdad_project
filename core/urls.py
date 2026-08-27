from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('logout/',views.custom_logout, name= 'logout'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add-stock/', views.add_stock, name='add_stock'),
    path('inventory/<int:pk>/edit/', views.edit_stock_item, name='edit_stock_item'),
    path('inventory/<int:pk>/delete/', views.delete_stock_item, name='delete_stock_item'),
    path('inventory/<int:pk>/maintenance/', views.send_to_maintenance, name='send_to_maintenance'),

    path('sales/', views.sales_page, name='sales_page'),

    path('customers/', views.customers_page, name='customers_page'),
    path('customers/<int:pk>/settle/', views.settle_account, name='settle_account'),

    path('reports/', views.reports_page, name='reports_page'),
    path('reports/export/', views.export_sales_csv, name='export_sales_csv'),
]
