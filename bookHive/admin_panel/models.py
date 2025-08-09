from django.db import models
from django.utils.timezone import now




# Create your models here.
class Genre(models.Model):
    
    genre_name = models.CharField(max_length=255)  # Ensures name is not null and unique
    is_active = models.BooleanField()

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
    created_at = models.DateTimeField(default=now)  # Auto timestamp
    updated_at = models.DateTimeField(auto_now=True)  # Auto-updated on modification

    def __str__(self):
        return self.book_title
    

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

    


    