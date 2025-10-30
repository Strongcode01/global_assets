from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, RegisterForm
from django.contrib.auth import authenticate, login as auth_login, logout

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('dashboard:dashboard')  # redirect to dashboard after signup
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'core/page-register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')  # already logged in

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                auth_login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('dashboard:dashboard')
            else:
                messages.error(request, "Invalid username or password.")

            if request.POST.get("remember_me"):
                request.session.set_expiry(1209600)  
            else:
                request.session.set_expiry(0)  

        else:
            messages.error(request, "Invalid login credentials. Please try again.")
    else:
        form = LoginForm()

    return render(request, "core/page-login.html", {"form": form})

def logout_view(request):
    """Logs out the current user and redirects to the home page."""
    logout(request)
    return redirect('core:home')


def home(request):
    return render(request, "core/index.html")

def about(request):
    return render(request, "core/about.html")

def contact(request):
    return render(request, "core/contact.html")

def career(request):
    return render(request, "core/career.html")

def blog(request):
    return render(request, "core/blog-sidebar-right.html")

def blog_detail(request):
    return render(request, "core/blog-details.html")

def mission(request):
    return render(request, "core/page-mission.html")


def wallet(request):
    return render(request, "core/page-wallet.html")


def blank(request):
    return render(request, "core/_blank.html")
