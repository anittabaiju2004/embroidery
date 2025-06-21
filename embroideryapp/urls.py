from django.urls import path
from . import views
from .views import *
from django.urls import path
from .views import admin_view_users
from django.urls import path
from .views import seller_view_users
from django.urls import path
from . import views
from django.urls import path
from . import views
from django.urls import path
from .views import view_product_list  # Import the view function
from django.urls import path
from . import views
from django.urls import path,re_path
from . import views
from django.urls import path

urlpatterns = [
  path('',index,name='index'),
  path('login/', login, name='login'),
  path('logout/', logout_view, name='logout'),
  path('register/', register, name='register'),
  path('seller/register/', seller_register, name='seller_register'),
  path('admin_index/', admin_index, name='admin_index'),
  path('seller_index/', seller_index, name='seller_index'),
  path('user_index/', user_index, name='user_index'),
  path('view-users/', admin_view_users, name='admin_view_users'),
  path('pending-sellers/', admin_view_pending_sellers, name='admin_view_pending_sellers'),
  path('approve-seller/<int:seller_id>/', approve_seller, name='approve_seller'),
  path('reject-seller/<int:seller_id>/', reject_seller, name='reject_seller'),
  path('approved-sellers/', admin_view_approved_sellers, name='admin_view_approved_sellers'),
  path('rejected-sellers/', admin_view_rejected_sellers, name='admin_view_rejected_sellers'),
  path('feedback/', leave_feedback, name='leave_feedback'),
  path('admin-view-feedback/',views.admin_view_feedback, name='admin_view_feedback'),
  path('seller-view-users/', seller_view_users, name='view_users'),
  path('seller-view-feedback/',view_feedback, name='view_feedback'),
  path('seller/products/', views.view_product, name='view_product'),
  path('seller/products/add/', views.add_product, name='add_product'),
  path('seller/products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
  path('seller/products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
  path('', views.index, name='index'),
  path('user_view_products/', views.user_view_products, name='user_view_products'),  # URL for viewing products
  path('seller/view_product_details/<int:product_id>/', views.view_product_details, name='view_product_details'),
  # path('view_products/', views.view_products, name='view_products'),
  path('add-video/', views.add_video, name='add_video'),
  path('view-videos/', views.view_videos, name='view_videos'),
  path('delete-video/<int:video_id>/', views.delete_video, name='delete_video'),
  path('videos/', views.view_video, name='videos'), 
  path('products/', views.products, name='products'),
  path('seller-view-videos/', views.seller_view_videos, name='seller_view_videos'),
  # path('user_products/', views.product_list, name='user_product_list'),
  path('products/<int:product_id>/', views.product_detail, name='product_detail'),
  path('commissions/', views.commission_list, name='commission_list'),
  path('commissions/<int:commission_id>/', views.commission_detail, name='commission_detail'),
  path('payment/<int:order_id>/', views.payment_page, name='payment'),
  path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
  path('cart/', views.view_cart, name='view_cart'),
  path('cart/update/<int:cart_item_id>/', views.update_cart, name='update_cart'),
  path('cart/remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
  path('checkout/', views.checkout, name='checkout'),
  path('buy/<int:product_id>/', views.buy_now, name='buy_now'),
  path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
  path('orders/', views.order_history, name='order_history'),
  path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
  path('seller/orders/', views.seller_orders, name='seller_orders'),
  path('seller/orders/<int:order_id>/', views.seller_order_detail, name='seller_order_detail'),
  path('seller/notifications/', views.seller_notifications, name='seller_notifications'),
  path('seller/notifications/<int:notification_id>/', views.view_notification, name='view_notification'),
  path('order-summary/', views.order_summary, name='order_summary'),
  path('profile/', views.profile_view, name='profile'),
  path('profile/edit/', views.edit_profile, name='edit_profile'),
  path('videos/edit/<int:video_id>/', views.edit_video, name='edit_video'),
  path('seller_profile/', views.seller_profile_view, name='seller_profile'),
  path('seller_profile/edit/', views.seller_profile_edit, name='seller_profile_edit'),
]
 







