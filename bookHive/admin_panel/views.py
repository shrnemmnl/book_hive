from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from users.models import CustomUser,Order,OrderItem,Review # Import your user model
from .models import Genre, Product, Variant, ProductImage
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache, cache_control
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.shortcuts import  get_object_or_404
from datetime import datetime, timezone


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

    return render(request, 'admin/books.html', {"books":books})



@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required(login_url='admin_signin')  
def admin_order(request):

    order_details=Order.objects.prefetch_related('order_items').order_by('-created_at')

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
    genre= Genre.objects.all().order_by('is_active')

    # Create Paginator object with 5 Genre per page
    paginator = Paginator(genre, 5)  
    page_number = request.GET.get('page') # Get the current page number from request
    print(page_number) 
    page_obj = paginator.get_page(page_number) # Get Genre for the requested page
    print(page_obj)

    if request.method == 'POST':
        genre_name = request.POST.get('genre', "").strip()
        
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




def genre_edit(request):
    if request.method == 'POST':
        genre_id=request.POST.get('genre_id', "").strip()
        genre = Genre.objects.get(id=genre_id)
        
        
    return render(request, 'admin/genre_edit.html', {'genres':genre})




def genre_edit_post(request):
    if request.method == 'POST':
        genre_id=request.POST.get('genre_id', "").strip()
        name=request.POST.get('genre', "").strip()

        genre = Genre.objects.get(id=genre_id)
        genre.genre_name = name
        genre.save()
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



def book_edit(request):
    
    book_id=request.POST.get('book_id', "").strip()
    book = Product.objects.get(id=book_id)
    genres = Genre.objects.all()
    return render(request, 'admin/book_edit.html',{'book':book,'genres':genres })



def book_edit_post(request):
    if request.method == 'POST':
        book_id=request.POST.get('book_id', "").strip()
        book_name = request.POST.get('book_title', "").strip()
        author = request.POST.get('book_author', "").strip()
        description = request.POST.get('book_description', "").strip()
        genre_id=request.POST.get('genre_id', "").strip()
        image = request.FILES.get('image')
        # Offer Fields
        is_offer = request.POST.get('is_offer') == 'on'
        offer_title = request.POST.get('offer_title', "").strip()
        discount_percentage = request.POST.get('discount_percentage', 0)

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
        messages.success(request, 'Updated successfully!')

        return render(request, 'admin/book_edit.html', {'redirect': True, 'redirect_url': 'books'})  # Send flag to template

    return render(request, 'admin/book_edit.html',{'book':book})



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



def variant_edit(request):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id', "").strip()
        variant = get_object_or_404(Variant, id=variant_id)
        
        images = variant.productimage_set.first()  # set of 3 images per variant

        return render(request, 'admin/variant_edit.html', {
            'variant': variant,
            'images': images
        })

    return render(request, 'admin/variant_edit.html')  



def variant_edit_post(request):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id', "").strip()
        publisher = request.POST.get('publisher', "").strip()
        published_date = request.POST.get('published_date', "").strip()
        price = request.POST.get('price', "").strip()
        page = request.POST.get('page', "").strip()
        available_quantity = request.POST.get('stock', "").strip()
        language = request.POST.get('language', "").strip()

        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')

        # Get Variant
        variant = get_object_or_404(Variant, id=variant_id)
        variant.publisher = publisher

        # Convert and assign date
        try:
            variant.published_date = datetime.strptime(published_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "⚠ Invalid date format.")
            return render(request, 'admin/variant_edit.html', {'variant': variant})

        # Other fields
        variant.price = int(price)
        variant.page = int(page)
        variant.available_quantity = int(available_quantity)
        variant.language = language
        variant.save()

        # Handle ProductImage
        product_image, created = ProductImage.objects.get_or_create(variant=variant)

        if image1:
            product_image.image1 = image1
        if image2:
            product_image.image2 = image2
        if image3:
            product_image.image3 = image3

        product_image.save()

        # messages.success(request, '✅ Variant and images updated successfully!')

        return redirect('books')

    return render(request, 'admin/variant_edit.html')


@login_required
def admin_order_details(request, order_id):

    order = get_object_or_404(Order, id=order_id)
    
    
    if request.method == 'POST':
        # Handle payment status update
        # if 'is_paid' in request.POST:
        #     is_paid = request.POST.get('is_paid') == 'true'
        #     order.is_paid = is_paid
        #     order.save()
        #     messages.success(request, f"Payment status updated to {'Paid' if is_paid else 'Unpaid'}.")
        #     return redirect('admin_order_details', order_id=order.id)

        # Handle order item status update
        # item_id = request.POST.get('item_id')
        new_status = request.POST.get('status')
        print(new_status)
        valid_statuses = ['pending', 'shipped', 'delivered', 'cancelled', 'request to cancel']
        
        if new_status == 'delivered':
            order.is_paid = True


        if new_status not in valid_statuses:
            messages.error(request, "Invalid status selected.")
            return redirect('admin_order_details', order_id=order.id)
            
        # order_item = get_object_or_404(OrderItem, id=item_id, order=order)

        
            
        # Check if the item is being cancelled and the order is paid
        if new_status == 'request to cancel' and order.is_paid:
            user = order.user
            refund_amount = order.order_items.total_amount  # Changed from net_amount to total_amount
            user.wallet_amount += refund_amount
            user.save()
            messages.success(request, f"Refunded ₹{refund_amount:.2f} to user {user.email}'s wallet.")
            
            order.status = 'cancelled'
            # order_item.updated_at = timezone.now()
            order.order_items.save()
            messages.success(request, f"Status for item '{ order.order_items.product_variant.product.book_title }' updated to {order.status}.")
            return redirect('admin_order_details', order_id=order.id)

        order.status = new_status
        order.save()

    context = {
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