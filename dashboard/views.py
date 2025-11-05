# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
import uuid

from .models import UserProfile, Wallet, Deposit, Buy, Withdraw, Swap, KYC
from .forms import WalletForm, DepositForm, BuyForm, WithdrawForm, SwapForm, KYCForm



@login_required
def dashboard_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    wallets = Wallet.objects.filter(user=request.user)
    return render(request, 'dashboard/index.html', {
        'profile': profile,
        'wallets': wallets,
    })


@login_required
def link_wallet_view(request):
    if request.method == 'POST':
        form = WalletForm(request.POST)
        if form.is_valid():
            wallet = form.save(commit=False)
            wallet.user = request.user
            wallet.save()
            messages.success(request, f"{wallet.wallet_name} linked successfully.")
            return redirect('dashboard:dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = WalletForm()

    return render(request, 'dashboard/link_wallet.html', {'form': form})


@login_required
def transactions_view(request):
    transactions = []  # Replace with actual queryset later
    return render(request, 'dashboard/transactions.html', {'transactions': transactions})


@login_required
def investments_view(request):
    investments = []  # Replace with actual queryset later
    return render(request, 'dashboard/investments.html', {'investments': investments})

@login_required
def kyc_view(request):
    profile = request.user.profile
    kyc_instance = getattr(request.user, 'kyc', None)

    if request.method == 'POST':
        form = KYCForm(request.POST, request.FILES, instance=kyc_instance)
        if form.is_valid():
            kyc = form.save(commit=False)
            kyc.user = request.user
            kyc.status = 'pending'  # set to pending after submission
            kyc.save()
            profile.kyc_verified = False
            profile.save()
            messages.success(request, "✅ KYC submitted successfully! Status: Pending Verification.")
            return redirect('dashboard:kyc')
        else:
            messages.error(request, "⚠ Please correct the errors below.")
    else:
        form = KYCForm(instance=kyc_instance)

    return render(request, 'dashboard/kyc.html', {'form': form, 'profile': profile, 'kyc': kyc_instance})


@login_required
@transaction.atomic
def deposit_view(request):
    profile = UserProfile.objects.select_for_update().get(user=request.user)
    if request.method == "POST":
        form = DepositForm(request.POST)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.user = request.user
            deposit.reference = str(uuid.uuid4())[:12]
            deposit.status = "successful"  # for now simulate success
            deposit.save()

            # Update wallet balance
            profile.total_balance += deposit.amount
            profile.save()

            messages.success(request, f"Deposit of ${deposit.amount} was successful!")
            return redirect("dashboard:index")
        else:
            messages.error(request, "Invalid deposit amount.")
    else:
        form = DepositForm()

    return render(request, "dashboard/deposit.html", {"form": form, "profile": profile})


@login_required
@transaction.atomic
def buy_view(request):
    profile = UserProfile.objects.select_for_update().get(user=request.user)
    if request.method == "POST":
        form = BuyForm(request.POST)
        if form.is_valid():
            buy = form.save(commit=False)
            buy.user = request.user
            buy.reference = str(uuid.uuid4())[:12]
            buy.status = "successful"
            buy.save()

            # Deduct from balance
            if profile.total_balance >= buy.amount:
                profile.total_balance -= buy.amount
                profile.save()
                messages.success(request, f"Purchase of {buy.item_name} for ${buy.amount} successful!")
            else:
                messages.error(request, "Insufficient balance.")
            return redirect("dashboard:dashboard")
    else:
        form = BuyForm()
    return render(request, "dashboard/buy.html", {"form": form, "profile": profile})


@login_required
@transaction.atomic
def withdraw_view(request):
    profile = UserProfile.objects.select_for_update().get(user=request.user)
    if request.method == "POST":
        form = WithdrawForm(request.POST)
        if form.is_valid():
            withdraw = form.save(commit=False)
            withdraw.user = request.user
            withdraw.reference = str(uuid.uuid4())[:12]
            if profile.total_balance >= withdraw.amount:
                withdraw.status = "successful"
                withdraw.save()
                profile.total_balance -= withdraw.amount
                profile.save()
                messages.success(request, f"Withdrawal of ${withdraw.amount} successful!")
            else:
                messages.error(request, "Insufficient balance.")
            return redirect("dashboard:dashboard")
    else:
        form = WithdrawForm()
    return render(request, "dashboard/withdraw.html", {"form": form, "profile": profile})


@login_required
def swap_view(request):
    profile = UserProfile.objects.get(user=request.user)
    if request.method == "POST":
        form = SwapForm(request.POST)
        if form.is_valid():
            swap = form.save(commit=False)
            swap.user = request.user
            swap.reference = str(uuid.uuid4())[:12]
            swap.status = "successful"
            swap.save()
            messages.success(request, f"Swapped {swap.amount} {swap.from_asset} → {swap.to_asset} successfully!")
            return redirect("dashboard:dashboard")
    else:
        form = SwapForm()
    return render(request, "dashboard/swap.html", {"form": form, "profile": profile})