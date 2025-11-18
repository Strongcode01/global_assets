# views.py
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
import uuid
from .models import Card, User, UserProfile, Wallet, Deposit, Buy, Withdraw, Swap, KYC, CardRequest
from .forms import CardPreOrderForm, WalletForm, DepositForm, BuyForm, WithdrawForm, SwapForm, KYCForm
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from itertools import chain
from django.db.models import Value, CharField
import re


@login_required
def dashboard_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    wallets = Wallet.objects.filter(user=request.user)

    deposits = Deposit.objects.filter(user=request.user).annotate(
        type=Value('Deposit', output_field=CharField())
    )
    withdrawals = Withdraw.objects.filter(user=request.user).annotate(
        type=Value('Withdrawal', output_field=CharField())
    )

    # Combine and sort
    transactions = sorted(
        chain(deposits, withdrawals),
        key=lambda x: x.date,
        reverse=True
    )

    context = {
        'profile': profile,
        'wallets': wallets,
        'transactions': transactions[:10],
        "tg_username": settings.TG_USERNAME
    }
    return render(request, 'dashboard/index.html', context)

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

                # Only set to pending if it's a new submission or unverified
                if not kyc_instance or kyc_instance.status != 'verified':
                    kyc.status = 'pending'
                    profile.kyc_verified = False
                else:
                    # If it's already verified, keep status and profile untouched
                    kyc.status = kyc_instance.status

                kyc.save()
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
def deposit_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = DepositForm(request.POST)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.user = request.user
            deposit.status = "pending"  # admin must approve
            deposit.save()
            messages.success(request, "✅ Deposit recorded — awaiting admin approval.")
            # return fresh balance (unchanged until admin approves)
            profile.refresh_from_db()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'balance': float(profile.total_balance)})
            return redirect("dashboard:dashboard")
        else:
            messages.error(request, "Please enter a valid deposit amount.")
    else:
        form = DepositForm()
    return render(request, "dashboard/deposit.html", {"form": form, "profile": profile})


@login_required
def withdraw_view(request):
    """
    Create a withdrawal request in 'pending' state. Admin must approve to actually deduct.
    This prevents users from deducting their own balance while admin is the actor.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = WithdrawForm(request.POST)
        if form.is_valid():
            withdraw = form.save(commit=False)
            withdraw.user = request.user
            withdraw.status = "pending"  # admin will approve
            withdraw.save()
            messages.success(request, "Withdrawal request submitted — awaiting admin approval.")
            # return current balance (unchanged until admin approves)
            profile.refresh_from_db()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'balance': float(profile.total_balance)})
            return redirect("dashboard:dashboard")
        else:
            messages.error(request, "Please correct the errors.")
    else:
        form = WithdrawForm()
    return render(request, "dashboard/withdraw.html", {"form": form, "profile": profile})
   

@login_required
def get_balance(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    # ensure fresh value after any F() updates
    profile.refresh_from_db()
    kyc_status = getattr(getattr(request.user, 'kyc', None), 'status', 'Pending')
    return JsonResponse({
        'balance': float(profile.total_balance),
        'kyc_status': kyc_status.capitalize(),
    })

@login_required
def transactions_view(request):
    deposits = Deposit.objects.filter(user=request.user).values(
        'amount', 'status', 'date', 'reference'
    )
    transactions = [
        {'type': 'deposit', **txn} for txn in deposits
    ]
    return render(request, 'dashboard/transactions.html', {'transactions': transactions})


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



@receiver(post_save, sender=Withdraw)
def apply_withdraw_balance(sender, instance: Withdraw, created, **kwargs):
    """
    When a Withdraw becomes 'successful' and hasn't been applied yet,
    atomically decrement the user's profile.total_balance and mark withdraw.applied=True.
    If the user does not have enough balance at the moment of approval, mark as failed.
    """
    # Only proceed for successful and not applied withdraws
    if instance.status != 'successful' or instance.applied:
        return

    # Atomic apply to avoid race conditions
    from django.db import transaction
    with transaction.atomic():
        try:
            profile = UserProfile.objects.select_for_update().get(user=instance.user)
        except UserProfile.DoesNotExist:
            # no profile - can't withdraw
            # mark withdraw as failed
            Withdraw.objects.filter(pk=instance.pk).update(status='failed', applied=False)
            return

        # ensure enough balance
        # We read current balance fresh and compare
        profile.refresh_from_db()
        if profile.total_balance < instance.amount:
            # insufficient funds - reverse the approval
            Withdraw.objects.filter(pk=instance.pk).update(status='failed', applied=False)
            return

        # Deduct using F to be safe
        profile.total_balance = F('total_balance') - instance.amount
        profile.save()

        # mark withdraw as applied; use update() to avoid re-triggering handler
        Withdraw.objects.filter(pk=instance.pk, applied=False).update(applied=True)


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


@login_required
def my_card(request):
    # Fetch user's card and card request
    card = Card.objects.filter(user=request.user).first()
    card_request = CardRequest.objects.filter(user=request.user).first()

    # Render Active Card page if card exists
    if card:
        return render(request, "cards/card_active.html", {"card": card})

    # Render Pending Card page if preorder exists
    if card_request:
        return render(request, "cards/card_pending.html", {"card_request": card_request})

    # Render Preorder Card page if no card/request exists
    if request.method == "POST":
        form = CardPreOrderForm(request.POST)
        if form.is_valid():
            card_req = form.save(commit=False)
            card_req.user = request.user
            # `pin` is an extra field on the form — store its hash
            card_req.set_pin(form.cleaned_data["pin"])
            card_req.save()
            messages.success(request, "🎉 Your card preorder has been submitted successfully!")
            return redirect("dashboard:my_card")  # <-- fixed redirect
    else:
        form = CardPreOrderForm()

    return render(request, "cards/card_preorder.html", {"form": form})
