from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver

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
class Deposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed')],
        default='pending'
    )
    reference = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Deposit {self.amount} by {self.user.username}"

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