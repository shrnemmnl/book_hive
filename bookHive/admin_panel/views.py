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
from datetime import datetime
from django.utils import timezone
from django.db.models import F,Q
import base64
import re
from django.core.files.base import ContentFile






# Create your views here.
@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
def admin_signin(request):
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
    return render(request, 'admin/dashboard.html', {'heading': {'name': 'DASHBOARD'}})



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

    # Create Paginator object with 5 Genre per page
    paginator = Paginator(genre, 5)  
    page_number = request.GET.get('page') # Get the current page number from request
    print(page_number) 
    page_obj = paginator.get_page(page_number) # Get Genre for the requested page
    print(page_obj)

    if request.method == 'POST':
        genre_name = request.POST.get('genre', "").strip().lower()
        
        if Genre.objects.filter(genre_name=genre_name).exists():
            messages.error(request, 'Genre already exists.')
            return redirect('genre')  # Redirect to avoid form resubmission
        
        Genre.objects.create(genre_name=genre_name,is_active=True)
        messages.success(request, 'Genre added successfully.')
        return redirect('genre')  # Redirect after successful creation
    
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
        name=request.POST.get('genre', "").strip().lower()
        genre = Genre.objects.get(id=genre_id)

        if Genre.objects.filter(genre_name=name).exists():
            messages.error(request, 'Genre already exists.')
            return redirect('genre_edit', genre_id=genre.id)
        else:   
            genre.genre_name = name
            genre.save()
            messages.success(request, 'Genre Edited Successfully.')
            return redirect('genre')
 
    return render(request, 'admin/genre_edit.html', {'genres':genre})



def genre_search(request):
    
    
    search_query=request.POST.get('genre_search', "").strip()
    genre = Genre.objects.filter(genre_name__istartswith=search_query)

    # Create Paginator object with 5 Genre per page
    paginator = Paginator(genre, 5)  
    page_number = request.GET.get('page') # Get the current page number from request
    print(page_number) 
    page_obj = paginator.get_page(page_number)  # Get Genre for the requested page
    print(page_obj)
        
    
    return render(request, 'admin/genre.html', {'page_obj':page_obj})




def add_new_book(request):
    if request.method == 'POST':
        book_name = request.POST.get('book_name', "").strip()
        author = request.POST.get('author', "").strip()
        genre_id = request.POST.get('genre_id', "").strip()
        description = request.POST.get('description', "").strip()
        image = request.FILES.get('images')

        # Check if book already exists
        if Product.objects.filter(book_title=book_name).exists():
            messages.error(request, 'Book already exists.')
            return redirect('add_new_book')  

        # Ensure genre exists
        try:
            genre = Genre.objects.get(id=int(genre_id))
        except (Genre.DoesNotExist, ValueError):
            messages.error(request, 'Invalid genre selected.')
            return redirect('add_new_book')

        # Create new book
        new_product = Product.objects.create(
            book_title=book_name,
            author=author,
            genre=genre,  # Assign Genre object instead of ID
            is_active=True,
            description=description,
            image=image
        )
        
        messages.success(request, 'Book added successfully!')
        return render(request, 'admin/add_new_book.html', {'redirect': True, 'redirect_url': 'books'})  # Redirect to book list page

    # Fetch genres for dropdown
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

        # discount percentage validation
        if not discount_percentage.isdigit() and int(discount_percentage) <= 0:
            error['discount_percentage']="Discount percentage must be a positive integer."
            is_valid = False
        
        if image:
                valid_extensions = ["jpg", "jpeg", "png"]
                if not image.name.split(".")[-1].lower() in valid_extensions:
                    error['valid_image']="Please enter a valid image extension in jpg, jpeg and png formats."
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
            return messages.error(request,"Product not found")
        
        
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
    
    
    if request.method == 'POST':
        
        new_status = request.POST.get('status')
        
        valid_statuses = ['pending', 'shipped', 'delivered', 'cancelled', 'request to cancel','return approved','request to return']
        
        if new_status == 'delivered':
            order.is_paid = True


        elif new_status not in valid_statuses:
            messages.error(request, "Invalid status selected.")
            return redirect('admin_order_details', order_id=order.id)
        
        #If item cancelled stock needs to update.    
        elif new_status == 'cancelled' and not order.is_paid:

            #Stock need to update
            for item in order.order_items.all():
                variant = item.product_variant  
                variant.available_quantity = F('available_quantity') + item.quantity  # db math - more safe and concorency proof
                variant.save(update_fields=['available_quantity'])  #save only field available_quantity
            
        # Check if the item is being cancelled and the order is paid
        elif new_status in ['return approved','cancelled'] and order.is_paid:

            user = order.user

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