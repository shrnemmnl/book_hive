
from datetime import timedelta
import datetime as dt
import random
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from django.urls import reverse
# Import your user model
from .models import CustomUser, Address, Cart, CartItem, Order, OrderItem, Review, Wishlist, Wallet
from django.contrib.auth.hashers import make_password  # Hash password before saving
from django.views.decorators.cache import never_cache, cache_control
from django.db.models import Min
from admin_panel.models import Product, Variant, Coupon
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Min, Max
import json
import re
from .utils import send_verification_email, generate_otp
from django.core.paginator import Paginator
from django.db.models import Avg, Sum, F, ExpressionWrapper, DecimalField
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
import razorpay


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)  # Create logger


def signup(request):

    if request.user.is_authenticated:
        return redirect('loading_page')  # already logged in → go to home
    errors = {}  # Dictionary to store field-specific errors

    if request.method == 'POST':
        firstName = request.POST.get('firstName', '').strip()
        lastName = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()
        confirmPassword = request.POST.get('confirmPassword', '').strip()
        referral_code = request.POST.get('referral_code', '').strip().upper()

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
        
        # Validate referral code if provided
        referrer = None
        if referral_code:
            try:
                referrer = CustomUser.objects.get(referral_code=referral_code)
            except CustomUser.DoesNotExist:
                errors['referral_code'] = "Invalid referral code."

        if not errors:
            request.session['userdata'] = {
                'first_name': firstName.capitalize(),
                'last_name': lastName.capitalize(),
                'email': email,
                'phone_no': mobile,
                'password': make_password(password),
                'referrer_id': referrer.id if referrer else None,
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

    request.session['address_update'] = False
    # logger.debug(f"address flag : {address_update}")

    # Start with all active books with min price in its variant
    books = Product.objects.annotate(min_price=Min(
        'variant__price')).filter(is_active=True)

    # Get filter parameters from request
    sort = request.GET.get('sort', 'featured')
    genres = request.GET.get('genres', 'allgenres')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Apply genre filter if specified
    if genres and genres != 'allgenres':
        genre_list = genres.split(',')
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

    # Pagination
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
        'selected_genres': genres.split(',') if genres and genres != 'allgenres' else [],
        'selected_min_price': min_price if min_price else price_range['min'],
        'selected_max_price': max_price if max_price else price_range['max']
    }

    return render(request, 'index.html', context)


@never_cache
def user_login(request):

    errors = {}
    found_error = False
    user_check = None

    if request.user.is_authenticated:
        return redirect('loading_page')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        # Backend validation
        if not email:
            errors['email'] = "Email is required."
            print("email")
            found_error = True

        if not re.match(email_regex, email):
            errors['email'] = "Please enter a valid email address."
            print("email1")
            found_error = True

        if not password:
            errors['password'] = "Password is required."
            print("password")
            found_error = True

        if not found_error:
            user_check = authenticate(email=email, password=password)

        if user_check:
            login(request, user_check)
            messages.success(request, "Login successful.")
            # Redirect normal users to user home
            return redirect('loading_page')
        else:
            messages.error(
                request, "Authentication Error, Check the Credentials and Try Again.")

    return render(request, 'login/login.html', {'errors': errors})


@never_cache
def logout_user(request):

    logout(request)
    return redirect('loading_page')


def product_details(request, id):
    # Fetch the product
    try:
        book = get_object_or_404(Product, id=id, is_active=True)
    except:
        messages.error(request, "Book is no longer available.")
        return redirect('loading_page')

    # get the possible variants from the respective product
    # product_variants = Variant.objects.filter(product=book)
    

    


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
        )

        messages.success(request, "Your Review is successfully submitted.")

    # Get all variants for the given product
    variants = Variant.objects.filter(product=book).prefetch_related('productimage_set')

    # Use the first variant as default
    default_variant = variants.first()

    # Check if ALL variants have zero quantity
    is_sold_out = default_variant.available_quantity
    print("is variant sold out: ",is_sold_out)

    # Use the best discount from product or genre
    if default_variant:
        discount_price = round(book.get_discounted_price(default_variant.price))
    else:
        discount_price = 0

    # fetches the entire reviews related to the particular book and reviewed user.
    review_content = Review.objects.filter(product=book).select_related('user')
    # for i in review_content:
    #     print('review content ',i.rating)
    average_rating = review_content.aggregate(Avg('rating'))['rating__avg']
    print(f"here is the {default_variant.price} and its quantity {default_variant.available_quantity}")

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
    product = variant.product

    # Calculate best discount
    has_active_offer = product.has_active_offer()
    best_discount_percentage = product.get_best_discount_percentage()
    discounted_price = round(product.get_discounted_price(variant.price))
    offer_title = product.get_active_offer_title()

    # Prepare response data
    data = {
        'id': variant.id,
        'price': variant.price,
        'original_price': variant.price,
        'discounted_price': discounted_price,
        'has_active_offer': has_active_offer,
        'best_discount_percentage': best_discount_percentage,
        'offer_title': offer_title,
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

    search_string = request.GET.get('search_string', "").strip()
    # Start with all active books with min price in its variant
    books = Product.objects.annotate(min_price=Min('variant__price')).filter(
        is_active=True, book_title__istartswith=search_string)

    # Get filter parameters from request
    sort = request.GET.get('sort', 'featured')
    genres = request.GET.get('genres', 'allgenres')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Apply genre filter if specified
    if genres and genres != 'allgenres':
        genre_list = genres.split(',')
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

    # Pagination
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
        'selected_genres': genres.split(',') if genres and genres != 'allgenres' else [],
        'selected_min_price': min_price if min_price else price_range['min'],
        'selected_max_price': max_price if max_price else price_range['max']
    }

    return render(request, 'index.html', context)


