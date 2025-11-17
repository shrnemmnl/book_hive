# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from admin_panel.models import Variant
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from admin_panel.models import Product
import datetime
import random
import string



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
    phone_no = models.CharField(unique=True, null=True, blank=True)  
    is_verified = models.BooleanField(default=False)
    
    # Referral system fields
    referral_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

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

    def generate_referral_code(self):
        """Generate a unique referral code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not CustomUser.objects.filter(referral_code=code).exists():
                return code
    
    def save(self, *args, **kwargs):
        # Generate referral code if it doesn't exist
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)
        
    
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
        return f"Cart #{self.id} - {self.user.email}"

    def total_price(self):
        return sum(item.get_total_price() for item in self.cart_items.all())


class CartItem(models.Model):
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product_variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    def get_discounted_price(self):
        """Get the price with the best available discount (product or genre)"""
        price = self.product_variant.price
        product = self.product_variant.product
        if product.has_active_offer():
            price = round(product.get_discounted_price(price))
        return price

    def get_total_price(self):
        """Get total price for this cart item (discounted price * quantity)"""
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
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Order #{self.order_id} - {self.user.email}"

    def generate_order_id(self):
        """Generate a unique order_id in the format BKDDMMYYYYHHMMSSmmm."""
        prefix = "BK"
        timestamp = timezone.now()

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
    cancel_reason = models.CharField(max_length=500, blank=True, null=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Item #{self.id} - {self.product_variant}"
    
    def total_amount(self):
        # discount price is neither unit price or after discounted price
        return self.discount_price*self.quantity
    
    def is_refunded(self):
        """Check if this order item has been refunded by checking transactions"""
        try:
            return Transaction.objects.filter(
                user=self.order.user,
                transaction_type='refund',
                description__icontains=f'item {self.id}'
            ).exists()
        except:
            return False
    
    def has_credit_note(self):
        """Check if this order item has a credit note"""
        # Use a direct database query - most reliable method
        # This works regardless of prefetch_related or relationship access issues
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM users_creditnote WHERE order_item_id = %s LIMIT 1",
                    [self.id]
                )
                return cursor.fetchone() is not None
        except Exception:
            # If table doesn't exist or any error, return False
            return False
    

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
    

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cod', 'COD'),
        ('refund', 'Refund'),
        ('wallet_addition', 'Wallet Addition'),
        ('wallet_debit', 'Wallet Debit'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    order_item = models.ForeignKey('OrderItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    transaction_id = models.CharField(max_length=50, unique=True, editable=False)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='completed')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['-transaction_date'], name='users_trans_transac_12a4ad_idx'),
            models.Index(fields=['transaction_type'], name='users_trans_transac_dd58bb_idx'),
            models.Index(fields=['user', '-transaction_date'], name='users_trans_user_id_b50875_idx'),
        ]
    
    def generate_transaction_id(self):
        """Generate a unique transaction_id in the format TXN + timestamp + random."""
        prefix = "TXN"
        timestamp = timezone.now()
        base_id = f"{prefix}{timestamp.strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        transaction_id = base_id
        counter = 0
        while Transaction.objects.filter(transaction_id=transaction_id).exists():
            counter += 1
            transaction_id = f"{base_id}{random.randint(100, 999)}"
            if counter > 10:
                raise ValueError("Unable to generate a unique transaction_id after multiple attempts.")
        return transaction_id
    
    def save(self, *args, **kwargs):
        """Override save to set transaction_id on creation."""
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.transaction_id} - {self.get_transaction_type_display()} - ₹{self.amount}"


class Invoice(models.Model):
    """
    Invoice model to store locked invoice data.
    Invoice is created only when order status becomes 'shipped' and is locked thereafter.
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    invoice_date = models.DateField(auto_now_add=True)
    
    # Seller details (fixed)
    seller_name = models.CharField(max_length=200, default='Book Hive Pvt Ltd')
    seller_address = models.CharField(max_length=500, default='24/B MG Road, Bangalore')
    seller_phone = models.CharField(max_length=20, default='7907302778')
    seller_email = models.EmailField(default='info@bookhive.com')
    seller_gstin = models.CharField(max_length=20, default='29ABCDE1234F1Z5')
    
    # Customer details (snapshot at invoice creation)
    customer_name = models.CharField(max_length=200)
    customer_address = models.TextField()
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField()
    
    # Order details (snapshot)
    snapshot_order_id = models.CharField(max_length=50)  # Renamed to avoid clash with order.id
    order_date = models.DateField()
    payment_method = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Invoice summary (locked values)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Invoice items (locked snapshot at invoice creation - stored as JSON)
    # This ensures invoice never changes even if order items are modified or deleted
    invoice_items = models.JSONField(default=list, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-invoice_date', '-created_at']
    
    def generate_invoice_number(self):
        """Generate a unique invoice number in the format INV + timestamp."""
        prefix = "INV"
        timestamp = timezone.now()
        base_id = f"{prefix}{timestamp.strftime('%Y%m%d%H%M%S')}"
        
        invoice_number = base_id
        counter = 0
        while Invoice.objects.filter(invoice_number=invoice_number).exists():
            counter += 1
            suffix = str(random.randint(0, 9))
            invoice_number = f"{base_id}{suffix}"
            if counter > 10:
                raise ValueError("Unable to generate a unique invoice_number after multiple attempts.")
        return invoice_number
    
    def save(self, *args, **kwargs):
        """Override save to set invoice_number on creation."""
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - Order {self.snapshot_order_id}"


class CreditNote(models.Model):
    """
    Credit Note model to store credit note data for refunded/cancelled items.
    Credit note is generated per item when item is cancelled/returned AFTER invoice creation.
    Once generated, credit note cannot be edited.
    """
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='credit_note')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='credit_notes')
    credit_note_number = models.CharField(max_length=50, unique=True, editable=False)
    credit_note_date = models.DateField(auto_now_add=True)
    
    # Reference to original invoice
    original_invoice_number = models.CharField(max_length=50)
    original_invoice_date = models.DateField()
    
    # Customer details (snapshot)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField()
    
    # Seller details (fixed)
    seller_name = models.CharField(max_length=200, default='Book Hive Pvt Ltd')
    seller_address = models.CharField(max_length=500, default='24/B MG Road, Bangalore')
    seller_phone = models.CharField(max_length=20, default='7907302778')
    seller_email = models.EmailField(default='info@bookhive.com')
    seller_gstin = models.CharField(max_length=20, default='29ABCDE1234F1Z5')
    
    # Refund details
    item_name = models.CharField(max_length=500)
    quantity_returned = models.PositiveIntegerField()
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Summary (locked values)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)  # Item total before discount
    discount_reversal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Discount to reverse
    total_refund = models.DecimalField(max_digits=10, decimal_places=2)  # Final refund amount
    
    # Payment details
    original_payment_method = models.CharField(max_length=100)
    refund_method = models.CharField(max_length=100, default='Wallet')
    
    # Reason
    reason = models.CharField(max_length=500, blank=True, null=True)  # cancellation/return reason
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-credit_note_date', '-created_at']
    
    def generate_credit_note_number(self):
        """Generate a unique credit note number in the format CN + timestamp."""
        prefix = "CN"
        timestamp = timezone.now()
        base_id = f"{prefix}{timestamp.strftime('%Y%m%d%H%M%S')}"
        
        credit_note_number = base_id
        counter = 0
        while CreditNote.objects.filter(credit_note_number=credit_note_number).exists():
            counter += 1
            suffix = str(random.randint(0, 9))
            credit_note_number = f"{base_id}{suffix}"
            if counter > 10:
                raise ValueError("Unable to generate a unique credit_note_number after multiple attempts.")
        return credit_note_number
    
    def save(self, *args, **kwargs):
        """Override save to set credit_note_number on creation."""
        if not self.credit_note_number:
            self.credit_note_number = self.generate_credit_note_number()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Credit Note {self.credit_note_number} - Item {self.order_item.id}"


class CustomerSupport(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
    )
    
    CATEGORY_CHOICES = (
        ('Order Related', 'Order Related'),
        ('Payment Related', 'Payment Related'),
        ('Product Related', 'Product Related'),
        ('Shipping Related', 'Shipping Related'),
        ('Returns & Refunds', 'Returns & Refunds'),
        ('Other', 'Other'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='support_queries')
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_reply = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Query from {self.user.email} - {self.subject}"