# dashboard/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from .models import Deposit, Withdraw, UserProfile

@receiver(post_save, sender=Deposit)
@receiver(post_save, sender=Withdraw)
def recalc_user_balance(sender, instance, created, **kwargs):
    """
    Recalculate user's balance when Deposit or Withdraw changes.
    Note: only successful deposits and successful withdrawals count.
    """
    user = instance.user
    # sum successful deposits
    deposits_total = Deposit.objects.filter(user=user, status__in=['successful']).aggregate(total=models.Sum('amount'))['total'] or 0
    # sum successful withdrawals that have been applied (or successful)
    withdrawals_total = Withdraw.objects.filter(user=user, status__in=['successful']).aggregate(total=models.Sum('amount'))['total'] or 0

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.total_balance = deposits_total - withdrawals_total
    profile.save(update_fields=['total_balance'])


# @receiver(post_save, sender=Deposit)
# def update_balance_on_deposit(sender, instance, created, **kwargs):
#     """When admin approves deposit, update user's balance."""
#     if instance.status == 'approved':
#         profile, _ = UserProfile.objects.get_or_create(user=instance.user)
#         # Ensure balance matches total of approved deposits minus withdrawals
#         deposits = Deposit.objects.filter(user=instance.user, status='approved').aggregate(total=models.Sum('amount'))['total'] or 0
#         withdrawals = Withdraw.objects.filter(user=instance.user, status='successful').aggregate(total=models.Sum('amount'))['total'] or 0
#         profile.total_balance = deposits - withdrawals
#         profile.save()


# @receiver(post_save, sender=Withdraw)
# def update_balance_on_withdraw(sender, instance, created, **kwargs):
#     """When admin approves withdraw, update user's balance."""
#     if instance.status == 'successful':
#         profile, _ = UserProfile.objects.get_or_create(user=instance.user)
#         deposits = Deposit.objects.filter(user=instance.user, status='approved').aggregate(total=models.Sum('amount'))['total'] or 0
#         withdrawals = Withdraw.objects.filter(user=instance.user, status='successful').aggregate(total=models.Sum('amount'))['total'] or 0
#         profile.total_balance = deposits - withdrawals
#         profile.save()