@login_required
def user_profile(request):
    has_error = False
    user = request.user
    error = {}

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
            name_pattern = r"^[A-Za-z\s'-]+$"
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            mobile_pattern = r'^\d{10}$'  # Assuming 10-digit mobile number

        # Validate email
        # if not re.match(email_pattern, email):
        #     messages.error(
        #         request, "Oops! That doesn't look like a valid email. Try again?")
        #     has_error = True

            if not re.match(name_pattern, fname):
                error['fname_pattern'] = "First name can only contain letters, spaces, hyphens, and apostrophes."
                has_error = True

            if not re.match(name_pattern, lname):
                error['lname_pattern'] = "last name can only contain letters, spaces, hyphens, and apostrophes."
                has_error = True

            if len(fname) < 2 or len(fname) > 50:
                error['pattern_length'] = "First name must be between 2 and 50 characters long."
                has_error = True

            if not re.match(mobile_pattern, phone_no):
                error['mobile_pattern'] = "Please enter a valid mobile number."
                has_error = True

            if profile_pic:
                valid_extensions = ["jpg", "jpeg", "png"]
                if not profile_pic.name.split(".")[-1].lower() in valid_extensions:
                    error['valid_image'] = "Please enter a valid image extension in jpg, jpeg and png formats."

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
                messages.success(
                    request, "Profile details updated successfully.")
                return redirect('user_profile')

    return render(request, 'user/user_profile.html', {'error': error})


@login_required
def profile_password_change(request):

    errors = {}
    user = request.user

    if request.method == 'POST':

        form_type = request.POST.get('form_type')

        if form_type == 'password_change':

            current_password = request.POST.get('current_password', "").strip()
            new_password = request.POST.get('new_password', "").strip()
            confirm_password = request.POST.get('confirm_password', "").strip()

            if not current_password:
                errors['current_password'] = "Current password is required."

            if not new_password:
                errors['new_password'] = "New password is required."

            if not confirm_password:
                errors['confirm_password'] = "Please confirm your new password."

             # At least one uppercase, one lowercase, one digit, one special char, and 8+ length
            strong_password_regex = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$'

            if not user.check_password(current_password):
                errors['current_password'] = "Current password is incorrect."

            elif new_password and not re.match(strong_password_regex, new_password):
                errors['new_password'] = (
                    "Password must be at least 8 characters long, contain an uppercase letter, "
                    "a lowercase letter, a number, and a special character."
                )

            elif current_password == new_password:
                messages.error(
                    request, "New password matches to current password, Try new.")

            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Password changed successfully!")
                update_session_auth_hash(request, user)  # Keep user logged in
                return redirect('user_profile')

    return render(request, 'user/profile_password_change.html', {'errors': errors})


@login_required
def profile_email_change(request):
    """
    Handle email verification with OTP
    """
    error = {}
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'send_otp':
            email = request.POST.get('email', '').strip()

            # To check if the entered is email is already exist
            if not CustomUser.objects.filter(email=email).exists():

                # Store OTP in session
                otp_generate_pls = generate_otp()
                request.session['otp'] = otp_generate_pls
                request.session['email'] = email
                request.session['otp_verified'] = False

                try:
                    send_verification_email(
                        email, otp_generate_pls, 'profile_email_change')

                    messages.success(
                        request, 'OTP sent successfully! Check your email.')
                    return render(request, 'user/profile_email_change.html', {
                        'otp_sent': True,
                        'email': email,
                    })

                except Exception as e:
                    messages.error(
                        request, f'Failed to send email. Please try again.')
                    return render(request, 'user/profile_email_change.html')

            else:
                error['duplicate_email'] = 'Entered email is already existed. Enter a new valid email.'
                return render(request, 'user/profile_email_change.html', {"error": error})

        elif action == 'verify_otp':
            entered_otp = request.POST.get('otp', '').strip()
            stored_otp = request.session.get('otp')
            email = request.session.get('email')

            if not stored_otp or not email:
                messages.error(
                    request, 'Session expired. Please request a new OTP.')
                return redirect('profile_email_change')

            if entered_otp == stored_otp:

                CustomUser.objects.filter(
                    id=request.user.id).update(email=email)
                # OTP verified successfully
                request.session['otp_verified'] = True
                messages.success(request, 'Email id changed Successfully.')

                # Clear OTP from session
                del request.session['otp']

                # Redirect to next page (e.g., dashboard, profile, etc.)
                # Change this to your desired redirect
                return redirect('user_profile')
            else:
                messages.error(request, 'Invalid OTP. Please try again.')
                return render(request, 'user/profile_email_change.html', {
                    'otp_sent': True,
                    'email': email
                })

    return render(request, 'user/profile_email_change.html')


