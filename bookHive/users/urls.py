from . import views
from django.urls import path

urlpatterns = [
    path('', views.loading_page, name='loading_page'),
    path('login', views.user_login, name='login'),
    path('signup', views.signup, name='signup'),
    path('home_page', views.home_page, name='home_page'),
    path('logout_user', views.logout_user, name='logout_user'),
    path('product_details/<int:id>/',
         views.product_details, name='product_details'),
    path('search_book',
         views.search_book, name='search_book'),
     path('user_profile',views.user_profile, name='user_profile'),
     path('user_address',views.user_address, name='user_address'),
     path('user_cart',views.user_cart, name='user_cart'),
     path('user_order',views.user_order, name='user_order'),
     path('user_wishlist',views.user_wishlist, name='user_wishlist'),
     path('user_wallet',views.user_wallet, name='user_wallet'),
     path('user_cust_care',views.user_cust_care, name='user_cust_care'),
     path('add_to_cart',views.add_to_cart, name='add_to_cart'),
     path('checkoutpage',views.checkoutpage, name='checkoutpage'),
     path('verification',views.verification, name='verification'),
     path('fg_verification',views.fg_verification, name='fg_verification'),
]
