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

from .models import KYC

def user_profile_context(request):
    if request.user.is_authenticated:
        try:
            kyc = KYC.objects.filter(user=request.user).first()
        except KYC.DoesNotExist:
            kyc = None
        return {
            "kyc": kyc,
            "kyc_verified": kyc.status == "verified" if kyc else False,
            "profile_pic_url": kyc.profile_pic.url if kyc and kyc.profile_pic else None,
        }
    return {}