@login_required
def user_address(request):

    print(request.session.get('address_update'))

    address = Address.objects.filter(
        user=request.user, is_active=True).order_by('-is_default')
    logger.info(f"New address is created: {address}")
    has_error = False

    if request.method == 'POST':

        address_type = request.POST.get(
            'address_type', '').strip().capitalize()
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
            messages.error(
                request, "Please enter a valid 6-digit postal code.")
            has_error = True

        if Address.objects.filter(user=request.user, is_active=True).exists():
            default = False
        else:
            default = True

        if not has_error:

            Address.objects.create(
                user=request.user,
                address_type=address_type,
                street=street,
                phone=phone,
                landmark=landmark,
                city=city,
                state=state,
                postal_code=postal_code,
                is_default=default,
            )
            messages.success(
                request, "Your new delivery address has been added successfully.")

            address_update = request.session['address_update']
            print(address_update)
            if address_update:
                return redirect('checkoutpage')
            else:
                # Or wherever you want to redirect
                return redirect('user_address')

    return render(request, 'user/user_address.html', {'addresss': address})


@login_required
def default_address(request, address_id):
    print(request.user, address_id)
    try:
        with transaction.atomic():

            # Reset all default flags for this user
            Address.objects.filter(
                user=request.user, is_default=True).update(is_default=False)

            # Set the selected one as default
            d_address = get_object_or_404(
                Address, id=address_id, user=request.user)
            d_address.is_default = True
            d_address.save()

        messages.success(
            request, f'{d_address.address_type} is now set as your default address.')
    except Address.DoesNotExist:
        messages.error(request, "Address not found or already unset.")
    except Exception as e:
        print(e)
        messages.error(request, f"Something went wrong: {str(e)}")

    return redirect('user_address')


@login_required
def user_cart(request):

    # Get or create the cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)
    # logger.debug(f"this is the cart created- {cart}")

    # Get all active cart items linked to this cart
    cart_item = CartItem.objects.filter(
        cart=cart, product_variant__is_active=True)
    subtotal = 0
    for item in cart_item:
        product = item.product_variant.product
        price = item.product_variant.price
        if product.is_offer:
            # apply discount on this product
            price = round(
                price - (price * product.discount_percentage / 100)
            )

        # store discounted price in the item (optional, for template)
        item.discounted_price = price

        # add to subtotal (quantity * discounted price)
        subtotal += price * item.quantity
        item.total_price = price * item.quantity
    count = cart_item.count()

    logger.debug(f"This is the cart created- {cart_item}")

    return render(request, 'user/user_cart.html', {
        'cart_item': cart_item,
        'subtotal': subtotal,
        'count': count,
    })


@login_required
def user_order(request):

    order_details = Order.objects.prefetch_related(
        'order_items').filter(user=request.user).order_by('-created_at')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(order_details, 5)
    order_details = paginator.get_page(page)

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
            orders = orders.filter(
                created_at__date__range=(start_date, end_date))
        elif period_filter == '2024':
            start_date = datetime(2024, 1, 1).date()
            end_date = datetime(2024, 12, 31).date()
            orders = orders.filter(
                created_at__date__range=(start_date, end_date))

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
        'order_count': order_count,
        'period_filter': period_filter,
    }

    return render(request, 'user/user_order.html', context)


@login_required
def cancel_order(request, order_id):

    if request.method == 'POST':

        reason = request.POST.get('reason')

        try:

            order = Order.objects.get(id=order_id)
            if order.status == 'delivered':
                order.status = 'request to return'
            else:
                order.status = 'request to cancel'

            order.is_active = False
            order.cancel_reason = reason
            order.save()

            messages.info(
                request, f"Your order id - {order.order_id} is requested to cancel.")
            return redirect('user_order')

        except Exception as e:

            messages.error(request, f"Error - {e}")

    return render(request, 'user/user_order.html',)


@login_required
def user_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)

    return render(request, 'user/user_wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def wishlist_toggle(request):
    if request.method == "POST":
        variant_id = request.POST.get("product_id")  # this is Variant ID
        print(variant_id)
        variant = get_object_or_404(Variant, id=variant_id)

        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user, variant=variant)

        if not created:
            wishlist_item.delete()
            return JsonResponse({"removed": True})
        else:
            return JsonResponse({"added": True})
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def user_wallet(request):

    user_wallet, created = Wallet.objects.get_or_create(user=request.user)
    wallet_amount = user_wallet.wallet_amount

    return render(request, 'user/user_wallet.html', {'wallet_amount': wallet_amount, 'user_wallet': user_wallet})


