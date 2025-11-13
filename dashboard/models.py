from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from django.conf import settings
from decimal import Decimal
import uuid

User = get_user_model()


# ======================== WALLET MODELS ========================

class WalletName(models.Model):
    """Wallet options created by admin"""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Wallet Names"

    def __str__(self):
        return self.name


class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wallet_name = models.ForeignKey(WalletName, on_delete=models.CASCADE)
    wallet_phrase = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self):
        return reverse('dashboard:link_wallet')

    class Meta:
        verbose_name_plural = "Wallets"

    def __str__(self):
        return f"{self.wallet_name} - {self.user.username}"


# ======================== USER PROFILE ========================

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    total_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    kyc_verified = models.BooleanField(default=False)
    country = models.CharField(max_length=100, blank=True, null=True)
    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Profiles"

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


# ======================== KYC ========================

class KYC(models.Model):
    STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    id_type = models.CharField(max_length=100)
    id_number = models.CharField(max_length=100)
    kyc_doc = models.FileField(upload_to='kyc_docs/', blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unverified')
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.kyc_verified = (self.status == 'verified')
        profile.save()

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"


# ======================== DEPOSIT ========================

class Deposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed')],
        default='pending'
    )
    reference = models.CharField(max_length=100, unique=True, blank=True)
    applied = models.BooleanField(default=False)

    def __str__(self):
        return f"Deposit {self.amount} by {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = uuid.uuid4().hex[:12]
            while Deposit.objects.filter(reference=self.reference).exists():
                self.reference = uuid.uuid4().hex[:12]
        super().save(*args, **kwargs)


@receiver(post_save, sender=Deposit)
def apply_deposit_balance(sender, instance: Deposit, **kwargs):
    """Apply deposit to user balance when successful."""
    if instance.status != 'successful' or instance.applied:
        return

    with transaction.atomic():
        profile, _ = UserProfile.objects.select_for_update().get_or_create(user=instance.user)
        profile.total_balance = F('total_balance') + instance.amount
        profile.save(update_fields=['total_balance'])
        Deposit.objects.filter(pk=instance.pk, applied=False).update(applied=True)


# ======================== BUY ========================

class Buy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed')],
        default='pending'
    )
    reference = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.item_name} bought by {self.user.username}"


# ======================== WITHDRAW ========================

class Withdraw(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    account_number = models.CharField(max_length=30)
    bank_name = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True, blank=True)
    applied = models.BooleanField(default=False)

    def __str__(self):
        return f"Withdraw {self.amount} by {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = uuid.uuid4().hex[:12]
            while Withdraw.objects.filter(reference=self.reference).exists():
                self.reference = uuid.uuid4().hex[:12]

        super().save(*args, **kwargs)

        # Apply deduction only when marked as successful and not already applied
        if self.status == 'successful' and not self.applied:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().filter(user=self.user).first()
                if not profile:
                    self.status = 'failed'
                    super().save(update_fields=['status'])
                    return

                if profile.total_balance >= self.amount:
                    profile.total_balance -= self.amount
                    profile.save(update_fields=['total_balance'])
                    self.applied = True
                    super().save(update_fields=['applied'])
                else:
                    self.status = 'failed'
                    super().save(update_fields=['status'])


# ======================== SWAP ========================

class Swap(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    from_asset = models.CharField(max_length=50)
    to_asset = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=12, decimal_places=4, default=1.0)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed')],
        default='pending'
    )
    reference = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Swap {self.amount} {self.from_asset} to {self.to_asset}"
