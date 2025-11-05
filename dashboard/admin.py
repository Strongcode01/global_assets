from django.utils import timezone
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



@admin.action(description="Mark selected KYC as Verified ✅")
def mark_as_verified(modeladmin, request, queryset):
    now = timezone.now()
    count = queryset.update(status='verified', verified_at=now)
    for kyc in queryset:
        # Sync user profile
        profile, _ = UserProfile.objects.get_or_create(user=kyc.user)
        profile.kyc_verified = True
        profile.save()
    modeladmin.message_user(request, f"{count} KYC record(s) marked as verified successfully.")

@admin.action(description="Mark selected KYC as Pending ⏳")
def mark_as_pending(modeladmin, request, queryset):
    count = queryset.update(status='pending')
    for kyc in queryset:
        profile, _ = UserProfile.objects.get_or_create(user=kyc.user)
        profile.kyc_verified = False
        profile.save()
    modeladmin.message_user(request, f"{count} KYC record(s) set back to pending.")

@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'country', 'status', 'submitted_at')
    list_filter = ('status', 'country')
    search_fields = ('user__username', 'full_name', 'id_number')
    actions = [mark_as_verified, mark_as_pending]
