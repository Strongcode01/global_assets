from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('link-wallet/', views.link_wallet_view, name='link_wallet'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('investments/', views.investments_view, name='investments'),
    path('kyc/', views.kyc_view, name='kyc'),
    path('kyc/view/', views.kyc_view_info, name='kyc_view_info'),
    path("buy/", views.buy_view, name="buy"),
    path("deposit/", views.deposit_view, name="deposit"),
    path("withdraw/", views.withdraw_view, name="withdraw"),
    path("swap/", views.swap_view, name="swap"),
    path('get-balance/', views.get_balance, name='get_balance'), 
]
