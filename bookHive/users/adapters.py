from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import Wallet

class MyAccountAdapter(DefaultAccountAdapter):
    def get_signup_form_initial_data(self, request):
        """Ensure username is not requested"""
        data = super().get_signup_form_initial_data(request)
        data.pop("username", None)  # Remove username
        return data

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """Ensure username is not assigned"""
        user = super().populate_user(request, sociallogin, data)
        user.username = None  # Remove username assignment
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """Save user and create wallet"""
        user = super().save_user(request, sociallogin, form)
        # Create wallet for the new user
        Wallet.objects.get_or_create(user=user, defaults={'wallet_amount': 0})
        return user
