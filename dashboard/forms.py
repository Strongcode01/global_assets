from django import forms
from .models import Card, Wallet, WalletName, Deposit, Swap, Withdraw, Buy, KYC, CardRequest
import re
from django.core.exceptions import ValidationError


class WalletForm(forms.ModelForm):
    wallet_name = forms.ModelChoiceField(
        queryset=WalletName.objects.all(),
        empty_label="Select Wallet",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Wallet
        fields = ['wallet_name', 'wallet_phrase']
        widgets = {
            'wallet_phrase': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your 12-word recovery phrase. Separate words with spaces.',
                'rows': 5,
                'aria-label': 'Wallet recovery phrase'
            }),
        }

    def clean_wallet_phrase(self):
        phrase = self.cleaned_data.get('wallet_phrase', '') or ''
        # Normalize whitespace, remove extra spaces/newlines
        tokens = [w for w in re.split(r'\s+', phrase.strip()) if w]
        if len(tokens) != 12:
            raise ValidationError("Recovery phrase must be exactly 12 words (found %d)." % len(tokens))
        # Normalize for storage/comparison: lower-case and single spaced
        normalized = ' '.join(tokens).lower()
        return normalized

    def clean(self):
        cleaned = super().clean()
        wallet_name = cleaned.get('wallet_name')
        phrase = cleaned.get('wallet_phrase')  # already normalized by clean_wallet_phrase if present

        # Only run duplicate check if we have both fields and no prior errors
        if wallet_name and phrase and not self.errors:
            # If form is used to update an existing Wallet instance, skip checking itself:
            qs = Wallet.objects.filter(wallet_name=wallet_name, wallet_phrase=phrase)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                # Attach error to the field so it appears under phrase
                self.add_error('wallet_phrase', ValidationError(
                    "This recovery phrase is already linked to the selected wallet."
                ))
        return cleaned

class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = ['full_name', 'country', 'id_type', 'id_number', 'kyc_doc', 'profile_pic']
        labels = {
            'id_type': 'Valid ID Type',
            'id_number': 'ID Number',
            'kyc_doc': 'Upload ID Document',
            'profile_pic': 'Upload Profile Picture',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country of residence'}),
            'id_type': forms.TextInput(attrs={'placeholder': "e.g. Passport, Driver's License", 'label':'Valid ID'}),
            'id_number': forms.TextInput(attrs={'placeholder': 'ID Number'}), 
             
        }
        

class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount to deposit'
            })
        }

class BuyForm(forms.ModelForm):
    class Meta:
        model = Buy
        fields = ['item_name', 'amount']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item name'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount'}),
        }


class WithdrawForm(forms.ModelForm):
    class Meta:
        model = Withdraw
        fields = ['amount', 'account_number', 'bank_name']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount to withdraw'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account Number'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank Name'}),
        }


class SwapForm(forms.ModelForm):
    class Meta:
        model = Swap
        fields = ['from_asset', 'to_asset', 'amount']
        widgets = {
            'from_asset': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'From'}),
            'to_asset': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'To'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount'}),
        }

# forms.py
from django import forms
from .models import CardRequest


class CardPreOrderForm(forms.ModelForm):
    # extra field (not stored directly on model)
    pin = forms.CharField(
        max_length=4,
        widget=forms.PasswordInput(attrs={"placeholder": "1234"}),
        label="Transaction PIN"
    )

    class Meta:
        model = CardRequest
        # only include model fields here — 'pin' is defined above as an extra form field
        fields = ["name_on_card"]

    def clean_pin(self):
        pin = self.cleaned_data.get("pin", "")
        if not pin.isdigit() or len(pin) != 4:
            raise forms.ValidationError("PIN must be 4 numeric digits.")
        return pin