@login_required
def wallet_payment(request):

    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')
        total_amount = data.get('total_amount')
        print("wallet-",address_id,total_amount)

        user_wallet=Wallet.objects.get(user=request.user)
        print(user_wallet.wallet_amount)

        if user_wallet.wallet_amount>=int(total_amount):
            prev_amount=user_wallet.wallet_amount
            with transaction.atomic():
                user_wallet.wallet_amount-=int(total_amount)
                user_wallet.save()
                
 
                # Get cart and create order items
                cart = Cart.objects.filter(user=request.user).latest("created_at")
                cart_items = cart.cart_items.all()
                logger.info("Hi this is inside the transcation.")

                try:
                    address=Address.objects.get(id=address_id)
                except Exception as e:
                    return JsonResponse({"error": e}, status=500)
                
                # Calculate subtotal from cart
                subtotal = sum(item.get_total_price() for item in cart_items)
                
                # Get coupon discount from session
                coupon_code = request.session.get('applied_coupon_code', '')
                coupon_discount = float(request.session.get('coupon_discount', 0))
                
                # Calculate final amount after discount
                net_amount = subtotal - coupon_discount
                
                # Create local order first
                order = Order.objects.create(
                user=request.user,
                address=address,
                subtotal=subtotal,
                coupon_code=coupon_code,
                coupon_discount=coupon_discount,
                net_amount=net_amount,
                status="pending",
                order_date=timezone.now(),
                payment_method='wallet')   

                
                # Create order items and update stock
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product_variant=item.product_variant,
                        quantity=item.quantity,
                        unit_price=item.product_variant.price,
                        discount_price=item.get_discounted_price()
                    )
                    
                        # Update stock
                    item.product_variant.available_quantity -= item.quantity
                    item.product_variant.save()
                
                # Clear cart
                cart.delete()
                
                # Clear coupon from session after successful order
                if 'applied_coupon_code' in request.session:
                    del request.session['applied_coupon_code']
                if 'applied_coupon_id' in request.session:
                    del request.session['applied_coupon_id']
                if 'coupon_discount' in request.session:
                    del request.session['coupon_discount']
                
                logger.debug(f"The order amount: {total_amount} is deducted from the wallet {prev_amount}rs. Balance wallet amount {user_wallet.wallet_amount}.")
                return JsonResponse({
                    "status": "success",
                    "order_id": order.id,
                    "message": "Payment successful"
                })
        
        else: 
            return JsonResponse({"error": "Insufficient balance in Wallet. Try other payment method."}, status=500)
    
    except Exception as e:
        logger.error(f"Error processing order after payment verification: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
    


@login_required
def user_cust_care(request):

    return render(request, 'user/user_cust_care.html')


def calculate_total(cart_items):
    return sum(item.product_variant.price * item.quantity for item in cart_items)



@login_required
def checkoutpage(request):

    

    request.session['address_update'] = True

    try:
        cart = Cart.objects.filter(user=request.user).latest("created_at")
        cart_items = cart.cart_items.all()
    except Cart.DoesNotExist:
        cart_items = []
        return redirect("user_cart")

    subtotal = sum(item.get_total_price() for item in cart_items)
    
    # Check for applied coupon
    applied_coupon = None
    coupon_discount = 0
    
    if request.session.get('applied_coupon_id'):
        try:
            applied_coupon = Coupon.objects.get(id=request.session['applied_coupon_id'], is_active=True)
            coupon_discount = request.session.get('coupon_discount', 0)
        except Coupon.DoesNotExist:
            # Coupon no longer valid, remove from session
            if 'applied_coupon_code' in request.session:
                del request.session['applied_coupon_code']
            if 'applied_coupon_id' in request.session:
                del request.session['applied_coupon_id']
            if 'coupon_discount' in request.session:
                del request.session['coupon_discount']
    
    total = subtotal - coupon_discount
    addresses = Address.objects.filter(user=request.user, is_active=True)

    # print(request.method)

    if request.method == "POST":

        address_id = request.POST.get("shippingAddress")
        payment_method = request.POST.get("payment_method")
        print("hi checkout post method.")

        # Validate address
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Invalid address selected.")
            return redirect("checkoutpage")

        # Validate cart
        try:
            cart = Cart.objects.filter(user=request.user).latest("created_at")
        except Cart.DoesNotExist:
            messages.error(request, "No cart found.")
            return redirect("cart")

        # Validate cart
        cart_items = cart.cart_items.all()
        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect("cart")

        # Calculate net amount
        net_amount = sum(item.get_total_price() for item in cart_items)
        

        # handling cash on delivery
        if payment_method == "cod":

            # print("hi payment method is cod.")
            
            # Create local order first
            order = Order.objects.create(
                user=request.user,
                address=address,
                net_amount=net_amount,
                status="pending",
                order_date=timezone.now(),
                payment_method='cod')
            
            # print("order created: ", order)

            for item in cart_items:
                OrderItem.objects.create(order=order,
                                         product_variant=item.product_variant,
                                         quantity=item.quantity,
                                         unit_price=item.product_variant.price,
                                         discount_price=item.get_discounted_price())

                item.product_variant.available_quantity -= item.quantity
                item.product_variant.save()

            cart.delete()

            return redirect('order_confirm', id=order.id)

        # If Razorpay selected
        if payment_method == "razorpay":
            # Razorpay payment will be handled by JavaScript in the frontend
            # The form will be submitted via AJAX to create_razorpay_order view
            print('hi now you are in razorpay payment method.')
            messages.info(request, "Please complete the payment process.")
            return redirect("checkoutpage")

        # If COD / other methods
        return redirect("order_confirm", id=order.id)

    return render(request, "user/checkoutpage.html", {
        "addresses": addresses,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping": 0,
        "total": total,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "applied_coupon": applied_coupon,
        "coupon_discount": coupon_discount
    })


@login_required
def cod_payment(request):

    if request.method == "POST":

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)

        address_id = data.get("address_id")
        total_amount = data.get("total_amount")
        payment_method = data.get("payment_method")
        print(f"hey this is cod payment {address_id}, {total_amount}, {payment_method}")

        # Validate address
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            
            return JsonResponse({"error": "Invalid address selected."}, status=400)

        # Validate cart
        try:
            cart = Cart.objects.filter(user=request.user).latest("created_at")
        except Cart.DoesNotExist:
            
            return JsonResponse({"error": "No cart found."}, status=400)

        # Validate cart
        cart_items = cart.cart_items.all()
        if not cart_items.exists():
            
            return JsonResponse({"error": "Your cart is empty."}, status=400)

        # Calculate net amount (subtotal before coupon)
        subtotal = sum(item.get_total_price() for item in cart_items)
        
        # Get coupon discount from session
        coupon_code = request.session.get('applied_coupon_code', '')
        coupon_discount = float(request.session.get('coupon_discount', 0))
        
        # Calculate final amount after discount
        net_amount = subtotal - coupon_discount
            
        # Create local order first
        order = Order.objects.create(
                user=request.user,
                address=address,
                subtotal=subtotal,
                coupon_code=coupon_code,
                coupon_discount=coupon_discount,
                net_amount=net_amount,
                status="pending",
                order_date=timezone.now(),
                payment_method='cod')
            
            

        for item in cart_items:
            OrderItem.objects.create(order=order,
                                         product_variant=item.product_variant,
                                         quantity=item.quantity,
                                         unit_price=item.product_variant.price,
                                         discount_price=item.get_discounted_price())

            item.product_variant.available_quantity -= item.quantity
            item.product_variant.save()

        cart.delete()
        
        # Clear coupon from session after successful order
        if 'applied_coupon_code' in request.session:
            del request.session['applied_coupon_code']
        if 'applied_coupon_id' in request.session:
            del request.session['applied_coupon_id']
        if 'coupon_discount' in request.session:
            del request.session['coupon_discount']


    return JsonResponse({
                    "status": "success",
                    "order_id": order.id,
                    "message": "Cash on delivery Accepted."
                })

    


