
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from .models import CustomUser, Address, Cart, CartItem, Order, OrderItem, Review, Wishlist # Import your user model
from django.contrib.auth.hashers import make_password  # Hash password before saving
from django.views.decorators.cache import never_cache
from django.db.models import Min
from admin_panel.models import Product, Variant
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Min, Max
import json
import re
from .utils import send_verification_email, generate_otp
from django.core.paginator import Paginator
from django.db.models import Avg,Sum,F, ExpressionWrapper, DecimalField
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import logging
from django.db import transaction
from django.utils import timezone
import tempfile
import subprocess
import os
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)  # Create logger



def signup(request):
    errors = {}  # Dictionary to store field-specific errors

    if request.method == 'POST':
        firstName = request.POST.get('firstName', '').strip()
        lastName = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()
        confirmPassword = request.POST.get('confirmPassword', '').strip()

        # Validation patterns
        name_pattern = r'^[A-Za-z]+(?: [A-Za-z]+)?$'
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        mobile_pattern = r'^\d{10}$'  # Assuming 10-digit mobile number

        # Validate first name
        if not re.match(name_pattern, firstName):
            errors['firstName'] = "First name should contain only letters and at most one space."

        # Validate last name
        if not re.match(name_pattern, lastName):
            errors['lastName'] = "Last name should contain only letters and at most one space."

        # Validate email
        if not re.match(email_pattern, email):
            errors['email'] = "Invalid email format."

        # Validate mobile number
        if not re.match(mobile_pattern, mobile):
            errors['mobile'] = "Mobile number must be 10 digits."

        # Check if passwords match
        if password != confirmPassword:
            errors['password'] = "Passwords do not match."

        # Check if email is already registered
        if CustomUser.objects.filter(email=email).exists():
            errors['email'] = "Email is already registered."

        # Check if Mobile number is already registered
        if CustomUser.objects.filter(phone_no=mobile).exists():
            errors['mobile'] = "Phone is already registered. Plaese enter another contact number."

        if not errors: 
            request.session['userdata'] = {
                'first_name': firstName.capitalize(),
                'last_name': lastName.capitalize(),
                'email': email,
                'phone_no': mobile,
                'password': make_password(password),
            }
            otp = generate_otp()
            request.session['verification_email'] = email
            request.session['otp'] = otp

            send_verification_email(email, otp, type)

            # messages.success(request, f"Account created! A verification code has been sent to {email}.")

            # Show success message
            # messages.success(request, f"Welcome, {firstName} {lastName}! Your account is ready. Log in now.")

            # Redirect to login page after signup
            return redirect('verification')

    # Send errors dictionary to template
    return render(request, 'signup.html', {'errors': errors})


def loading_page(request):
    
    # Get filter parameters from request
    sort = request.GET.get('sort', 'featured')
    genres = request.GET.get('genres', '')
    min_price = request.GET.get('min_price', 0)
    max_price = request.GET.get('max_price', None)

    # Start with all active books
    books = Product.objects.annotate(min_price=Min(
        'variant__price')).filter(is_active=True)

    # Apply genre filter if specified
    if genres:
        genre_list = genres.split(',')
        print(genre_list)
        books = books.filter(genre__genre_name__in=genre_list)

    # Apply price range filter
    if min_price:
        try:
            min_price = float(min_price)
            books = books.filter(min_price__gte=min_price)
        except (ValueError, TypeError):
            pass

    if max_price:
        try:
            max_price = float(max_price)
            books = books.filter(min_price__lte=max_price)
        except (ValueError, TypeError):
            pass

    # Apply sorting
    if sort == 'lh':
        books = books.order_by('min_price')
    elif sort == 'hl':
        books = books.order_by('-min_price')
    elif sort == 'az':
        books = books.order_by('book_title')
    elif sort == 'za':
        books = books.order_by('-book_title')
    # else: featured, do nothing

    # 🚨 NOW do pagination — after all filters and sorting
    page = request.GET.get('page', 1)
    paginator = Paginator(books, 6)
    books = paginator.get_page(page)

    # Get all available genres
    categories = Product.objects.values_list(
        'genre__genre_name', flat=True).distinct()

    # Get price range
    price_range = {
        'min': Product.objects.aggregate(min_price=Min('variant__price'))['min_price'] or 0,
        'max': Product.objects.aggregate(max_price=Max('variant__price'))['max_price'] or 2000
    }

    context = {
        'books': books,
        'categories': categories,
        'price_range': price_range,
        'selected_sort': sort,
        'selected_genres': genres.split(',') if genres else [],
        'selected_min_price': min_price,
        'selected_max_price': max_price if max_price else price_range['max']
    }

    return render(request, 'index.html', context)


