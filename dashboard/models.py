from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from django.conf import settings
import uuid
from django.contrib.auth.hashers import make_password, check_password
import random
from django.utils import timezone

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


# =============================================================
# QFS Card Models (Final Best-Practice Version)
# =============================================================

CARD_STATUS = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]


def luhn_checksum(card_number: str) -> bool:
    digits = [int(d) for d in card_number if d.isdigit()]
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        d = digit
        if i % 2 == parity:
            d = d * 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def generate_luhn_number(prefix="4567", length=16):
    number = prefix
    while len(number) < (length - 1):
        number += str(random.randint(0, 9))

    for check in range(10):
        candidate = number + str(check)
        if luhn_checksum(candidate):
            return candidate
    return number + "0"


def generate_cvv():
    return f"{random.randint(0, 999):03d}"


class CardRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    name_on_card = models.CharField(max_length=100)
    requested_at = models.DateTimeField(auto_now_add=True)
    pin_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=CARD_STATUS, default="pending")
    admin_message = models.TextField(blank=True, null=True)

    def set_pin(self, pin_plain: str):
        self.pin_hash = make_password(pin_plain)

    def check_pin(self, pin_plain: str) -> bool:
        return check_password(pin_plain, self.pin_hash)

    def __str__(self):
        return f"CardRequest({self.user.username} - {self.status})"


class Card(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name_on_card = models.CharField(max_length=100)
    masked_pan = models.CharField(max_length=32)
    last4 = models.CharField(max_length=4)
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    card_token = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    @property
    def display_expiry(self):
        return f"{self.expiry_month:02d}/{str(self.expiry_year)[-2:]}"

    @staticmethod
    def issue_card_for_request(card_request: CardRequest):
        if Card.objects.filter(user=card_request.user).exists():
            raise ValueError("User already has a card issued")

        pan = generate_luhn_number()
        cvv = generate_cvv()
        expiry_year = timezone.now().year + 3
        expiry_month = random.randint(1, 12)
        last4 = pan[-4:]
        masked = "#### #### #### " + last4

        token = uuid.uuid4().hex

        card = Card.objects.create(
            user=card_request.user,
            name_on_card=card_request.name_on_card,
            masked_pan=masked,
            last4=last4,
            expiry_month=expiry_month,
            expiry_year=expiry_year,
            card_token=token,
            active=True,
        )

        card_request.status = "approved"
        card_request.save(update_fields=["status"])
        return card, cvv