@login_required
def order_confirm(request, id):

    try:
        order = Order.objects.get(id=id)
        order_items = OrderItem.objects.filter(order=order)

    except Exception as e:
        messages.error(request, f"Something went wrong: {str(e)}")

    return render(request, 'user/order_confirm.html', {'order': order, 'order_items': order_items})


@login_required
def order_failed(request):

    order = None
    order_id = request.GET.get('order_id')
    try:
        if order_id:
            order = Order.objects.get(id=order_id, user=request.user)
            # Do not overwrite status here; it should remain 'pending' for payment retry flow
            # Ensure payment flag reflects pending
            if order.is_paid:
                order.is_paid = False
                order.save(update_fields=["is_paid"]) 
    except Order.DoesNotExist:
        order = None

    return render(request, 'user/order_failed.html', {'order': order})


@login_required
@require_POST
def create_order_after_failed_payment(request):
    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')

        if not address_id:
            return JsonResponse({"error": "Address ID is required"}, status=400)

        # Validate address
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return JsonResponse({"error": "Invalid address"}, status=400)

        # Validate cart
        try:
            cart = Cart.objects.filter(user=request.user).latest("created_at")
            cart_items = cart.cart_items.all()
            if not cart_items.exists():
                return JsonResponse({"error": "Cart is empty"}, status=400)
        except Cart.DoesNotExist:
            return JsonResponse({"error": "No cart found"}, status=400)

        # Calculate subtotal from cart
        subtotal = sum(item.get_total_price() for item in cart_items)
        
        # Get coupon discount from session
        coupon_code = request.session.get('applied_coupon_code', '')
        coupon_discount = float(request.session.get('coupon_discount', 0))
        
        # Calculate final amount after discount
        net_amount = subtotal - coupon_discount

        # Create order with payment pending
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                address=address,
                subtotal=subtotal,
                coupon_code=coupon_code,
                coupon_discount=coupon_discount,
                net_amount=net_amount,
                status='pending',
                is_paid=False,
                payment_method='razorpay',
                order_date=timezone.now(),
            )

            # Create order items and update stock (mirroring COD logic)
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=item.product_variant,
                    quantity=item.quantity,
                    unit_price=item.product_variant.price,
                    discount_price=item.get_discounted_price()
                )
                item.product_variant.available_quantity -= item.quantity
                item.product_variant.save()

            # Clear cart
            cart.delete()

        return JsonResponse({
            "status": "success",
            "order_id": order.id
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error creating pending order after payment failure: {str(e)}")
        return JsonResponse({"error": "Failed to create order"}, status=500)


@login_required
@require_POST
def add_to_cart(request, id):
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        quantity = int(data.get('quantity', 0))  # ensure integer
        is_buy_now = data.get("buy_now", False)

        # Remove wishlist entry
        Wishlist.objects.filter(user=request.user, variant=variant_id).delete()

        if quantity <= 0:
            return JsonResponse({'success': False, 'message': 'Invalid quantity'})

        # Get or create user's cart
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Get variant object
        variant = get_object_or_404(Variant, id=variant_id)

        try:
            cart_item = CartItem.objects.get(
                cart=cart, product_variant=variant)

            new_quantity = cart_item.quantity + quantity
            print('new_quantity -', new_quantity)
            # Check quantity limit
            if new_quantity > 5:
                return JsonResponse({
                    'success': False,
                    'message': 'You cannot add more than 5 of this item.'
                })
            print('stock - ', cart_item.product_variant.available_quantity)
            print('quantity- ', quantity)

            if cart_item.product_variant.available_quantity <= quantity:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid quantity'
                })

            cart_item.quantity += quantity
            cart_item.save()

        except CartItem.DoesNotExist:
            if quantity > 5:
                return JsonResponse({
                    'success': False,
                    'message': 'You cannot add more than 5 of this item.'
                })

            CartItem.objects.create(
                cart=cart,
                product_variant=variant,
                quantity=quantity
            )

            response = {"success": True}

            if is_buy_now:
            # Redirect user to the cart or checkout page
                response["redirect_url"] = reverse('user_cart')
            return JsonResponse(response)

        return JsonResponse({'success': True, 'redirect_url': '/user/cart/'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})


