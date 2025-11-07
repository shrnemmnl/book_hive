from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from users.models import CustomUser,Order,OrderItem,Review, Wallet # Import your user model
from .models import Genre, Product, Variant, ProductImage,Coupon,CouponUsage
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache, cache_control
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.shortcuts import  get_object_or_404
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import F,Q, Sum, Count, DecimalField
from django.db.models.functions import TruncDate
import base64
import re
from django.core.files.base import ContentFile
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import logging



logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)  # Create logger





# Create your views here.
@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
def admin_signin(request):

    if request.user.is_authenticated:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        email=request.POST.get('email', "").strip()
        password=request.POST.get('password', "").strip()

        isuser=authenticate(request, email=email, password=password)
        

        if isuser is not None and isuser.is_superuser:
            login(request, isuser)
            messages.success(request, 'You are successfully logged in!')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')

    return render(request, 'admin/admin_signin.html')




@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required(login_url='admin_signin')  # Redirect to login page if not authenticated
def admin_dashboard(request):


    
    """Generate sales report with filtering options"""
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    orders = Order.objects.filter(
        status__in=['pending', 'shipped', 'delivered'],
        is_active=True
    ).select_related('user')
    
    now = timezone.now()
    filter_label = "All Time"
    
    if filter_type == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_day)
        filter_label = "Today"
    elif filter_type == 'week':
        start_of_week = now - timedelta(days=7)
        orders = orders.filter(created_at__gte=start_of_week)
        filter_label = "Past 7 Days"
    elif filter_type == 'month':
        start_of_month = now - timedelta(days=30)
        orders = orders.filter(created_at__gte=start_of_month)
        filter_label = "Past 30 Days"
    elif filter_type == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            orders = orders.filter(created_at__range=[start, end])
            filter_label = f"{start_date} to {end_date}"
        except ValueError:
            messages.error(request, "Invalid date format")
    
    summary = orders.aggregate(
        total_orders=Count('id'),
        total_amount=Sum('net_amount'),
        total_discount=Sum('coupon_discount'),
        total_subtotal=Sum('subtotal')
    )
    
    # Handle None values
    summary['total_orders'] = summary['total_orders'] or 0
    summary['total_amount'] = summary['total_amount'] or 0
    summary['total_discount'] = summary['total_discount'] or 0
    summary['total_subtotal'] = summary['total_subtotal'] or 0
    
    orders_list = orders.order_by('-created_at')
    
    paginator = Paginator(orders_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)
    
    context = {
        'orders': orders_page,
        'summary': summary,
        'filter_type': filter_type,
        'filter_label': filter_label,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'admin/admin_dashboard.html', context)



    



@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required(login_url='admin_signin')  
def books(request):
    
    books = Product.objects.select_related('genre').order_by('-updated_at')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(books, 5)
    books = paginator.get_page(page)


    return render(request, 'admin/books.html', {"books":books})



