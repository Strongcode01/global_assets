from django.contrib import admin
from .models import Wallet, UserProfile, WalletName, Deposit, KYC


@admin.register(WalletName)
class WalletNameAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('wallet_name', 'user', 'created_at')
    list_filter = ('wallet_name', 'created_at')
    search_fields = ('wallet_name__name', 'user__username')
    ordering = ('-created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_balance', 'kyc_verified', 'country')
    list_filter = ('kyc_verified', 'country')
    search_fields = ('user__username',)
    ordering = ('user',)

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'date', 'reference')


@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'full_name', 'country')