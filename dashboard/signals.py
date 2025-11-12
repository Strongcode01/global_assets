# dashboard/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Deposit, Withdraw, UserProfile
from dashboard import models

@receiver(post_save, sender=Deposit)
def update_balance_on_deposit(sender, instance, created, **kwargs):
    """When admin approves deposit, update user's balance."""
    if instance.status == 'approved':
        profile, _ = UserProfile.objects.get_or_create(user=instance.user)
        # Ensure balance matches total of approved deposits minus withdrawals
        deposits = Deposit.objects.filter(user=instance.user, status='approved').aggregate(total=models.Sum('amount'))['total'] or 0
        withdrawals = Withdraw.objects.filter(user=instance.user, status='successful').aggregate(total=models.Sum('amount'))['total'] or 0
        profile.total_balance = deposits - withdrawals
        profile.save()


@receiver(post_save, sender=Withdraw)
def update_balance_on_withdraw(sender, instance, created, **kwargs):
    """When admin approves withdraw, update user's balance."""
    if instance.status == 'successful':
        profile, _ = UserProfile.objects.get_or_create(user=instance.user)
        deposits = Deposit.objects.filter(user=instance.user, status='approved').aggregate(total=models.Sum('amount'))['total'] or 0
        withdrawals = Withdraw.objects.filter(user=instance.user, status='successful').aggregate(total=models.Sum('amount'))['total'] or 0
        profile.total_balance = deposits - withdrawals
        profile.save()