@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required(login_url='admin_signin')  
def admin_order(request):

    order_details=Order.objects.prefetch_related('order_items').order_by('-created_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(order_details, 10)
    order_details = paginator.get_page(page)

    return render(request, 'admin/admin_order.html', {"order_details":order_details})



@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required(login_url='admin_signin')  
def update_order_item_status(request,order_item_id):
    status=request.POST.get('status')
    order_item=OrderItem.objects.get(id=order_item_id)
    order_item.status=status
    order_item.save()

    return redirect('order')



def genre(request):

    genre= Genre.objects.all().order_by('-is_active')

    paginator = Paginator(genre, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        genre_name = request.POST.get('genre', "").strip()
        is_offer = request.POST.get('is_offer') == 'on'
        offer_title = request.POST.get('offer_title', "").strip()
        discount_percentage = request.POST.get('discount_percentage', 0)
        
        if not genre_name:
            messages.error(request, 'Genre name is required.')
            return redirect('genre')
        
        if not re.match(r'^[A-Za-z\s]+$', genre_name):
            messages.error(request, 'Genre name must contain only alphabets and spaces.')
            return redirect('genre')
        
        if len(genre_name) > 255:
            messages.error(request, 'Genre name is too long (max 255 characters).')
            return redirect('genre')
        
        if Genre.objects.filter(genre_name=genre_name.lower()).exists():
            messages.error(request, 'Genre already exists.')
            return redirect('genre')
        
        try:
            discount_percentage = int(discount_percentage) if discount_percentage else 0
            if discount_percentage < 0:
                messages.error(request, 'Discount percentage cannot be negative.')
                return redirect('genre')
            if discount_percentage >= 100:
                messages.error(request, 'Discount percentage must be less than 100%.')
                return redirect('genre')
        except ValueError:
            discount_percentage = 0
        
        Genre.objects.create(
            genre_name=genre_name.lower(),
            is_active=True,
            is_offer=is_offer,
            offer_title=offer_title if is_offer else '',
            discount_percentage=discount_percentage if is_offer else 0
        )
        messages.success(request, 'Genre added successfully.')
        return redirect('genre')
    
    return render(request, 'admin/genre.html', {'page_obj':page_obj})




def change_genre_status(request):
    if request.method == 'POST':
        genre_id=request.POST.get('genre_id', "").strip()
        status = Genre.objects.get(id=genre_id)
        status.is_active=not status.is_active
        status.save()
        return redirect('genre')
    return render(request, 'admin/genre.html')




def genre_edit(request, genre_id):

    genre = Genre.objects.get(id=genre_id)

    if request.method == 'POST':
        name = request.POST.get('genre', "").strip()
        is_offer = request.POST.get('is_offer') == 'on'
        offer_title = request.POST.get('offer_title', "").strip()
        discount_percentage = request.POST.get('discount_percentage', 0)
        
        genre = Genre.objects.get(id=genre_id)
        
        if not name:
            messages.error(request, 'Genre name is required.')
            return redirect('genre_edit', genre_id=genre.id)
        
        # Validate genre name contains only alphabets (and spaces)
        if not re.match(r'^[A-Za-z\s]+$', name):
            messages.error(request, 'Genre name must contain only alphabets and spaces.')
            return redirect('genre_edit', genre_id=genre.id)
        
        if len(name) > 255:
            messages.error(request, 'Genre name is too long (max 255 characters).')
            return redirect('genre_edit', genre_id=genre.id)

        if Genre.objects.filter(genre_name=name.lower()).exclude(id=genre_id).exists():
            messages.error(request, 'Genre already exists.')
            return redirect('genre_edit', genre_id=genre.id)
        
        try:
            discount_percentage = int(discount_percentage) if discount_percentage else 0
            if discount_percentage < 0:
                messages.error(request, 'Discount percentage cannot be negative.')
                return redirect('genre_edit', genre_id=genre.id)
            if discount_percentage >= 100:
                messages.error(request, 'Discount percentage must be less than 100%.')
                return redirect('genre_edit', genre_id=genre.id)
        except ValueError:
            discount_percentage = 0
                
        genre.genre_name = name.lower()
        genre.is_offer = is_offer
        genre.offer_title = offer_title if is_offer else ''
        genre.discount_percentage = discount_percentage if is_offer else 0
        genre.save()
        messages.success(request, 'Genre Edited Successfully.')
        return redirect('genre')
 
    return render(request, 'admin/genre_edit.html', {'genres':genre})



def genre_search(request):
    
    
    search_query=request.POST.get('genre_search', "").strip()
    genre = Genre.objects.filter(genre_name__istartswith=search_query)

    paginator = Paginator(genre, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
        
    
    return render(request, 'admin/genre.html', {'page_obj':page_obj})




def add_new_book(request):
    if request.method == 'POST':
        book_name = request.POST.get('book_name', "").strip()
        author = request.POST.get('author', "").strip()
        genre_id = request.POST.get('genre_id', "").strip()
        description = request.POST.get('description', "").strip()
        image = request.FILES.get('image')

        if Product.objects.filter(book_title=book_name).exists():
            messages.error(request, 'Book already exists.')
            return redirect('add_new_book')  

        try:
            genre = Genre.objects.get(id=int(genre_id))
        except (Genre.DoesNotExist, ValueError):
            messages.error(request, 'Invalid genre selected.')
            return redirect('add_new_book')

        if not image:
            messages.error(request, 'Book image is required.')
            return redirect('add_new_book')
        
        valid_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
        valid_mime_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
        
        file_extension = image.name.split(".")[-1].lower() if "." in image.name else ""
        if not file_extension or file_extension not in valid_extensions:
            messages.error(request, 'Please upload a valid image file (jpg, jpeg, png, gif, or webp formats only).')
            return redirect('add_new_book')
        
        file_mime_type = image.content_type.lower() if hasattr(image, 'content_type') and image.content_type else ""
        if not file_mime_type or file_mime_type not in valid_mime_types:
            messages.error(request, 'Invalid file type detected. Please upload a valid image file (jpg, jpeg, png, gif, or webp formats only).')
            return redirect('add_new_book')

        Product.objects.create(
            book_title=book_name,
            author=author,
            genre=genre,
            is_active=True,
            description=description,
            image=image
        )
        
        messages.success(request, 'Book added successfully!')
        return render(request, 'admin/add_new_book.html', {'redirect': True, 'redirect_url': 'books'})

    all_genres = Genre.objects.all()   
    return render(request, 'admin/add_new_book.html', {'all_genres': all_genres})



def book_edit(request, book_id):
    
    book = Product.objects.get(id=book_id)
    genres = Genre.objects.all()
    error = {}

    if request.method == 'POST':
        book_name = request.POST.get('book_title', "").strip()
        author = request.POST.get('book_author', "").strip()
        description = request.POST.get('book_description', "").strip()
        genre_id=request.POST.get('genre_id', "").strip()
        image = request.FILES.get('image')
        # Offer Fields
        is_offer = request.POST.get('is_offer') == 'on'
        offer_title = request.POST.get('offer_title', "").strip()
        discount_percentage = request.POST.get('discount_percentage', 0)

        is_valid = True

        # Discount percentage validation
        if is_offer and discount_percentage:
            try:
                discount_percentage = int(discount_percentage)
                if discount_percentage < 0:
                    error['discount_percentage'] = "Discount percentage cannot be negative."
                    is_valid = False
                elif discount_percentage >= 100:
                    error['discount_percentage'] = "Discount percentage must be less than 100%."
                    is_valid = False
            except (ValueError, AttributeError):
                error['discount_percentage'] = "Discount percentage must be a valid number."
                is_valid = False
        
        if image:
            valid_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
            valid_mime_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
            
            file_extension = image.name.split(".")[-1].lower() if "." in image.name else ""
            if not file_extension or file_extension not in valid_extensions:
                error['valid_image'] = "Please upload a valid image file (jpg, jpeg, png, gif, or webp formats only)."
                is_valid = False
            
            if is_valid:
                file_mime_type = image.content_type.lower() if hasattr(image, 'content_type') and image.content_type else ""
                if not file_mime_type or file_mime_type not in valid_mime_types:
                    error['valid_image'] = "Invalid file type detected. Please upload a valid image file (jpg, jpeg, png, gif, or webp formats only)."
                    is_valid = False

        if is_valid:
            book = Product.objects.get(id=book_id)
            book.book_title = book_name
            book.genre =Genre.objects.get(id=genre_id) 
            print(genre_id)
            book.author = author

            if image:
                book.image = image

            book.description = description
            book.is_offer = is_offer
            book.offer_title = offer_title if is_offer else ''
            book.discount_percentage = int(discount_percentage) if is_offer else 0

            book.save()
            messages.success(request, f'{book.book_title} Updated successfully!')

            return redirect('books')  


    return render(request, 'admin/book_edit.html',{'book':book,'genres':genres ,'error':error})





def book_delete(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_delete', "").strip()
        status = Product.objects.get(id=book_id)
        status.is_active=not status.is_active
        status.save()
        return redirect('books')
        
    return render(request, 'admin/books.html',{'status':status})




def view_variant(request, book_id):

    variants = Variant.objects.filter(product=book_id).prefetch_related('productimage_set')

    first_variant=book_id

    return render(request, 'admin/view_variant.html', {
        'variants': variants,
        'first_variant':first_variant
    })


def variant_delete(request):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id', "").strip()  #comes from html

        variant = Variant.objects.get(id=variant_id)
        variant.is_active=not variant.is_active
        variant.save()
        return redirect(f'view_variant/{variant.product.id}')
        
    return render(request, 'admin/view_variant.html')



def add_variant(request, book_id):
    if request.method == 'POST':
        publisher = request.POST.get('publisher', "").strip()
        published_date = request.POST.get('published_date', "").strip()
        stock = request.POST.get('stock', "").strip()
        language = request.POST.get('language', "").strip()
        price = request.POST.get('price', "").strip()
        page = request.POST.get('page', "").strip()
         # Handling file uploads correctly
        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')

        try:
            product = Product.objects.get(id=book_id)  # Fetch Product instance
        except Product.DoesNotExist:
            messages.error(request,"Product not found")
            return redirect('books')
        
        if not publisher or not published_date or not language or not page:
            messages.error(request, 'All fields are required.')
            return redirect(reverse('view_variant', args=[book_id]))
        
        try:
            stock = int(stock) if stock else 0
            if stock < 0:
                messages.error(request, 'Stock cannot be negative.')
                return redirect(reverse('view_variant', args=[book_id]))
        except ValueError:
            messages.error(request, 'Invalid stock value.')
            return redirect(reverse('view_variant', args=[book_id]))
        
        try:
            price = int(price) if price else 0
            if price <= 0:
                messages.error(request, 'Price must be positive.')
                return redirect(reverse('view_variant', args=[book_id]))
        except ValueError:
            messages.error(request, 'Invalid price value.')
            return redirect(reverse('view_variant', args=[book_id]))
        
        try:
            page = int(page) if page else 0
            if page <= 0:
                messages.error(request, 'Page count must be positive.')
                return redirect(reverse('view_variant', args=[book_id]))
        except ValueError:
            messages.error(request, 'Invalid page count.')
            return redirect(reverse('view_variant', args=[book_id]))
        
        new_variant = Variant.objects.create(
            product=product,
            publisher=publisher,
            published_date=published_date,
            available_quantity=stock,
            language=language,
            page=page,
            price=price,
            )
        
         # Save images only if they exist
        if image1 or image2 or image3:
            ProductImage.objects.create(
                variant=new_variant,
                image1=image1,
                image2=image2,
                image3=image3
            )

        messages.success(request, 'Variant Added successfully!')

        return render(request, 'admin/add_variant.html', {
    'redirect': True,
    'redirect_url': reverse('view_variant', args=[book_id])
})

    return render(request, 'admin/add_variant.html', { 'book_id': book_id } )




@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
def admin_logout(request):

    logout(request)  # Clears the session and logs out the user
    request.session.flush()  # Ensures all session data is removed

    return redirect('admin_signin')



@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required(login_url='admin_signin')  
def customer_details(request):
    users = CustomUser.objects.all().exclude(is_superuser = True).order_by('-date_joined')

     # Create Paginator object with 10 customers per page
    paginator = Paginator(users, 10)  
    page_number = request.GET.get('page') # Get the current page number from request
    print(page_number) 
    page_obj = paginator.get_page(page_number)  # Get customers for the requested page
    print(page_obj)

    return render(request, 'admin/customer_details.html', {'users':page_obj})



def change_user_status(request):
    
    if request.method == 'POST':
        user_id=request.POST.get('user_id', "").strip()
        status = CustomUser.objects.get(id=user_id)
        status.is_active = not status.is_active
        status.save()

        return redirect('customer_details')
    
    return render(request, 'admin/customer_details.html')



def user_search(request):
    
    
    search_query=request.POST.get('user_search', "").strip()
    users = CustomUser.objects.filter(first_name__istartswith=search_query).exclude(is_superuser = True).order_by('-date_joined')

    # Create Paginator object with 10 customers per page
    paginator = Paginator(users, 10)  
    page_number = request.GET.get('page') # Get the current page number from request
    print(page_number) 
    page_obj = paginator.get_page(page_number)  # Get customers for the requested page
    print(page_obj)
        
    
    return render(request, 'admin/customer_details.html', {'users':page_obj})



def variant_edit(request, variant_id):
    error = {}    
    variant = get_object_or_404(Variant, id=variant_id)
    images = variant.productimage_set.first()  # set of 3 images per variant

    if request.method == 'POST':
        publisher = request.POST.get('publisher', "").strip()
        published_date = request.POST.get('published_date', "").strip()
        price = request.POST.get('price', "").strip()
        page = request.POST.get('page', "").strip()
        available_quantity = request.POST.get('stock', "").strip()
        language = request.POST.get('language', "").strip()

        # Get raw files
        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')

        # Get cropped base64 images
        image1_cropped = request.POST.get('image1_cropped')
        image2_cropped = request.POST.get('image2_cropped')
        image3_cropped = request.POST.get('image3_cropped')

        is_valid = True

        # --- Validations ---

        # 1️⃣ Published date
        try:           
            pub_date = datetime.strptime(published_date, "%Y-%m-%d").date()
            if pub_date > timezone.now().date():
                error['published_date'] = "Published date cannot be in the future."
                is_valid = False
        except ValueError:
            error['published_date'] = "Invalid published date format."
            is_valid = False

        # 2️⃣ Price
        if not price.replace('.', '', 1).isdigit():
            error['price'] = "Price must contain only digits."
            is_valid = False
        else:
            price = float(price)
            if price < 0:
                error['price'] = "Price cannot be negative."
                is_valid = False

        # 3️⃣ Page count
        if not page.isdigit() or int(page) <= 0:
            error['page'] = "Page count must be a positive integer."
            is_valid = False

        # 4️⃣ Available quantity
        if not available_quantity.isdigit() or int(available_quantity) <= 0:
            error['available_quantity'] = "Available quantity must be a positive integer."
            is_valid = False

        # 5️⃣ Image validation (raw files)
        valid_extensions = ["jpg", "jpeg", "png"]
        for img, name in zip([image1, image2, image3], ['Image 1', 'Image 2', 'Image 3']):
            if img:
                ext = img.name.split('.')[-1].lower()
                if ext not in valid_extensions:
                    error['valid_image'] = f"{name} must be in jpg, jpeg, or png format."
                    is_valid = False

        # 6️⃣ Cropped image validation
        for img_cropped, name in zip([image1_cropped, image2_cropped, image3_cropped],
                                     ['Image 1', 'Image 2', 'Image 3']):
            if img_cropped and not img_cropped.startswith("data:image"):
                error['valid_image'] = f"{name} has invalid cropped image format."
                is_valid = False

        # --- Save Variant ---
        if is_valid:
            variant.publisher = publisher
            variant.price = float(price)
            variant.page = int(page)
            variant.available_quantity = int(available_quantity)
            variant.language = language
            variant.save()

            # Handle ProductImage
            product_image, _ = ProductImage.objects.get_or_create(variant=variant)

            # Helper to save cropped/base64 image
            def save_cropped_image(cropped, raw, field_name):
                if cropped:
                    format, imgstr = cropped.split(';base64,')
                    ext = format.split('/')[-1]
                    setattr(product_image, field_name, ContentFile(base64.b64decode(imgstr), name=f'{field_name}_{variant.id}.{ext}'))
                elif raw:
                    setattr(product_image, field_name, raw)

            save_cropped_image(image1_cropped, image1, 'image1')
            save_cropped_image(image2_cropped, image2, 'image2')
            save_cropped_image(image3_cropped, image3, 'image3')

            product_image.save()
            messages.success(request, 'Variants updated successfully!')
            return redirect('books')

    return render(request, 'admin/variant_edit.html', {'variant': variant, 'images': images, 'error': error})




@login_required
def admin_order_details(request, order_id):

    order = get_object_or_404(Order, id=order_id)
    
    logger.info(f"admin side status: {order.status} and order status : {"Paid" if order.is_paid else "Not Paid."}")

    if request.method == 'POST':
        
        new_status = request.POST.get('status')
        logger.info(f"admin side status: {new_status} and order status : {"Paid" if order.is_paid else "Not Paid."}")
        
        valid_statuses = ['pending', 'shipped', 'delivered', 'cancelled', 'request to cancel','return approved','request to return']
        
        # for cod
        if new_status == 'delivered':
            order.is_paid = True


        elif new_status not in valid_statuses:
            messages.error(request, "Invalid status selected.")
            return redirect('admin_order_details', order_id=order.id)
        
        #If item cancelled stock needs to update. mainly in cash on delivery.    
        elif new_status == 'cancelled' and not order.is_paid:

            #Stock need to update
            for item in order.order_items.all():
                variant = item.product_variant  
                variant.available_quantity = F('available_quantity') + item.quantity  # db math - more safe and concorency proof
                variant.save(update_fields=['available_quantity'])  #save only field available_quantity
            
        # Check if the item is being cancelled and the order is paid
        elif new_status in ['return approved','cancelled'] and order.is_paid:

            user = order.user
            print("hiiiiiiiiiiiiiiiiiii")

            #Stock need to update
            for item in order.order_items.all():
                variant = item.product_variant  
                variant.available_quantity = F('available_quantity') + item.quantity  # db math - more safe and concorency proof
                variant.save(update_fields=['available_quantity'])  #save only field available_quantity
                
            
            
            #Wallet crediting
            refund_amount = order.net_amount  # Changed from net_amount to total_amount
            user_wallet, created = Wallet.objects.get_or_create(user=user)
            user_wallet.wallet_amount += refund_amount
            user_wallet.save()
            try:
                from users.models import WalletTransaction
                WalletTransaction.objects.create(
                    user=user,
                    amount=refund_amount,
                    transaction_type='refund',
                    description=f'Refund for order {order.order_id}'
                )
            except Exception as e:
                logger.error(f"Failed to log wallet refund: {e}")

            if new_status == 'cancelled':
                order.status = 'cancelled'
            else:
                order.status = 'return approved'
    
            order.save()
        
            messages.success(request, f"Refunded ₹{refund_amount:.2f} to user {user.email}'s wallet.")
          
            return redirect('admin_order_details', order_id=order.id)

        order.status = new_status
        order.save()
        

    context = {
        'reload': True,
        'order': order,
        'heading': {'name': f'Order Details #{ order.id }'}
    }

    return render(request, 'admin/admin_order_details.html', context)




def admin_review(request):
    reviews = Review.objects.select_related('user', 'product').order_by('-created_at')
    return render(request, "admin/admin_review.html", {'reviews':reviews})


def toggle_review_status(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_active = not review.is_active  # Flip True to False or vice versa
    review.save()
    status_text = "Activated" if review.is_active else "Deactivated"
    messages.success(request, f'Review status changed to {status_text}.')
    return redirect('admin_review')


@never_cache
@login_required
def coupon_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    discount_type_filter = request.GET.get('discount_type', 'all')
    
    coupons = Coupon.objects.all()
    
    if query:
        coupons = coupons.filter(
            Q(code__icontains=query) |
            Q(description__icontains=query)
        )
    
    if status_filter == 'active':
        coupons = coupons.filter(is_active=True, valid_until__gte=timezone.now())
    elif status_filter == 'inactive':
        coupons = coupons.filter(is_active=False)
    elif status_filter == 'expired':
        coupons = coupons.filter(valid_until__lt=timezone.now())
    
    if discount_type_filter != 'all':
        coupons = coupons.filter(discount_type=discount_type_filter)
    
    coupons = coupons.order_by('-created_at')
    
    # Statistics
    total_coupons = Coupon.objects.count()
    active_coupons = Coupon.objects.filter(is_active=True, valid_until__gte=timezone.now()).count()
    expired_coupons = Coupon.objects.filter(valid_until__lt=timezone.now()).count()
    total_usage = CouponUsage.objects.count()
    
    paginator = Paginator(coupons, 10)
    page = request.GET.get('page')
    
    try:
        coupons = paginator.page(page)
    except PageNotAnInteger:
        coupons = paginator.page(1)
    except EmptyPage:
        coupons = paginator.page(paginator.num_pages)
    
    context = {
        'coupons': coupons,
        'query': query,
        'status_filter': status_filter,
        'discount_type_filter': discount_type_filter,
        'total_coupons': total_coupons,
        'active_coupons': active_coupons,
        'expired_coupons': expired_coupons,
        'total_usage': total_usage,
    }
    
    return render(request, 'coupons/coupon_list.html', context)

@login_required
def add_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()
        discount_type = request.POST.get('discount_type', 'percentage')
        discount_value = request.POST.get('discount_value', '').strip()
        minimum_amount = request.POST.get('minimum_amount', '0').strip()
        maximum_discount = request.POST.get('maximum_discount', '').strip()
        usage_limit = request.POST.get('usage_limit', '').strip()
        valid_from = request.POST.get('valid_from', '').strip()
        valid_until = request.POST.get('valid_until', '').strip()
        
        errors = []
        
        # Validate coupon code
        if not code:
            errors.append("Coupon code is required")
        elif len(code) < 3:
            errors.append("Coupon code should be at least 3 characters long")
        elif len(code) > 50:
            errors.append("Coupon code should not exceed 50 characters")
        elif not re.match(r'^[A-Z0-9]+$', code):
            errors.append("Coupon code should only contain uppercase letters and numbers")
        elif Coupon.objects.filter(code=code).exists():
            errors.append("A coupon with this code already exists")
        
        # Validate discount value
        if not discount_value:
            errors.append("Discount value is required")
        else:
            try:
                discount_value = float(discount_value)
                if discount_value <= 0:
                    errors.append("Discount value must be greater than 0")
                if discount_type == 'percentage' and discount_value > 100:
                    errors.append("Percentage discount cannot exceed 100%")
            except ValueError:
                errors.append("Please enter a valid discount value")
        
        # Validate minimum amount
        try:
            minimum_amount = float(minimum_amount)
            if minimum_amount < 0:
                errors.append("Minimum amount cannot be negative")
        except ValueError:
            errors.append("Please enter a valid minimum amount")
        
        # Validate maximum discount
        if maximum_discount:
            try:
                maximum_discount = float(maximum_discount)
                if maximum_discount <= 0:
                    errors.append("Maximum discount must be greater than 0")
            except ValueError:
                errors.append("Please enter a valid maximum discount")
        else:
            maximum_discount = None
       
        
        # Validate dates
        if not valid_from:
            errors.append("Valid from date is required")
        if not valid_until:
            errors.append("Valid until date is required")
        
        if valid_from and valid_until:
            try:
                from_date = timezone.make_aware(datetime.strptime(valid_from, '%Y-%m-%dT%H:%M'))
                until_date = timezone.make_aware(datetime.strptime(valid_until, '%Y-%m-%dT%H:%M'))
                
                if from_date >= until_date:
                    errors.append("Valid from date must be before valid until date")
                
                if until_date <= timezone.now():
                    errors.append("Valid until date must be in the future")
                    
            except ValueError:
                errors.append("Please enter valid dates")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'coupons/add_coupon.html', {
                'code': request.POST.get('code', ''),
                'description': description,
                'discount_type': discount_type,
                'discount_value': request.POST.get('discount_value', ''),
                'minimum_amount': request.POST.get('minimum_amount', ''),
                'maximum_discount': request.POST.get('maximum_discount', ''),
                
                'valid_from': valid_from,
                'valid_until': valid_until,
            })
        
        try:
            Coupon.objects.create(
                code=code,
                description=description,
                discount_type=discount_type,
                discount_value=discount_value,
                minimum_amount=minimum_amount,
                maximum_discount=maximum_discount,
                valid_from=from_date,
                valid_until=until_date,
                is_active=True
            )
            messages.success(request, f"Coupon '{code}' created successfully")
            return redirect('coupon_list')
        except Exception as e:
            messages.error(request, "An error occurred while creating the coupon")
            return render(request, 'coupons/add_coupon.html', {
                'code': request.POST.get('code', ''),
                'description': description,
                'discount_type': discount_type,
                'discount_value': request.POST.get('discount_value', ''),
                'minimum_amount': request.POST.get('minimum_amount', ''),
                'maximum_discount': request.POST.get('maximum_discount', ''),
                'valid_from': valid_from,
                'valid_until': valid_until,
            })
    
    return render(request, 'coupons/add_coupon.html')




@login_required
def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()
        discount_type = request.POST.get('discount_type', 'percentage')
        discount_value = request.POST.get('discount_value', '').strip()
        minimum_amount = request.POST.get('minimum_amount', '0').strip()
        maximum_discount = request.POST.get('maximum_discount', '').strip()
        usage_limit = request.POST.get('usage_limit', '').strip()
        valid_from = request.POST.get('valid_from', '').strip()
        valid_until = request.POST.get('valid_until', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        errors = []
        
        # Validate coupon code
        if not code:
            errors.append("Coupon code is required")
        elif len(code) < 3:
            errors.append("Coupon code should be at least 3 characters long")
        elif len(code) > 50:
            errors.append("Coupon code should not exceed 50 characters")
        elif not re.match(r'^[A-Z0-9]+$', code):
            errors.append("Coupon code should only contain uppercase letters and numbers")
        elif Coupon.objects.filter(code=code).exclude(id=coupon.id).exists():
            errors.append("A coupon with this code already exists")
        
        # Validate discount value
        if not discount_value:
            errors.append("Discount value is required")
        else:
            try:
                discount_value = float(discount_value)
                if discount_value <= 0:
                    errors.append("Discount value must be greater than 0")
                if discount_type == 'percentage' and discount_value > 100:
                    errors.append("Percentage discount cannot exceed 100%")
            except ValueError:
                errors.append("Please enter a valid discount value")
        
        # Validate minimum amount
        try:
            minimum_amount = float(minimum_amount)
            if minimum_amount < 0:
                errors.append("Minimum amount cannot be negative")
        except ValueError:
            errors.append("Please enter a valid minimum amount")
        
        # Validate maximum discount
        if maximum_discount:
            try:
                maximum_discount = float(maximum_discount)
                if maximum_discount <= 0:
                    errors.append("Maximum discount must be greater than 0")
            except ValueError:
                errors.append("Please enter a valid maximum discount")
        else:
            maximum_discount = None
        
       
        
        # Validate dates
        if not valid_from:
            errors.append("Valid from date is required")
        if not valid_until:
            errors.append("Valid until date is required")
        
        if valid_from and valid_until:
            try:
                from_date = timezone.make_aware(datetime.strptime(valid_from, '%Y-%m-%dT%H:%M'))
                until_date = timezone.make_aware(datetime.strptime(valid_until, '%Y-%m-%dT%H:%M'))
                
                if from_date >= until_date:
                    errors.append("Valid from date must be before valid until date")
                    
            except ValueError:
                errors.append("Please enter valid dates")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                coupon.code = code
                coupon.description = description
                coupon.discount_type = discount_type
                coupon.discount_value = discount_value
                coupon.minimum_amount = minimum_amount
                coupon.maximum_discount = maximum_discount
                coupon.valid_from = from_date
                coupon.valid_until = until_date
                coupon.is_active = is_active
                coupon.save()
                
                messages.success(request, f"Coupon '{code}' updated successfully")
                return redirect('coupon_list')
            except Exception as e:
                messages.error(request, "An error occurred while updating the coupon")
    
    # Get usage statistics
    usage_count = CouponUsage.objects.filter(coupon=coupon).count()
    
    context = {
        'coupon': coupon,
        'usage_count': usage_count,
    }
    
    return render(request, 'coupons/edit_coupon.html', context)

@login_required
def toggle_coupon_status(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'activate':
            coupon.is_active = True
            coupon.save()
            messages.success(request, f"Coupon '{coupon.code}' has been activated successfully")
        elif action == 'deactivate':
            coupon.is_active = False
            coupon.save()
            messages.success(request, f"Coupon '{coupon.code}' has been deactivated successfully")
        
        return redirect('coupon_list')
    
    # Get usage statistics for confirmation
    usage_count = CouponUsage.objects.filter(coupon=coupon).count()
    
    return render(request, 'coupons/toggle_coupon_status.html', {
        'coupon': coupon,
        'usage_count': usage_count,
    })


# Sales Report Views
def sales_report(request):
    """Generate sales report with filtering options"""
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    orders = Order.objects.filter(
        status__in=['pending', 'shipped', 'delivered'],
        is_active=True
    ).select_related('user', 'address').prefetch_related('order_items__product_variant__product')
    
    now = timezone.now()
    filter_label = "All Time"
    
    if filter_type == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_day)
        filter_label = "Today"
    elif filter_type == 'week':
        start_of_week = now - timedelta(days=7)
        orders = orders.filter(created_at__gte=start_of_week)
        filter_label = "Past 7 Days"
    elif filter_type == 'month':
        start_of_month = now - timedelta(days=30)
        orders = orders.filter(created_at__gte=start_of_month)
        filter_label = "Past 30 Days"
    elif filter_type == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            orders = orders.filter(created_at__range=[start, end])
            filter_label = f"{start_date} to {end_date}"
        except ValueError:
            messages.error(request, "Invalid date format")
    
    summary = orders.aggregate(
        total_orders=Count('id'),
        total_amount=Sum('net_amount'),
        total_discount=Sum('coupon_discount'),
        total_subtotal=Sum('subtotal')
    )
    
    # Handle None values
    summary['total_orders'] = summary['total_orders'] or 0
    summary['total_amount'] = summary['total_amount'] or 0
    summary['total_discount'] = summary['total_discount'] or 0
    summary['total_subtotal'] = summary['total_subtotal'] or 0
    
    # Get detailed order list
    orders_list = orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders_list, 20)
    page = request.GET.get('page', 1)
    
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)
    
    context = {
        'orders': orders_page,
        'summary': summary,
        'filter_type': filter_type,
        'filter_label': filter_label,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'admin/sales_report.html', context)


def download_sales_report_pdf(request):
    """Download sales report as PDF"""
    # Get same filters as main report
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Apply same filtering logic
    orders = Order.objects.filter(
        status__in=['pending', 'shipped', 'delivered'],
        is_active=True
    ).select_related('user')
    
    now = timezone.now()
    filter_label = "All Time"
    
    if filter_type == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_day)
        filter_label = "Today"
    elif filter_type == 'week':
        start_of_week = now - timedelta(days=7)
        orders = orders.filter(created_at__gte=start_of_week)
        filter_label = "Past 7 Days"
    elif filter_type == 'month':
        start_of_month = now - timedelta(days=30)
        orders = orders.filter(created_at__gte=start_of_month)
        filter_label = "Past 30 Days"
    elif filter_type == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            orders = orders.filter(created_at__range=[start, end])
            filter_label = f"{start_date} to {end_date}"
        except ValueError:
            pass
    
    # Calculate summary
    summary = orders.aggregate(
        total_orders=Count('id'),
        total_amount=Sum('net_amount'),
        total_discount=Sum('coupon_discount'),
        total_subtotal=Sum('subtotal')
    )
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=30,
        alignment=1  # Center
    )
    elements.append(Paragraph("Book Hive - Sales Report", title_style))
    elements.append(Paragraph(f"Period: {filter_label}", styles['Normal']))
    elements.append(Paragraph(f"Generated: {now.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Summary table
    summary_data = [
        ['Metric', 'Value'],
        ['Total Orders', str(summary['total_orders'] or 0)],
        ['Subtotal', f"{summary['total_subtotal'] or 0:.2f} Rs."],
        ['Total Discount', f"{summary['total_discount'] or 0:.2f} Rs."],
        ['Net Amount', f"{summary['total_amount'] or 0:.2f} Rs."],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Orders table
    elements.append(Paragraph("Order Details", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    orders_data = [['Order ID', 'Date', 'Customer', 'Subtotal', 'Discount', 'Net Amount']]
    
    for order in orders.order_by('-created_at')[:50]:  # Limit to 50 orders for PDF
        orders_data.append([
            order.order_id,
            order.created_at.strftime('%Y-%m-%d'),
            f"{order.user.first_name} {order.user.last_name}",
            f"{order.subtotal:.2f} Rs.",
            f"{order.coupon_discount:.2f} Rs.",
            f"{order.net_amount:.2f} Rs.",
        ])
    
    orders_table = Table(orders_data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
    orders_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(orders_table)
    
    # Build PDF
    doc.build(elements)
    
    # Return response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{filter_label.replace(" ", "_")}.pdf"'
    
    return response


def download_sales_report_excel(request):
    """Download sales report as Excel"""
    # Get same filters as main report
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Apply same filtering logic
    orders = Order.objects.filter(
        status__in=['pending', 'shipped', 'delivered'],
        is_active=True
    ).select_related('user')
    
    now = timezone.now()
    filter_label = "All Time"
    
    if filter_type == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_day)
        filter_label = "Today"
    elif filter_type == 'week':
        start_of_week = now - timedelta(days=7)
        orders = orders.filter(created_at__gte=start_of_week)
        filter_label = "Past 7 Days"
    elif filter_type == 'month':
        start_of_month = now - timedelta(days=30)
        orders = orders.filter(created_at__gte=start_of_month)
        filter_label = "Past 30 Days"
    elif filter_type == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            orders = orders.filter(created_at__range=[start, end])
            filter_label = f"{start_date} to {end_date}"
        except ValueError:
            pass
    
    # Calculate summary
    summary = orders.aggregate(
        total_orders=Count('id'),
        total_amount=Sum('net_amount'),
        total_discount=Sum('coupon_discount'),
        total_subtotal=Sum('subtotal')
    )
    
    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Report"
    
    # Styling
    header_fill = PatternFill(start_color="2563eb", end_color="2563eb", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Title
    ws['A1'] = "Book Hive - Sales Report"
    ws['A1'].font = Font(bold=True, size=16, color="2563eb")
    ws.merge_cells('A1:F1')
    
    ws['A2'] = f"Period: {filter_label}"
    ws['A3'] = f"Generated: {now.strftime('%Y-%m-%d %H:%M')}"
    
    # Summary section
    ws['A5'] = "Summary"
    ws['A5'].font = Font(bold=True, size=14)
    
    summary_headers = ['Metric', 'Value']
    for col, header in enumerate(summary_headers, 1):
        cell = ws.cell(row=6, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
    
    summary_data = [
        ['Total Orders', summary['total_orders'] or 0],
        ['Subtotal', f"₹{summary['total_subtotal'] or 0:.2f}"],
        ['Total Discount', f"₹{summary['total_discount'] or 0:.2f}"],
        ['Net Amount', f"₹{summary['total_amount'] or 0:.2f}"],
    ]
    
    for row_idx, (metric, value) in enumerate(summary_data, 7):
        ws.cell(row=row_idx, column=1, value=metric).border = border
        ws.cell(row=row_idx, column=2, value=value).border = border
    
    # Orders section
    ws['A12'] = "Order Details"
    ws['A12'].font = Font(bold=True, size=14)
    
    # Headers for orders
    headers = ['Order ID', 'Date', 'Customer', 'Email', 'Subtotal', 'Discount', 'Coupon Code', 'Net Amount', 'Status']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=13, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
    
    # Orders data
    row_num = 14
    for order in orders.order_by('-created_at'):
        ws.cell(row=row_num, column=1, value=order.order_id).border = border
        ws.cell(row=row_num, column=2, value=order.created_at.strftime('%Y-%m-%d %H:%M')).border = border
        ws.cell(row=row_num, column=3, value=f"{order.user.first_name} {order.user.last_name}").border = border
        ws.cell(row=row_num, column=4, value=order.user.email).border = border
        ws.cell(row=row_num, column=5, value=f"₹{order.subtotal:.2f}").border = border
        ws.cell(row=row_num, column=6, value=f"₹{order.coupon_discount:.2f}").border = border
        ws.cell(row=row_num, column=7, value=order.coupon_code or 'N/A').border = border
        ws.cell(row=row_num, column=8, value=f"₹{order.net_amount:.2f}").border = border
        ws.cell(row=row_num, column=9, value=order.status.title()).border = border
        row_num += 1
    
    # Adjust column widths
    for column_cells in ws.columns:
        max_length = 0
        column_letter = None
        
        for cell in column_cells:
            # Skip merged cells
            if hasattr(cell, 'column_letter'):
                column_letter = cell.column_letter
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
        
        if column_letter:
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 to avoid too wide columns
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="sales_report_{filter_label.replace(" ", "_")}.xlsx"'
    
    wb.save(response)
    return response