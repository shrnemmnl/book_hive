from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

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
