
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
from django.http import HttpResponse
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt







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

        if not errors:  # If no errors, proceed with user creation
            # user = CustomUser.objects.create(
            #     first_name=firstName,
            #     last_name=lastName,
            #     email=email,
            #     phone_no=mobile,
            #     password=make_password(password)  # Hash password before saving
            # )
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
    print(genres)
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
    address = Address.objects.filter(user=request.user, is_active=True)

    if request.method == 'POST':
        Address.objects.create(
            user=request.user,
            address_type=request.POST['address_type'],
            street=request.POST['street'],
            phone=request.POST['phone'],
            landmark=request.POST['landmark'],
            city=request.POST['city'],
            state=request.POST['state'],
            postal_code=request.POST['pincode'],
        )
        return redirect('user_address')

    return render(request, 'user/user_address.html', {'addresss': address})





def user_cart(request):

    cart = Cart.objects.get(user=request.user)
    cart_item = CartItem.objects.filter(cart=cart,product_variant__is_active=True)

    subtotal = sum(item.get_total_price() for item in cart_item)
    

    return render(request, 'user/user_cart.html',{ 'cart_item':cart_item, "subtotal":subtotal })

    

    
    


def user_order(request):
    order_details = Order.objects.prefetch_related(
        'order_items').filter(user=request.user)

    return render(request, 'user/user_order.html', {'order_details': order_details})


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


def checkoutpage(request):
    if request.method == 'POST':
        print(request.POST)
        address_id = request.POST.get('shippingAddress')
        payment_method = request.POST.get('payment_method')

        # Get user's active/latest cart
        try:
            cart = Cart.objects.filter(user=request.user).latest('created_at')
        except Cart.DoesNotExist:
            return redirect('cart')  # no cart found

        cart_items = cart.cart_items.all()

        if not cart_items.exists():
            return redirect('cart')  # handle empty cart

        # Create order
        order = Order.objects.create(
            user=request.user,
            address=Address.objects.get(id=address_id),
            net_amount=calculate_total(cart_items),
            status='Pending'
        )

        # Add order items
        for item in cart_items:
            order.order_items.create(
                product_variant=item.product_variant,  # reference the product_variant field
                quantity=item.quantity,
                # calculate total amount based on quantity and price
                total_amount=item.product_variant.price * item.quantity
            )

        # Delete the cart after checkout
        cart.delete()

        # return redirect('user_order', order_id=order.id)
        return redirect('user_order')

    # GET Request
    try:
        cart = Cart.objects.filter(user=request.user).latest('created_at')
        cart_items = cart.cart_items.all()
    except Cart.DoesNotExist:
        cart_items = []

    subtotal = calculate_total(cart_items)
    shipping = 0  # Optional logic
    total = subtotal + shipping

    address = Address.objects.filter(user=request.user, is_active=True)

    return render(request, 'user/checkoutpage.html', {
        'addresses': address,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total': total
    })

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
        print(cart)

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
        # subtotal = sum(item.get_total_price() for item in cart_item)
        return JsonResponse({
            'success': True,
            'new_quantity': cart_item.quantity,
            'item_total_price': item_total_price,
            'cart_total': cart_total
        })

    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})

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
                user = CustomUser.objects.create(
                    first_name=user_session_data['first_name'],
                    last_name=user_session_data['last_name'],
                    email=user_session_data['email'],
                    phone_no=user_session_data['phone_no'],
                    password=user_session_data['password']

                )

                # Clear session after creating
                del request.session['userdata']
                del request.session['otp']
                del request.session['verification_email']

                messages.success(
                    request, "Email verified and account created! You can now log in.")
                return redirect('login')  # or home page
            else:
                messages.error(request, "Invalid OTP. Try again.")

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


def sample(request):
    print('hi')
    if request.method == "POST":
        biscuits = request.COOKIES
        print(biscuits)
        print('hi2')
        return render(request, 'sample.html', {'biscuits': biscuits})

    return render(request, 'sample.html')






