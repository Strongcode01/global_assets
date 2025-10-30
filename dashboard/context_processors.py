from .models import UserProfile, KYC

def user_profile_context(request):
    """Provide user profile and KYC globally to all templates."""
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        kyc = None
        try:
            kyc = KYC.objects.get(user=request.user)
        except KYC.DoesNotExist:
            pass
        return {'profile': profile, 'kyc': kyc}
    return {}
