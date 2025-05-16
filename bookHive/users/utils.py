from django.core.mail import send_mail
from django.conf import settings
import random

def generate_otp():
    return str(random.randint(100000, 999999))

def send_verification_email(to_email, otp):
    subject = 'Your Email Verification Code'
    message = f'Hey! Your verification code is: {otp}. Enter this in the verification page to complete signup.'
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [to_email])

def send_verification_email_fg(to_email, otp):
    subject = 'Your Email Verification Code'
    message = f'Hey! Your verification code is: {otp}. Enter this in the verification page to complete Forgot password.'
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [to_email])
