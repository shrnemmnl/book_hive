from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from users.models import CustomUser,Order,OrderItem # Import your user model
from .models import Genre, Product, Variant, ProductImage
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache, cache_control
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse




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

        book = Product.objects.get(id=book_id)
        book.book_title = book_name
        book.genre =Genre.objects.get(id=genre_id) 
        print(genre_id)
        book.author = author
        if image:
            book.image = image
        book.description = description
       
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
        variant_id=request.POST.get('variant_id', "").strip()
        variant = Variant.objects.get(id=variant_id)
        
        
    return render(request, 'admin/variant_edit.html', {'variants':variant})



def variant_edit_post(request):
    if request.method == 'POST':
        variant_id=request.POST.get('variant_id', "").strip()
        publisher = request.POST.get('publisher', "").strip()
        publish_date = request.POST.get('publish_date', "").strip()
        price = request.POST.get('price', "").strip()
        available_quantity=request.POST.get('available_quantity', "").strip()
        language=request.POST.get('language', "").strip()
        image = request.FILES.get('image')

        variant = Variant.objects.get(id=variant_id)
        variant.publisher = publisher
        
        # print(genre_id)
        # variant.publisher = publisher
        # if image:
        #     variant.image = image
        # variant.description = description
       
        variant.save()
        messages.success(request, 'Updated successfully!')

        return render(request, 'admin/variant_edit.html', {'redirect': True, 'redirect_url': 'view_variant'})  # Send flag to template

    return render(request, 'admin/variant_edit.html',{'variants':variant})


def admin_order_details(request, order):

    return render(request, "admin/admin_order_details.html")