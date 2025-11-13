from django.utils import timezone
from django.contrib import admin
from .models import Wallet, UserProfile, WalletName, Deposit, KYC, Withdraw
from django.db import transaction
from django.db.models import F
from django.contrib import messages


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
    list_display = ('user', 'amount', 'status', 'date', 'reference', 'applied')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'reference')
    actions = ['approve_deposits', 'mark_failed']

    @admin.action(description="Mark selected deposits as successful (approve)")
    def approve_deposits(self, request, queryset):
        approved = 0
        with transaction.atomic():
            # process one-by-one to ensure profile locking per user
            for deposit in queryset.select_for_update():
                if deposit.status == 'successful' and deposit.applied:
                    # already applied, skip
                    continue
                if deposit.status != 'successful':
                    deposit.status = 'successful'
                # Save deposit first so post_save signal will run and apply to profile
                deposit.save()
                # after save, the post_save handler will apply the deposit (if not applied)
                approved += 1
        self.message_user(request, f"{approved} deposit(s) marked successful and applied to user balances.")

    @admin.action(description="Mark selected deposits as failed")
    def mark_failed(self, request, queryset):
        failed = queryset.exclude(status='failed').update(status='failed')
        # do not subtract applied amounts — we assume only pending deposits should be marked failed
        self.message_user(request, f"{failed} deposit(s) marked failed.")


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


@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'date', 'reference')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'reference')
    actions = ['approve_withdrawals', 'mark_failed']

    @admin.action(description="Approve selected withdrawals (mark as successful and apply)")
    def approve_withdrawals(self, request, queryset):
        applied_count = 0
        failed_count = 0

        with transaction.atomic():
            for withdraw in queryset.select_for_update():
                if withdraw.status == 'successful':
                    continue

                profile = UserProfile.objects.select_for_update().filter(user=withdraw.user).first()
                if not profile:
                    withdraw.status = 'failed'
                    withdraw.save(update_fields=['status'])
                    failed_count += 1
                    continue

                if profile.total_balance < withdraw.amount:
                    withdraw.status = 'failed'
                    withdraw.save(update_fields=['status'])
                    failed_count += 1
                    continue

                withdraw.status = 'successful'
                withdraw.save()  # triggers balance deduction
                applied_count += 1

        self.message_user(
            request,
            f"{applied_count} withdrawal(s) approved; {failed_count} failed due to insufficient funds.",
            level=messages.INFO
        )

    @admin.action(description="Mark selected withdrawals as failed")
    def mark_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f"{updated} withdrawal(s) marked as failed.", level=messages.WARNING)