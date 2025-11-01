from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth import get_user_model
from .models import Wallet

User = get_user_model()

class MyCustomSignupForm(SignupForm):
    phone_no = forms.CharField(
        max_length=15, required=False, label="Phone Number"
    )

    def save(self, request):
        user = super().save(request)
        user.phone_no = self.cleaned_data.get("phone_no")  # Use .get() to handle optional field
        user.save()
        
        # Create wallet for the new user
        Wallet.objects.get_or_create(user=user, defaults={'wallet_amount': 0})
        
        return user