@never_cache
def user_login(request):

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        user_check = authenticate(email=email, password=password)

        if user_check:
            login(request, user_check)
            return redirect('home_page')  # Redirect normal users to user home
        else:
            messages.error(
                request, "Invalid email or password. Please try again.")

    return render(request, 'login/login.html')


@never_cache
def logout_user(request):

    logout(request)
    return redirect('loading_page')


@never_cache
def home_page(request):
    books = Product.objects.annotate(min_price=Min(
        'variant__price')).filter(is_active=True)
    print(books)

    return render(request, 'index.html', {'books': books})


def product_details(request, id):
    

    # Fetch the product
    try:
        book = get_object_or_404(Product, id=id, is_active=True)
    except:
        return redirect('loading_page')

    # get the possible variants from the respective product
    product_variants = Variant.objects.filter(product=book)

    # Check if ALL variants have zero quantity
    is_sold_out = not product_variants.filter(
        available_quantity__gt=0).exists()

    # Get related books in the same genre, exclude current one
    related_books = Product.objects.filter(
        genre=book.genre,
        is_active=True
    ).exclude(id=book.id)[:4]  # Only 4 suggestions

    if request.method == "POST" and request.user.is_authenticated:
        # user_id = request.user.id
        rating = request.POST.get('overallRating', '').strip()
        comments = request.POST.get('comment', '').strip()

        review = Review.objects.create(
            user=request.user,
            product=book,
            rating=int(rating),
            comments=comments,
            status='pending',
        )

        messages.success(request, "Your Review is successfully submitted.")

    # Get all variants for the given product
    variants = Variant.objects.filter(
        product=book).prefetch_related('productimage_set')

    # Use the first variant as default
    default_variant = variants.first()

    if book.is_offer and default_variant:
        discount_price = round(
            default_variant.price - (default_variant.price * book.discount_percentage / 100))
    else:
        discount_price = default_variant.price

    # fetches the entire reviews related to the particular book and reviewed user.
    review_content = Review.objects.filter(product=book).select_related('user')
    # for i in review_content:
    #     print('review content ',i.rating)
    average_rating = review_content.aggregate(Avg('rating'))['rating__avg']
    # book_user = CustomUser.objects.filter(review__product=book).distinct()
    # review_count=book.review.count()
    # print(review_count)
    # try:
    #     user_rating=Review.objects.get(user=book_user,product=book).anno #review count for a particular book
    # except Review.DoesNotExist:
    #     user_rating=None
    # print(user_rating)
    # average_rating = Review.objects.filter(product=book).aggregate(Avg('rating'))['rating__avg'] #rounded average rating figure of particular book
    # print(average_rating)
    context = {
        'book': book,  # specific product details which variants included
        'discount_price': discount_price,
        'variants': variants,  # all the variant for the specific product
        'default_variant': default_variant,  # Use the first variant as default
        'review_content': review_content,  # fetches the entire reviews
        'review_count': review_content.count(),  # review count for a particular book
        'average_rating': average_rating,
        'average_rating_int': int(round(average_rating)) if average_rating is not None else 0,
        'is_sold_out': is_sold_out,
        'related_books': related_books,

    }

    return render(request, 'user/product_details.html', context)


