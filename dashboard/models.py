from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F

User = get_user_model()


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


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    total_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    kyc_verified = models.BooleanField(default=False)
    country = models.CharField(max_length=100, blank=True, null=True)
    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name_plural = "profiles"

    def __str__(self):
        return (self.user.username)+"'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# models.py (only the KYC model portion)
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
        # Save object first
        super().save(*args, **kwargs)
        # Sync profile
        from .models import UserProfile  # avoid circular import at top if necessary
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.kyc_verified = (self.status == 'verified')
        profile.save()

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"

# ===================================================================================================================================
# ===================================================================================================================================

User = get_user_model()

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
    # `applied` ensures the amount is only added once to the profile/balance
    applied = models.BooleanField(default=False)

    def __str__(self):
        return f"Deposit {self.amount} by {self.user.username}"

    def save(self, *args, **kwargs):
        # auto-generate a short unique reference if missing
        if not self.reference:
            self.reference = uuid.uuid4().hex[:12]
            # ensure uniqueness loop (very unlikely collision)
            while Deposit.objects.filter(reference=self.reference).exists():
                self.reference = uuid.uuid4().hex[:12]
        super().save(*args, **kwargs)


# Post-save signal:
@receiver(post_save, sender=Deposit)
def apply_deposit_balance(sender, instance: Deposit, created, **kwargs):
    """
    When a Deposit becomes 'successful' and hasn't been applied yet,
    atomically increment the user's profile.total_balance and mark deposit.applied=True.
    This handler is idempotent: runs safely if admin updates the same record multiple times.
    """
    # quick-out: only proceed if status is successful and not already applied
    if instance.status != 'successful' or instance.applied:
        return

    # update using F-expression to avoid race conditions
    from .models import UserProfile  # local import to avoid circulars if any
    # Use a transaction to keep operations safe
    with transaction.atomic():
        # increment the profile's balance
        # use select_for_update to avoid lost updates in concurrent approval
        try:
            profile = UserProfile.objects.select_for_update().get(user=instance.user)
        except UserProfile.DoesNotExist:
            # if profile missing, create it and then apply
            profile = UserProfile.objects.create(user=instance.user, total_balance=0)
        # Use F() to increment safely
        profile.total_balance = F('total_balance') + instance.amount
        profile.save()

        # mark deposit as applied so we don't double-credit
        # Use update() to avoid re-triggering this signal recursively
        Deposit.objects.filter(pk=instance.pk, applied=False).update(applied=True)


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


class Withdraw(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    account_number = models.CharField(max_length=30)
    bank_name = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed')],
        default='pending'
    )
    reference = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Withdraw {self.amount} by {self.user.username}"
    

@transaction.atomic
class Withdraw(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    account_number = models.CharField(max_length=30)
    bank_name = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed')],
        default='pending'
    )
    reference = models.CharField(max_length=100, unique=True)
    # ensure we only deduct once
    applied = models.BooleanField(default=False)

    def __str__(self):
        return f"Withdraw {self.amount} by {self.user.username}"

    def save(self, *args, **kwargs):
        # Generate reference if not set
        if not self.reference:
            self.reference = uuid.uuid4().hex[:12]
            while Withdraw.objects.filter(reference=self.reference).exists():
                self.reference = uuid.uuid4().hex[:12]

        # Save the withdraw object first
        super().save(*args, **kwargs)

        # Automatically update balance if withdrawal is approved/successful and not already applied
        if self.status in ['successful', 'approved'] and not self.applied:
            from dashboard.models import Profile  # Import Profile model here

            profile = Profile.objects.filter(user=self.user).first()
            if profile:
                profile.total_balance -= self.amount
                profile.save()
                self.applied = True
                # Save again to mark applied without recursion issues
                super().save(update_fields=['applied'])

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