@login_required
@require_POST
def update_cart_quantity(request):
    item_id = request.POST.get('item_id')
    action = request.POST.get('action')  # 'increase' or 'decrease'

    try:
        cart_item = CartItem.objects.get(id=item_id)

        # Update quantity
        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1

        cart_item.save()

        # Use model method for item total
        item_total_price = cart_item.get_total_price()

        # Subtotal (all items, discounts included)
        cart_items = CartItem.objects.filter(cart=cart_item.cart)
        subtotal = sum(item.get_total_price() for item in cart_items)

        return JsonResponse({
            'success': True,
            'new_quantity': cart_item.quantity,
            'item_total_price': item_total_price,
            'subtotal': subtotal,
            'cart_total': subtotal,
        })

    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})


@login_required
@require_POST
def delete_cart_item(request):

    item_id = request.POST.get('item_id')
    print("item_id received:", item_id)

    try:
        cart_item = CartItem.objects.get(id=item_id)
        cart = cart_item.cart
        cart_item.delete()

        # fetching the remaining cart_items
        cart_items = CartItem.objects.filter(cart=cart)
        count = cart_items.count()
        print("count -", count)
        cart_total = sum(item.get_total_price() for item in cart_items)

        return JsonResponse({
            'success': True,
            'cart_total': cart_total,
            'count': count,
        })

    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})


@never_cache
def verification(request):

    if request.user.is_authenticated:
        return redirect('loading_page')

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
                    # Get referrer if exists
                    referrer = None
                    referrer_id = user_session_data.get('referrer_id')
                    if referrer_id:
                        try:
                            referrer = CustomUser.objects.get(id=referrer_id)
                        except CustomUser.DoesNotExist:
                            pass
                    
                    # Create new user
                    user = CustomUser.objects.create(
                        first_name=user_session_data['first_name'],
                        last_name=user_session_data['last_name'],
                        email=user_session_data['email'],
                        phone_no=user_session_data['phone_no'],
                        password=user_session_data['password'],
                        referred_by=referrer
                    )
                    
                    # Create referral reward coupon for the referrer
                    if referrer:
                        # Generate unique coupon code
                        coupon_code = f"REF{referrer.referral_code[:4]}{user.id}"
                        
                        # Create coupon valid for 90 days
                        Coupon.objects.create(
                            code=coupon_code,
                            description=f"Referral reward for referring {user.first_name} {user.last_name}",
                            discount_type='fixed',
                            discount_value=300,
                            minimum_amount=0,
                            valid_from=timezone.now(),
                            valid_until=timezone.now() + timedelta(days=90),
                            is_active=True,
                            specific_user=referrer,
                            is_referral_reward=True
                        )
                        logger.info(f"Referral coupon {coupon_code} created for user {referrer.email}")

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


@never_cache
def fg_verification(request):

    if request.user.is_authenticated:
        return redirect('loading_page')

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


@never_cache
def otp_page_fg(request):

    if request.user.is_authenticated:
        return redirect('loading_page')

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


@never_cache
def password_change(request):
    errors = {}

    # 🚫 If password was changed, don't show this page again
    if request.session.get('password_changed'):

        del request.session['password_changed']
        return redirect('login')

    try:

        test = request.session['verification_email']
        user = CustomUser.objects.get(email=test)

    except KeyError as e:

        messages.error(
            request, "You have to verify your email first. Click the forget password.")
        return redirect('login')

    if request.method == 'POST':

        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not new_password:
            errors['new_password'] = "New password is required."

        if not confirm_password:
            errors['confirm_password'] = "Please confirm your new password."

        # At least one uppercase, one lowercase, one digit, one special char, and 8+ length
        strong_password_regex = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$'

        if new_password and not re.match(strong_password_regex, new_password):
            errors['new_password'] = (
                "Password must be at least 8 characters long, contain an uppercase letter, "
                "a lowercase letter, a number, and a special character."
            )

        if new_password and confirm_password and new_password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        # Check if passwords match
        if not errors:
            user.password = make_password(new_password)  # new password saved.
            user.save()

            messages.success(request, "Your Password changed sucessfully.")

            request.session['password_changed'] = True  # 🧠 Set the flag
            return redirect('login')

        else:

            errors['confirm_password'] = "Passwords do not match. Please re-enter the password again."

    return render(request, 'login/password_change.html', {'errors': errors})