def get_variant_details(request, variant_id):
    """API endpoint to get variant details via AJAX"""
    variant = get_object_or_404(Variant, id=variant_id)
    variant_image = variant.productimage_set.first()

    # Prepare response data
    data = {
        'id': variant.id,
        'price': variant.price,
        'available_quantity': variant.available_quantity,
        'published_date': variant.published_date.strftime('%d-%m-%Y'),
        'publisher': variant.publisher,
        'page': variant.page,
        'language': variant.language,
        'images': {
            'image1': variant_image.image1.url if variant_image else '',
            'image2': variant_image.image2.url if variant_image else '',
            'image3': variant_image.image3.url if variant_image else '',
        }
    }

    return JsonResponse(data)


def search_book(request):
    # print('hellooooooooooooooooooooooooooooooo')
    if request.method == 'GET':
        search_string = request.GET.get('search_string')
        print(search_string)
        books = Product.objects.annotate(min_price=Min('variant__price')).filter(
            is_active=True, book_title__istartswith=search_string)

        return render(request, 'index.html', {'books': books})


def user_profile(request):
    has_error = False
    user = request.user

    if request.method == 'POST':

        form_type = request.POST.get('form_type')

        if form_type == 'personal_info':
            profile_pic = request.FILES.get('profile_pic')
            fname = request.POST.get('firstName', '').strip()
            lname = request.POST.get('lastName', '').strip()
            # email = request.POST.get('email', '').strip()
            phone_no = request.POST.get('phone_no', '').strip()

        # print(email)
        # Validation patterns

            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            mobile_pattern = r'^\d{10}$'  # Assuming 10-digit mobile number

        # Validate email
        # if not re.match(email_pattern, email):
        #     messages.error(
        #         request, "Oops! That doesn't look like a valid email. Try again?")
        #     has_error = True

        # Validate mobile number
            if not re.match(mobile_pattern, phone_no):
                messages.error(request, "Please enter a valid mobile number.")
                has_error = True


            if not has_error:
                user = CustomUser.objects.get(id=request.user.id)
                user.first_name = fname
                user.last_name = lname
                # user.email = email
                user.phone_no = phone_no

                if profile_pic:  # Only overwrite if user uploaded a new file
                    user.profile_pic = profile_pic

                user.save()
                messages.success(request, "Profile details updated successfully.")
                return redirect('user_profile')
        elif form_type == 'password_change':
            current_pwd = request.POST.get('current_password')
            new_pwd = request.POST.get('new_password')
            confirm_pwd = request.POST.get('confirm_password')

            if not user.check_password(current_pwd):
                messages.error(request, "Current password is incorrect.")
            elif new_pwd != confirm_pwd:
                messages.error(request, "New passwords do not match.")
            else:
                user.set_password(new_pwd)
                user.save()
                messages.success(request, "Password changed successfully!")
                update_session_auth_hash(request, user)  # Keep user logged in


    return render(request, 'user/user_profile.html' )


def user_address(request):
    address = Address.objects.filter(user=request.user, is_active=True).order_by('-is_default')
    logger.info(f"New address is created: {address}")
    has_error = False

    if request.method == 'POST':

        
        address_type = request.POST.get('address_type', '').strip().capitalize()
        street = request.POST.get('street', '').strip().capitalize()
        phone = request.POST.get('phone', '').strip()
        landmark = request.POST.get('landmark', '').strip().capitalize()
        city = request.POST.get('city', '').strip().capitalize()
        state = request.POST.get('state', '').strip().capitalize()
        postal_code = request.POST.get('pincode', '').strip()

        phone_pattern = r'^\d{10}$'
        pincode_pattern = r'^\d{6}$' 

        if not re.match(phone_pattern, phone):
                messages.error(request, "Please enter a valid mobile number.")
                has_error = True

        if not re.match(pincode_pattern, postal_code):
                messages.error(request, "Please enter a valid 6-digit postal code.")
                has_error = True

        if Address.objects.filter(user=request.user, is_active=True).exists():
            default = False
        else:
            default = True

        if not has_error:       
            Address.objects.create(
                user=request.user,
                address_type = address_type,
                street = street,
                phone = phone,
                landmark = landmark,
                city = city,
                state = state,
                postal_code = postal_code,
                is_default = default,
            )
            messages.success(request, "Your new delivery address has been added successfully.")
            return redirect('user_address')  # Or wherever you want to redirect


    return render(request, 'user/user_address.html', {'addresss': address})

