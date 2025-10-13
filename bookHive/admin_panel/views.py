from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from users.models import CustomUser,Order,OrderItem,Review, Wallet# Import your user model
from .models import Genre, Product, Variant, ProductImage
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache, cache_control
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.shortcuts import  get_object_or_404
from datetime import datetime
from django.utils import timezone
from django.db.models import F
import base64
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
        elif new_status == 'cancelled':

            #Stock need to update
            for item in order.order_items.all():
                variant = item.product_variant  
                variant.available_quantity = F('available_quantity') + item.quantity  # db math - more safe and concorency proof
                variant.save(update_fields=['available_quantity'])  #save only field available_quantity
            
        # Check if the item is being cancelled and the order is paid
        elif new_status == 'return approved' and order.is_paid:

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