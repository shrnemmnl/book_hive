# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from admin_panel.models import Variant
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from admin_panel.models import Product
# import uuid
# import random
# import string



class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # Make email unique
    phone_no = models.BigIntegerField(unique=True, null=True, blank=True)  
    is_verified = models.BooleanField(default=False)
    profile_pic = models.ImageField(
        upload_to='profile_pics/',  # where it stores in media/
        default='profile_pics/default.jpg',  # this should exist in your media folder!
        null=True,
        blank=True
    )
    username = None  # Remove username field
    USERNAME_FIELD = 'email'  # Set email as the username field
    REQUIRED_FIELDS = []

    objects = CustomUserManager()  # Use custom manager

    def __str__(self):
        return self.email 
    
class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    address_type=models.CharField(max_length=100)
    street = models.CharField(max_length=255)  
    city = models.CharField(max_length=100)  
    landmark=models.CharField(max_length=100)
    state = models.CharField(max_length=100) 
    postal_code = models.CharField(max_length=10) 
    phone = models.CharField(max_length=15)  
    is_active=models.BooleanField(default=True)

    
    def __str__(self):
        return f"{self.address_type}, {self.city}"

class Cart(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"

    def total_price(self):
        return sum(item.get_total_price() for item in self.cart_items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product_variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    def get_total_price(self):
        return self.quantity * self.product_variant.price


    def __str__(self):
        return f"CartItem #{self.id} - {self.product_variant}"
    
 
class Order(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='orders')
    # payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    discount_percentage = models.IntegerField(default=0)
    order_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending')
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def calculate_total(self):
        total = sum(item.total_amount for item in self.order_items.all())
        discount = (self.discount_percentage / 100) * total
        return total - discount + self.shipping_charge



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product_variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='pending')
    image_url = models.URLField(max_length=500, null=True, blank=True)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if self.product_variant:
            self.total_amount = self.quantity * self.product_variant.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Item #{self.id} - {self.product_variant}"
    

class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='review')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField()
    comments = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)