def default_address(request, address_id):
    try:
        with transaction.atomic():
            
            current_default = Address.objects.get(is_default=True, user=request.user)
            current_default.is_default = False
            current_default.save()

            d_address = Address.objects.get(id=address_id, user=request.user)
            d_address.is_default = True
            d_address.save()

        messages.success(request, f'{d_address.address_type} is now set as your default address.')
    except Address.DoesNotExist:
        messages.error(request, "Address not found or already unset.")
    except Exception as e:
        messages.error(request, f"Something went wrong: {str(e)}")

    return redirect('user_address')



def user_cart(request):
    # Get or create the cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)
    # logger.debug(f"this is the cart created- {cart}")
    

    # Get all active cart items linked to this cart
    cart_item = CartItem.objects.filter(cart=cart, product_variant__is_active=True)

    count = cart_item.count()
    print("count -",count)
    logger.debug(f"This is the cart created- {cart_item}")
    # Calculate subtotal
    subtotal = sum(item.get_total_price() for item in cart_item)

    # Render the cart page
    return render(request, 'user/user_cart.html', {
        'cart_item': cart_item,
        'subtotal': subtotal,
        'count' : count,
    })




def user_order(request):

    order_details = Order.objects.prefetch_related('order_items').filter(user=request.user).order_by('-created_at')
    

    return render(request, 'user/user_order.html', {'order_details': order_details})




@login_required
def order_search(request):

    # Get search parameters
    search_query = request.GET.get('search', '')
    period_filter = request.GET.get('period', 'all')
    status_filter = request.GET.get('status', '')

    # Start with all orders for the current user
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Apply time period filter
    if period_filter != 'all':
        if period_filter == '30days':
            start_date = timezone.now().date() - timedelta(days=30)
            orders = orders.filter(created_at__date__gte=start_date)
        elif period_filter == '3months':
            start_date = timezone.now().date() - timedelta(days=90)
            orders = orders.filter(created_at__date__gte=start_date)
        elif period_filter == '6months':
            start_date = timezone.now().date() - timedelta(days=180)
            orders = orders.filter(created_at__date__gte=start_date)
        elif period_filter == '2025':
            start_date = datetime(2025, 1, 1).date()
            end_date = datetime(2025, 12, 31).date()
            orders = orders.filter(created_at__date__range=(start_date, end_date))
        elif period_filter == '2024':
            start_date = datetime(2024, 1, 1).date()
            end_date = datetime(2024, 12, 31).date()
            orders = orders.filter(created_at__date__range=(start_date, end_date))

    # Apply search filter for order_id
    if search_query:
        orders = orders.filter(order_id__icontains=search_query)

    # Apply status filter
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Count the number of orders
    order_count = orders.count()

    context = {
        'order_details': orders,
        'order_count': order_count
    }


    return render(request, 'user/user_order.html', context)


def cancel_order(request, order_id):

    if request.method == 'POST':

        reason=request.POST.get('reason')

        try:

            order = Order.objects.get(id=order_id)
            order.status = 'request to cancel'
            order.is_active = False
            order.cancel_reason = reason
            order.save()
            
            messages.info(request, f"Your order id - {order.order_id} is requested to cancel." )
            return redirect('user_order')

        except Exception as e:

            messages.error(request, f"Error - {e}")


    return render(request, 'user/user_order.html',)
        

    


def user_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)


    return render(request, 'user/user_wishlist.html', {'wishlist_items':wishlist_items })



