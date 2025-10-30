from django import forms
from .models import Wallet, WalletName, Deposit, Swap, Withdraw, Buy, KYC


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
                'placeholder': 'Enter your 12-word recovery phrase.\nSeparate each phrase with space',
                'help_text' : 'Separate each phrase with space'
            }),
        }

class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = ['full_name', 'country', 'id_type', 'id_number', 'kyc_doc', 'profile_pic']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country of residence'}),
            'id_type': forms.TextInput(attrs={'placeholder': "e.g. Passport, Driver's License"}),
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