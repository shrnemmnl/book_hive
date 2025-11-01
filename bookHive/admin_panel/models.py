from django.db import models
from django.forms import ValidationError
from django.utils import timezone


# Create your models here.
class Genre(models.Model):
    
    genre_name = models.CharField(max_length=255)  # Ensures name is not null and unique
    is_active = models.BooleanField()
    discount_percentage = models.PositiveIntegerField(default=0, help_text="Enter % discount (e.g., 10 for 10%)")
    is_offer = models.BooleanField(default=False, help_text="Is there an active offer?")
    offer_title = models.CharField(max_length=100, blank=True, null=True, help_text="Offer name like 'Summer Sale'")
    

    def __str__(self):
        return self.genre_name
    

    
class Product(models.Model):
    
    book_title = models.CharField(max_length=255)  
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)  # Foreign Key to Category
    author = models.CharField(max_length=255)
    description = models.CharField(max_length=500)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True) 
    is_active = models.BooleanField()
    discount_percentage = models.PositiveIntegerField(default=0, help_text="Enter % discount (e.g., 10 for 10%)")
    is_offer = models.BooleanField(default=False, help_text="Is there an active offer?")
    offer_title = models.CharField(max_length=100, blank=True, null=True, help_text="Offer name like 'Summer Sale'")
    created_at = models.DateTimeField(default=timezone.now)  # Auto timestamp (callable, not called)
    updated_at = models.DateTimeField(auto_now=True)  # Auto-updated on modification

    def __str__(self):
        return self.book_title
    
    def get_best_discount_percentage(self):
        """
        Returns the higher discount between product offer and genre offer.
        Returns 0 if no offers are active.
        """
        product_discount = self.discount_percentage if self.is_offer else 0
        genre_discount = self.genre.discount_percentage if (self.genre and self.genre.is_offer) else 0
        return max(product_discount, genre_discount)
    
    def get_active_offer_title(self):
        """
        Returns the title of the active offer with higher discount.
        Returns None if no offers are active.
        """
        product_discount = self.discount_percentage if self.is_offer else 0
        genre_discount = self.genre.discount_percentage if (self.genre and self.genre.is_offer) else 0
        
        if product_discount >= genre_discount and product_discount > 0:
            return self.offer_title or f"{product_discount}% OFF"
        elif genre_discount > 0:
            return self.genre.offer_title or f"{genre_discount}% OFF"
        return None
    
    def has_active_offer(self):
        """Returns True if either product or genre has an active offer."""
        return (self.is_offer and self.discount_percentage > 0) or \
               (self.genre and self.genre.is_offer and self.genre.discount_percentage > 0)
    
    def get_discounted_price(self, original_price):
        """
        Calculates the discounted price based on the best available discount.
        Args:
            original_price: The original price to apply discount on
        Returns:
            The discounted price
        """
        discount_percentage = self.get_best_discount_percentage()
        if discount_percentage > 0:
            discount_amount = (original_price * discount_percentage) / 100
            return original_price - discount_amount
        return original_price
    

class Variant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.IntegerField()
    available_quantity = models.IntegerField()
    published_date = models.DateField()
    publisher = models.CharField(max_length=255)
    page = models.IntegerField()
    language = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)


    


class ProductImage(models.Model):
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    image1 = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image2 = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image3 = models.ImageField(upload_to='product_images/', null=True, blank=True) 
   
    uploaded_at = models.DateTimeField(auto_now_add=True)




class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    # User-specific coupon (null means it's available for everyone)
    specific_user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=True, blank=True, related_name='exclusive_coupons')
    is_referral_reward = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else '₹'}"

    def is_valid(self, user=None, cart_total=0):
        """Check if coupon is valid for use"""
        now = timezone.now()
        
        # Check if coupon is active
        if not self.is_active:
            return False, "This coupon is not active."
        
        # Check if coupon is user-specific
        if self.specific_user and user:
            if self.specific_user != user:
                return False, "This coupon is not available for you."
        elif self.specific_user and not user:
            return False, "This coupon requires authentication."
        
        # Check date validity
        if now < self.valid_from:
            return False, "This coupon is not yet valid."
        
        if now > self.valid_until:
            return False, "This coupon has expired."
        
        # Check minimum amount
        if cart_total < self.minimum_amount:
            return False, f"Minimum order amount of ₹{self.minimum_amount} required."
        
        # Check if coupon has already been used by this user
        if user:
            # Check if user has already used this specific coupon
            has_used = CouponUsage.objects.filter(user=user, coupon=self).exists()
            if has_used:
                return False, "This coupon can only be used once."
        
        return True, "Coupon is valid."

    def calculate_discount(self, cart_total):
        """Calculate discount amount for given cart total"""
        if self.discount_type == 'percentage':
            discount = (float(cart_total) * float(self.discount_value)) / 100
            if self.maximum_discount:
                discount = min(discount, self.maximum_discount)
        else:
            discount = self.discount_value
        
        # Ensure discount doesn't exceed cart total
        return min(discount, cart_total)
    



class CouponUsage(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    order = models.ForeignKey('users.Order', on_delete=models.CASCADE, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'coupon']

    def __str__(self):
        return f"{self.user.email} used {self.coupon.code}"