def wishlist_toggle(request):
    if request.method == "POST":
        variant_id = request.POST.get("product_id")  # this is Variant ID
        print(variant_id)
        variant = get_object_or_404(Variant, id=variant_id)

        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, variant=variant)

        if not created:
            wishlist_item.delete()
            return JsonResponse({"removed": True})
        else:
            return JsonResponse({"added": True})
    return JsonResponse({"error": "Invalid request"}, status=400)



def user_wallet(request):

    return render(request, 'user/user_wallet.html')


def user_cust_care(request):

    return render(request, 'user/user_cust_care.html')


def calculate_total(cart_items):
    return sum(item.product_variant.price * item.quantity for item in cart_items)



@csrf_exempt  # Use only if you don't have {% csrf_token %}, otherwise REMOVE this
def checkoutpage(request):
    

    if request.method == 'POST':
        
        address_id = request.POST.get('shippingAddress')
        payment_method = request.POST.get('payment_method')  # Use if needed later

        print('address_id -', address_id)
        print('payment_method -', payment_method)

        # ✅ Check for valid address
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Invalid address selected.")
            return redirect('checkoutpage')

        # ✅ Get latest active cart
        try:
            cart = Cart.objects.filter(user=request.user).latest('created_at')
        except Cart.DoesNotExist:
            messages.error(request, "No cart found.")
            return redirect('cart')

        cart_items = cart.cart_items.all()
        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('cart')

        # ✅ Calculate net amount
        net_amount = calculate_total(cart_items)

        try:

            with transaction.atomic():
                # ✅ Create Order
                order = Order.objects.create(
            user=request.user,
            address=address,
            net_amount=net_amount,
            status='pending',
            order_date=timezone.now()
        )
            print('order -', order)
        # ✅ Add items to order
            for item in cart_items:
                OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity,
                total_amount=item.product_variant.price * item.quantity,
                image_url=item.product_variant.image_url if hasattr(item.product_variant, 'image_url') else None,
                
            )

        # ✅ Clear cart
            cart.delete()

        # ✅ Redirect to order confirmation page with order_id
            return redirect('order_confirm', id=order.id)

        except Exception as e:

            messages.error(request, f"Something went wrong: {str(e)}")
    
    # 🟡 Handle GET request
    try:
        cart = Cart.objects.filter(user=request.user).latest('created_at')
        cart_items = cart.cart_items.all()

    except Cart.DoesNotExist:

        cart_items = []

    subtotal = calculate_total(cart_items)
    shipping = 0  # You can make this dynamic later
    total = subtotal + shipping

    addresses = Address.objects.filter(user=request.user, is_active=True).order_by('-is_default')

    return render(request, 'user/checkoutpage.html', {
        'addresses': addresses,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total': total
    })



def order_confirm(request, id):

    try:

        order = Order.objects.get(id = id)
        order_items = OrderItem.objects.filter(order = order)

    except Exception as e:

        messages.error(request, f"Something went wrong: {str(e)}")

    return render(request, 'user/order_confirm.html', {'order' : order, 'order_items' : order_items})



@require_POST
def add_to_cart(request, id):

    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        quantity = data.get('quantity')
        print(f"data:{data}, vaiant id:{variant_id}, quantity: {quantity}  {type(quantity)}")

        # variant = get_object_or_404(Variant, id=variant_id)
        # print(variant)
        # Try to find an existing cart for the current user.
        try:
            cart = Cart.objects.get(user=request.user)
            created = False
        except Cart.DoesNotExist:
            cart = Cart.objects.create(user=request.user)
            created = True
            

        # get the actual Variant object
        variant = get_object_or_404(Variant, id=variant_id)
        # Try to find an existing cart item
        try:
            cart_item = CartItem.objects.get(cart=cart, product_variant=variant)
            cart_item.quantity += quantity  # if you want to update quantity
            cart_item.save()
            created = False

        except CartItem.DoesNotExist:
            # If not found, create a new one
            cart_item = CartItem.objects.create(
                cart=cart,
                product_variant=variant,
                quantity=quantity,
            )
            created = True
        print(cart_item)
        
        # You can now process and return success
        return JsonResponse({'success': True, 'redirect_url': '/user/cart/'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})


