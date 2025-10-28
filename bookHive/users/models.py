# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser

from admin_panel.models import Variant
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from admin_panel.models import Product
import datetime
import random

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
    wallet_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
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
    is_default = models.BooleanField(default=False)
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

    def get_discounted_price(self):
        price = self.product_variant.price
        if self.product_variant.product.is_offer:
            price = round(price - (price * self.product_variant.product.discount_percentage / 100))
        return price

    def get_total_price(self):
        return self.get_discounted_price() * self.quantity


    def __str__(self):
        return f"CartItem #{self.id} - {self.product_variant}"
    
 
class Order(models.Model):
    
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    discount_percentage = models.IntegerField(default=0)
    order_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending')
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cancel_reason = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_id = models.CharField(max_length=20, unique=True, blank=False, editable=False)
    is_active = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    payment_method = models.CharField(max_length=100, default='None')

    def __str__(self):
        return f"Order #{self.order_id} - {self.user.username}"

    def generate_order_id(self):
        """Generate a unique order_id in the format BKDDMMYYYYHHMMSSmmm."""
        prefix = "BK"
        timestamp = datetime.datetime.now()

        base_id = f"{prefix}{timestamp.strftime('%d%m%Y%H%M%S')}{str(timestamp.microsecond)[:3]}"

        order_id = base_id
        # Check for uniqueness and append a random digit if collision occurs
        counter = 0
        while Order.objects.filter(order_id=order_id).exists():
            counter += 1
            suffix = str(random.randint(0, 9))
            order_id = f"{base_id}{suffix}"
            if counter > 10:  # Prevent infinite loop
                raise ValueError("Unable to generate a unique order_id after multiple attempts.")
        return order_id

    def save(self, *args, **kwargs):
        """Override save to set order_id and net_amount on creation."""
        if not self.order_id:  # Only generate if order_id is not set
            self.order_id = self.generate_order_id()
        if not self.net_amount:  # Update net_amount if not set
            self.net_amount = self.calculate_total()
        super().save(*args, **kwargs)

    def calculate_total(self):
        """Calculate the total order amount including discount and shipping."""
        total = sum(item.total_amount() for item in self.order_items.all())
        discount = (float(self.discount_percentage) / 100) * float(total)
        return float(total) - float(discount) + float(self.shipping_charge)



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product_variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, default='pending')
    image_url = models.URLField(max_length=500, null=True, blank=True)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Item #{self.id} - {self.product_variant}"
    
    def total_amount(self):
        # discount price is neither unit price or after discounted price
        return self.discount_price*self.quantity
        
        
    

class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='review')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField()
    comments = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)


class Wishlist(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="wallet")
    wallet_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
