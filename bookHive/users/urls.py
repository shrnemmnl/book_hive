from . import views
from django.urls import path

urlpatterns = [
    path('', views.loading_page, name='loading_page'),
    path('login', views.user_login, name='login'),
    path('signup', views.signup, name='signup'),
    path('logout_user', views.logout_user, name='logout_user'),
    path('product_details/<int:id>/', views.product_details, name='product_details'),
    path('search_book', views.search_book, name='search_book'),
    #user Profile
    path('user-profile',views.user_profile, name='user_profile'),
    path('profile-password-change',views.profile_password_change, name='profile_password_change'),
    path('profile-email-change',views.profile_email_change, name='profile_email_change'),
    #user address
    path('user_address',views.user_address, name='user_address'),
    path('default-address/<int:address_id>/',views.default_address, name='default_address'),
    path('address_delete/<int:address_id>/',views.address_delete, name='address_delete'),
    # cart 
    path('user-cart',views.user_cart, name='user_cart'),
    path('add_to_cart/<int:id>/',views.add_to_cart, name='add_to_cart'),
    path('update-quantity', views.update_cart_quantity, name='update_cart_quantity'),
    path('delete-cart-item',views.delete_cart_item, name='delete_cart_item'),
    #user order
    path('user_order',views.user_order, name='user_order'),
    path('order/search',views.order_search, name='order_search'),
    path('cancel_order/<int:item_id>/',views.cancel_order, name='cancel_order'),
    #user wishlist
    path('user-wishlist',views.user_wishlist, name='user_wishlist'),
    path('remove-from-wishlist',views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/toggle/', views.wishlist_toggle, name='wishlist-toggle'),
    #wallet
    path('user_wallet',views.user_wallet, name='user_wallet'),
    path('wallet/payment/',views.wallet_payment, name='wallet_payment'),
    
    path('user_cust_care',views.user_cust_care, name='user_cust_care'),
    
    path('verification',views.verification, name='verification'),
    path('fg_verification',views.fg_verification, name='fg_verification'),
    path('otp_page_fg',views.otp_page_fg, name='otp_page_fg'),
    path('password_change',views.password_change, name='password_change'),
    path('address_edit/<int:address_id>/',views.address_edit, name='address_edit'),
    
    path('change_variant/<int:book_id>/',views.change_variant, name='change_variant'),
    
    path('order-confirm/<int:id>/',views.order_confirm, name='order_confirm'),
    path('download_invoice/<int:id>/',views.download_invoice, name='download_invoice'),

    path('checkoutpage',views.checkoutpage, name='checkoutpage'),
    path('checkoutpage/cod/',views.cod_payment, name='cod_payment'),
    path('create-razorpay-order',views.create_razorpay_order, name='create_razorpay_order'),    
    path('verify-razorpay-payment',views.verify_razorpay_payment, name='verify_razorpay_payment'),    
    path('order-failed/', views.order_failed, name='order_failed'),
    # DEPRECATED: path('order/create-after-failed', views.create_order_after_failed_payment, name='create_order_after_failed_payment'),
    
    # Coupon URLs
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('get-available-coupons/', views.get_available_coupons, name='get_available_coupons'),

]