@require_POST
@csrf_exempt  # NOT safe in production unless token is handled
def update_cart_quantity(request):
    item_id = request.POST.get('item_id')
    action = request.POST.get('action')  # 'increase' or 'decrease'

    try:
        cart_item = CartItem.objects.get(id=item_id)

        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1
        
        cart_item.save()

        # Total price for this item
        item_total_price = cart_item.get_total_price()

        # Optional: Cart total for all items of this user
        cart_total = CartItem.objects.filter(cart=cart_item.cart).annotate(total_price=ExpressionWrapper(
            F('quantity') * F('product_variant__price'),output_field=DecimalField())).aggregate(
                total=Sum('total_price'))['total']
        
        # logger.debug(f"This is the cart item cart - {cart_item.cart}")

        cart_items = CartItem.objects.filter(cart=cart_item.cart)
        subtotal = sum(item.get_total_price() for item in cart_items)

        return JsonResponse({
            'success': True,
            'new_quantity': cart_item.quantity,
            'item_total_price': item_total_price,
            'cart_total': cart_total,
            'subtotal' : subtotal,
        })

    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})


@require_POST
@csrf_exempt
def delete_cart_item(request):
    item_id = request.POST.get('item_id')

    try:
        cart_item = CartItem.objects.get(id=item_id)
        cart = cart_item.cart
        cart_item.delete()

        cart_items = CartItem.objects.filter(cart=cart)  # fetching the remaining cart_items
        count = cart_items.count()
        print("count -",count)
        cart_total = sum(item.get_total_price() for item in cart_items)
        
        return JsonResponse({
            'success': True,
            'cart_total': cart_total,
            'count' : count,
        })

    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})

@never_cache
@require_POST
def verification(request):

    if request.method == 'POST':

        action = request.POST.get('action')
        if action == 'verify':
            entered_otp = ''.join([
                request.POST.get('digit1', ''),
                request.POST.get('digit2', ''),
                request.POST.get('digit3', ''),
                request.POST.get('digit4', ''),
                request.POST.get('digit5', ''),
                request.POST.get('digit6', ''),
            ])

            session_otp = request.session.get('otp')
            email = request.session.get('verification_email')

            if entered_otp == session_otp:
                # You can mark user as verified here (maybe add `is_verified` field to model)
                user_session_data = request.session.get('userdata')
                try:
                        user = CustomUser.objects.create(
                    first_name=user_session_data['first_name'],
                    last_name=user_session_data['last_name'],
                    email=user_session_data['email'],
                    phone_no=user_session_data['phone_no'],
                    password=user_session_data['password']

                )
                        
                except Exception as e:
                    messages.error(request, f'Error - {e}')
                    return redirect('signup')

                # Clear session after creating
                del request.session['userdata']
                del request.session['otp']
                del request.session['verification_email']

                messages.success(
                    request, "Email verified and account created! You can now log in.")
                return redirect('login')  # or home page
            else:
                messages.error(request, "Invalid OTP. Try again.")
                return redirect('signup')

        elif action == 'resend':
            new_otp = generate_otp()
            request.session['otp'] = new_otp

            email = request.session.get('verification_email')
            if email:
                send_verification_email(email, new_otp, 'signup')
                messages.info(
                    request, "A new OTP has been sent to your email.")
            else:
                messages.error(
                    request, "Something went wrong. Email not found in session.")
                

    return render(request, 'login/verification.html')


def fg_verification(request):

    if request.method == 'POST':

        email = request.POST.get('email', '').strip()

        if CustomUser.objects.filter(email=email).exists():
            request.session['verification_email'] = email
            otp_generate_pls = generate_otp()
            request.session['otp_generate_pls'] = otp_generate_pls

            send_verification_email(email, otp_generate_pls, 'password')
            return redirect('otp_page_fg')
        else:
            messages.error(
                request, "Email not found or an error occurred. Please check the email you entered. If you haven’t signed up yet, please register first.")
            redirect('fg_verification')

    return render(request, 'login/fg_verification.html')