@login_required
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
            messages.error(
                request, "Please enter a valid 6-digit postal code.")
            has_error = True

        if not has_error:
            address.save()
            messages.success(
                request, "Your new delivery address has been Edited successfully.")

            address_update = request.session['address_update']
            if address_update:
                return redirect('checkoutpage')
            else:
                return redirect('user_address')

    return render(request, 'user/address_edit.html', {'address': address})


@login_required
def address_delete(request, address_id):

    status = Address.objects.get(id=address_id)
    status.is_active = False
    status.save()

    active_addresses = Address.objects.filter(
        user=request.user, is_active=True)

    if not active_addresses.exists():
        return redirect('user_address')
    else:
        # ensure there's exactly one default (reset all, then set one)
        Address.objects.filter(user=request.user).update(is_default=False)
        set_default_address = active_addresses.first()
        set_default_address.is_default = True
        set_default_address.save()

    return redirect('user_address')


def change_variant(request, book_id):
    try:
        book = get_object_or_404(Product, id=book_id, is_active=True)
        data = json.loads(request.body)
        variant_id = data.get('variant_id')

        variant = Variant.objects.prefetch_related(
            'productimage_set').get(id=variant_id)

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
        # Use best discount from product or genre
        has_active_offer = book.has_active_offer()
        best_discount_percentage = book.get_best_discount_percentage()
        discounted_price = round(book.get_discounted_price(variant.price))
        offer_title = book.get_active_offer_title()
        
        # Format the variant data
        variant_data = {
            'id': variant.id,
            'language': variant.language,
            'publisher': variant.publisher,
            'published_date': variant.published_date.strftime('%d %b %Y') if variant.published_date else '',
            'page': variant.page,
            'price': discounted_price,
            'original_price': variant.price,
            'discounted_price': discounted_price,
            'best_discount_percentage': best_discount_percentage,
            'has_active_offer': has_active_offer,
            'offer_title': offer_title,
            'available_quantity': variant.available_quantity,
            'images': images,
            'is_offer': has_active_offer,  # For backward compatibility
        }
        print(variant_data)
        return JsonResponse({'success': True, 'variant': variant_data})

    except Variant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Variant not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
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


@login_required
@require_POST
def remove_from_wishlist(request):
    item_id = request.POST.get('item_id')
    print('item_id -', item_id)

    # handling the wishlist item removal
    try:
        # wishlist item removal
        wish_item = Wishlist.objects.get(id=item_id, user=request.user)
        wish_item.delete()

        return JsonResponse({
            'success': True,
        })

    except Wishlist.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})


