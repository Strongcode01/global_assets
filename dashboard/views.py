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
    # Ensure profile exists and avoid attribute errors
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Try to get existing KYC instance, None if not exists
    try:
        kyc_instance = request.user.kyc
    except KYC.DoesNotExist:
        kyc_instance = None

    # Determine whether user requested to edit
    want_edit = request.GET.get('edit') in ['1', 'true', 'True']  # e.g. ?edit=1

    # If KYC exists and is verified, disallow editing
    if kyc_instance and kyc_instance.status == 'verified':
        want_edit = False  # force view-only for verified KYC

    if request.method == 'POST':
        # If verified, prevent any updates
        if kyc_instance and kyc_instance.status == 'verified':
            messages.error(request, "Your KYC is already verified and cannot be edited.")
            return redirect('dashboard:kyc')

        # Bind form to instance if exists so we update instead of create duplicate
        form = KYCForm(request.POST, request.FILES, instance=kyc_instance)
        if form.is_valid():
            try:
                kyc = form.save(commit=False)
                kyc.user = request.user
                # When user submits or updates, mark as pending
                kyc.status = 'pending'
                kyc.save()
                # ensure profile reflects pending (unverified)
                profile.kyc_verified = False
                profile.save()

                messages.success(request, "✅ KYC submitted successfully. Status: Pending. The admin will review it.")
                return redirect('dashboard:kyc')
            except Exception as exc:
                # Log error server-side; show user-friendly message
                import logging
                logger = logging.getLogger(__name__)
                logger.exception("KYC save failed for user %s: %s", request.user.username, exc)
                messages.error(request, "An unexpected error occurred while submitting your KYC. Please try again.")
        else:
            messages.error(request, "Please correct the highlighted fields below.")
    else:
        # GET request: show form only if user asked to edit or no kyc exists yet
        if want_edit or not kyc_instance:
            form = KYCForm(instance=kyc_instance)
        else:
            form = None  # render the status-card, not the form

    # Render page with profile, kyc instance (if any), and the form (or None)
    return render(request, 'dashboard/kyc.html', {
        'profile': profile,
        'kyc': kyc_instance,
        'form': form,
    })

@login_required
def kyc_view_info(request):
    # View-only page to display full KYC details (for verified KYC)
    try:
        kyc = request.user.kyc
    except KYC.DoesNotExist:
        messages.info(request, "No KYC found.")
        return redirect('dashboard:kyc')

    return render(request, 'dashboard/kyc_view_info.html', {'kyc': kyc})

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