def otp_page_fg(request):

    if request.method == 'POST':

        action = request.POST.get('action')
        print('action', action)
        if action == 'verify':
            entered_otp = request.POST.get('digit', '')

            session_otp = request.session['otp_generate_pls']
            print('hirrrrrrrrr')

            if entered_otp == session_otp:
                del request.session['otp_generate_pls']
                print('hi')
                # messages.success(request, "Email verified! You can now change the password.")
                return redirect('password_change')
                # messages.error(request, "Something went wrong.")

    return render(request, 'login/otp_page_fg.html')


def password_change(request):
    print('hi')
    test = request.session['verification_email']
    user = CustomUser.objects.get(email=test)

    if request.method == 'POST':

        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        print(new_password, confirm_password)

        # Check if passwords match
        if new_password != confirm_password:
            messages.error(
                request, "Passwords do not match. Please re-enter the password again.")
        else:
            user.password = make_password(new_password)  # new password saved.
            user.save()
            print(user.password)
            messages.success(request, "Your Password changed sucessfully.")
            return render(request, 'login/password_change.html', {'redirect_to_login': True, 'redirect_url': 'login'})

    return render(request, 'login/password_change.html')


def address_edit(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    has_error = False

    if request.method == 'POST':
        address.address_type = request.POST.get('address_type')
        address.street = request.POST.get('street')
        address.phone = request.POST.get('phone')
        address.landmark = request.POST.get('landmark')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')

        mobile_pattern = r'^\d{10}$'  # Assuming 10-digit mobile number
        pincode_pattern = r'^[1-9][0-9]{5}$' 

        if not re.match(mobile_pattern, address.phone):
                messages.error(request, "Please enter a valid mobile number.")
                has_error = True

        if not re.match(pincode_pattern, address.postal_code):
                messages.error(request, "Please enter a valid 6-digit postal code.")
                has_error = True

        if not has_error:       
            address.save()
            messages.success(request, "Your new delivery address has been Edited successfully.")
            return redirect('user_address')  # Or wherever you want to redirect

    return render(request, 'user/address_edit.html', {'address': address})


def address_delete(request, address_id):

    status = Address.objects.get(id=address_id)
    status.is_active = not status.is_active
    status.save()
    return redirect('user_address')


def change_variant(request, book_id):
    try:
        book = get_object_or_404(Product, id=book_id, is_active=True)
        data = json.loads(request.body)
        variant_id = data.get('variant_id')

        variant = Variant.objects.prefetch_related('productimage_set').get(id=variant_id)

        # Get images from related model
        images = []
        for img in variant.productimage_set.all():
            if img.image1:
                images.append(img.image1.url)
            if img.image2:
                images.append(img.image2.url)
            if img.image3:
                images.append(img.image3.url)
        print(images)
        if book.is_offer and variant:
            discount_price = round(
            variant.price - (variant.price * book.discount_percentage / 100))
            is_offer=True
        else:
            discount_price = variant.price
            is_offer=False
        # Format the variant data
        variant_data = {
            'id': variant.id,
            'language': variant.language,
            'publisher': variant.publisher,
            'published_date': variant.published_date.strftime('%d %b %Y') if variant.published_date else '',
            'page': variant.page,
            'price': discount_price,
            'original_price': variant.price,
            'discount_percentage': book.discount_percentage or None,
            'available_quantity': variant.available_quantity,
            'images': images,
            'is_offer':  is_offer,
        }
        print(variant_data)
        return JsonResponse({'success': True, 'variant': variant_data})

    except Variant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Variant not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



def download_invoice(request, id):
    order = Order.objects.get(id=id)
    order_items = order.order_items.all()  
    template_path = 'invoices/invoice_template.html'
    context = {
        'order': order,
        'order_items': order_items,
    }

    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors with PDF generation <pre>' + html + '</pre>')
    return response