@login_required
@require_POST
def create_razorpay_order(request):
    try:
        data = json.loads(request.body)
        amount = float(data.get('amount', 0))
        address_id = data.get('address_id')
        
        if not amount or amount <= 0:
            return JsonResponse({"error": "Invalid amount"}, status=400)
        
        if not address_id:
            return JsonResponse({"error": "Address ID is required"}, status=400)
            
        # Validate address exists
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return JsonResponse({"error": "Invalid address"}, status=400)
        
        # Validate cart exists and has items
        try:
            cart = Cart.objects.filter(user=request.user).latest("created_at")
            cart_items = cart.cart_items.all()
            if not cart_items.exists():
                return JsonResponse({"error": "Cart is empty"}, status=400)
        except Cart.DoesNotExist:
            return JsonResponse({"error": "No cart found"}, status=400)

        # Create Razorpay order
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        
        # Amount should be in paise (multiply by 100)
        amount_in_paise = int(amount * 100)
        
        payment_order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": "1"   # auto capture
        })

        return JsonResponse({
            "order_id": payment_order["id"],
            "amount": amount_in_paise
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {str(e)}")
        return JsonResponse({"error": "Failed to create order"}, status=500)


@login_required
@require_POST
def verify_razorpay_payment(request):
    try:
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        address_id = data.get('address_id')
        total_amount = data.get('total_amount')
        
        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, address_id, total_amount]):
            return JsonResponse({"error": "Missing payment details"}, status=400)
        
        # Validate address
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return JsonResponse({"error": "Invalid address"}, status=400)
        
        # Verify payment signature
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        
        # Create signature verification data
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        # Verify the signature
        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"error": "Payment verification failed"}, status=400)
        
        # Payment is verified, now process the order like COD flow
        try:
            with transaction.atomic():
                # Get cart
                cart = Cart.objects.filter(user=request.user).latest("created_at")
                cart_items = cart.cart_items.all()
                if not cart_items.exists():
                    return JsonResponse({"error": "Cart is empty"}, status=400)

                # Recalculate subtotal from cart (don't trust client)
                subtotal = sum(item.get_total_price() for item in cart_items)
                
                # Get coupon discount from session
                coupon_code = request.session.get('applied_coupon_code', '')
                coupon_discount = float(request.session.get('coupon_discount', 0))
                
                # Calculate final amount after discount
                net_amount = subtotal - coupon_discount

                # Create order
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    subtotal=subtotal,
                    coupon_code=coupon_code,
                    coupon_discount=coupon_discount,
                    net_amount=net_amount,
                    status="pending",
                    order_date=timezone.now(),
                    is_paid=True,
                    payment_method='razorpay',
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_signature=razorpay_signature,
                )

                # Create order items and update stock
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product_variant=item.product_variant,
                        quantity=item.quantity,
                        unit_price=item.product_variant.price,
                        discount_price=item.get_discounted_price()
                    )
                    
                    # Update stock
                    item.product_variant.available_quantity -= item.quantity
                    item.product_variant.save()
                
                # Clear cart
                cart.delete()
                
                # Clear coupon from session after successful order
                if 'applied_coupon_code' in request.session:
                    del request.session['applied_coupon_code']
                if 'applied_coupon_id' in request.session:
                    del request.session['applied_coupon_id']
                if 'coupon_discount' in request.session:
                    del request.session['coupon_discount']

                return JsonResponse({
                    "status": "success",
                    "order_id": order.id,
                    "message": "Payment successful"
                })
                
        except Exception as e:
            logger.error(f"Error processing order after payment verification: {str(e)}")
            return JsonResponse({"error": "Failed to process order"}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error verifying Razorpay payment: {str(e)}")
        return JsonResponse({"error": "Payment verification failed"}, status=500)


@login_required
@require_POST
def apply_coupon(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        
        if not code:
            return JsonResponse({"success": False, "error": "Coupon code is required"}, status=400)
        
        # Check if coupon already applied
        if request.session.get('applied_coupon_code'):
            return JsonResponse({"success": False, "error": "A coupon is already applied. Remove it first."}, status=400)
        
        # Get cart and calculate subtotal
        try:
            cart = Cart.objects.filter(user=request.user).latest("created_at")
            cart_items = cart.cart_items.all()
            if not cart_items.exists():
                return JsonResponse({"success": False, "error": "Cart is empty"}, status=400)
        except Cart.DoesNotExist:
            return JsonResponse({"success": False, "error": "Cart is empty"}, status=400)
        
        subtotal = sum(item.get_total_price() for item in cart_items)
        
        # Validate coupon
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
        except Coupon.DoesNotExist:
            return JsonResponse({"success": False, "error": "Invalid or inactive coupon code"}, status=400)
        
        # Use the is_valid method which checks user-specific coupons
        is_valid, error_message = coupon.is_valid(user=request.user, cart_total=subtotal)
        if not is_valid:
            return JsonResponse({"success": False, "error": error_message}, status=400)
        
        # Calculate discount
        if coupon.discount_type == 'percentage':
            discount = (subtotal * coupon.discount_value) / 100
        else:  # fixed
            discount = coupon.discount_value
        
        # Apply maximum discount cap if set
        if coupon.maximum_discount and discount > coupon.maximum_discount:
            discount = coupon.maximum_discount
        
        # Ensure discount doesn't exceed subtotal
        discount = min(discount, subtotal)
        
        # Store in session
        request.session['applied_coupon_code'] = coupon.code
        request.session['applied_coupon_id'] = coupon.id
        request.session['coupon_discount'] = float(discount)
        
        return JsonResponse({
            "success": True,
            "discount": float(discount),
            "code": coupon.code,
            "message": "Coupon applied successfully"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error applying coupon: {str(e)}")
        return JsonResponse({"success": False, "error": "Failed to apply coupon"}, status=500)


@login_required
@require_POST
def remove_coupon(request):
    try:
        # Remove coupon from session
        if 'applied_coupon_code' in request.session:
            del request.session['applied_coupon_code']
        if 'applied_coupon_id' in request.session:
            del request.session['applied_coupon_id']
        if 'coupon_discount' in request.session:
            del request.session['coupon_discount']
        
        return JsonResponse({"success": True, "message": "Coupon removed"})
        
    except Exception as e:
        logger.error(f"Error removing coupon: {str(e)}")
        return JsonResponse({"success": False, "error": "Failed to remove coupon"}, status=500)


@login_required
def get_available_coupons(request):
    try:
        # Get all active coupons that are currently valid
        now = timezone.now()
        # Include general coupons (specific_user=None) and user-specific coupons for this user
        from django.db.models import Q
        coupons = Coupon.objects.filter(
            Q(specific_user=None) | Q(specific_user=request.user),
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now
        ).order_by('-discount_value')
        
        coupons_data = []
        for coupon in coupons:
            coupon_dict = {
                'code': coupon.code,
                'description': coupon.description or '',
                'discount_type': coupon.discount_type,
                'discount_value': float(coupon.discount_value),
                'minimum_amount': float(coupon.minimum_amount),
                'maximum_discount': float(coupon.maximum_discount) if coupon.maximum_discount else None,
                'valid_until': coupon.valid_until.isoformat(),
                'is_exclusive': coupon.specific_user is not None,
                'is_referral_reward': coupon.is_referral_reward
            }
            coupons_data.append(coupon_dict)
        
        return JsonResponse({
            "success": True,
            "coupons": coupons_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching coupons: {str(e)}")
        return JsonResponse({"success": False, "error": "Failed to fetch coupons"}, status=500)
