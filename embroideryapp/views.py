import re
import uuid
from decimal import Decimal
from django.forms import ModelForm
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.db.models import Prefetch
from django.contrib.auth import logout
from .models import tbl_register, Seller, Admin, Video, Products, Order, OrderItem, Payment, Notification, AdminCommission, Cart, Feedback



#Views for login, logout, index

def index(request):
    return render(request,'index.html')


def seller_index(request):
    return render(request,'seller/seller_index.html') 

def admin_index(request):
    return render(request,'admin/admin_index.html') 

def user_index(request):
    return render(request,'user/user_index.html') 

def login(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, "Email and password are required")
            return redirect('login')

        # Check user type
        user = tbl_register.objects.filter(email=email, password=password).first()
        seller = Seller.objects.filter(email=email, password=password, status="approved").first()
        admin = Admin.objects.filter(email=email, password=password).first()

        if user:
            request.session['id'] = user.id
            request.session['user_type'] = 'user'
            request.session['email'] = user.email
            request.session['name'] = user.name
            return redirect('user_index')
        
        if seller:
            request.session['id'] = seller.id
            request.session['user_type'] = 'seller'
            request.session['email'] = seller.email
            request.session['name'] = seller.name
            return redirect('seller_index')

        if admin:
            request.session['id'] = admin.id
            request.session['user_type'] = 'admin'
            request.session['email'] = admin.email
            request.session['name'] = admin.name
            return redirect('admin_index')

        # Seller exists but not approved
        if Seller.objects.filter(email=email, password=password).exists():
            messages.error(request, "Your seller account is pending approval")
            return redirect('login')

        messages.error(request, "Invalid email or password")
        return redirect('login')

    if 'id' in request.session:
        request.session.flush()
    
    return render(request, "login.html")


def logout(request):
    request.session.flush()
    messages.success(request, "You have been logged out successfully")
    return redirect('login')

def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to login page after logout

#---------------------------------------------------- Users  Module -------------------------------------------------------------------------------#

def register(request):
    import re
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')

        # Email validation
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            messages.error(request, "Invalid email format")
            return redirect('register')

        # Phone number validation (10-15 digits)
        phone_regex = r'^\d{10,15}$'
        if not re.match(phone_regex, phone_number):
            messages.error(request, "Phone number must be 10-15 digits")
            return redirect('register')

        # Password validation (min 8 chars, at least 1 letter and 1 number)
        password_regex = r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$'
        if not re.match(password_regex, password):
            messages.error(request, "Password must be at least 8 characters and contain letters and numbers")
            return redirect('register')

        if tbl_register.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('register')

        if tbl_register.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already exists")
            return redirect('register')

        user = tbl_register.objects.create(
            name=name,
            email=email,
            password=password,  
            phone_number=phone_number,
            address=address
        )
        user.save()

        messages.success(request, "Registration successful")
        return redirect('login')

    return render(request, 'user_register.html')


def leave_feedback(request):
    latest_feedback = None
    user_feedbacks = None
    user_obj = None

    if 'id' in request.session and request.session.get('user_type') == 'user':
        user_obj = tbl_register.objects.get(id=request.session['id'])

    if request.method == "POST":
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        name = request.POST.get('name', user_obj.name if user_obj else 'Anonymous')

        if not rating or not comment:
            messages.error(request, "Both rating and comment are required.")
        else:
            feedback = Feedback.objects.create(
                user=user_obj,
                name=name,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, "Thank you for your feedback!")
            latest_feedback = feedback

    # Show all feedbacks by this user (by user id)
    if user_obj:
        user_feedbacks = Feedback.objects.filter(user=user_obj).order_by('-created_at')

    return render(request, 'user/feedback_form.html', {
        'latest_feedback': latest_feedback,
        'user_feedbacks': user_feedbacks
    })



def user_view_products(request):
    product_list = Products.objects.all()
    paginator = Paginator(product_list, 10)  # 10 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    return render(request, 'user/view_product.html', {
        'products': products,
        'is_paginated': products.has_other_pages(),
        'page_obj': products,
    })

def product_detail(request, product_id):
    product = get_object_or_404(Products, pk=product_id)
    return render(request, 'user/product_detail.html', {'product': product})




@transaction.atomic
def buy_now(request, product_id):
    if request.method == 'POST':
        if 'id' not in request.session or request.session.get('user_type') != 'user':
            messages.error(request, "Please login as a user to make purchases")
            return redirect('login')
        
        try:
            user = tbl_register.objects.get(id=request.session['id'])
        except tbl_register.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('user_view_products')
        
        product = get_object_or_404(Products, pk=product_id)
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1
        
        if quantity <= 0:
            messages.error(request, "Invalid quantity.")
            return redirect('product_detail', product_id=product_id)
        
        if product.stock < quantity:
            messages.error(request, "Not enough stock available.")
            return redirect('product_detail', product_id=product_id)
        
        total_amount = product.price * quantity
        # Create the order (no product/quantity fields)
        order = Order.objects.create(
            user=user,
            seller=product.seller,
            total_amount=total_amount,
            status='pending'
        )
        # Create the order item
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price
        )
        # Optionally reduce stock here or after payment
        # product.stock -= quantity
        # product.save()
        request.session['order_id'] = order.id
        return redirect('payment', order_id=order.id)
    
    return redirect('product_detail', product_id=product_id)


@transaction.atomic
def payment_page(request, order_id):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login to complete payment")
        return redirect('login')
    
    order = get_object_or_404(Order, pk=order_id)
    if order.user.id != request.session['id']:
        messages.error(request, "You can only pay for your own orders")
        return redirect('user_view_products')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        if payment_method not in ['upi', 'card', 'cod']:
            messages.error(request, "Invalid payment method.")
            return render(request, 'user/payment.html', {'order': order})
        
        with transaction.atomic():
            payment_data = {
                'user': order.user,
                'order': order,
                'payment_method': payment_method,
                'amount': order.total_amount,
                'is_successful': True,
            }
            if payment_method == 'card':
                payment_data.update({
                    'transaction_id': f"card_{uuid.uuid4().hex[:10]}",
                    'card_holder_name': request.POST.get('card_holder_name'),
                    'card_number': request.POST.get('card_number')[-4:],
                    'card_expiry': request.POST.get('card_expiry'),
                    'card_cvv': request.POST.get('card_cvv'),
                })
            elif payment_method == 'upi':
                payment_data.update({
                    'transaction_id': f"upi_{uuid.uuid4().hex[:10]}",
                    'upi_id': request.POST.get('upi_id'),
                })
            else:  # COD
                payment_data.update({
                    'transaction_id': f"cod_{uuid.uuid4().hex[:10]}",
                })
            Payment.objects.create(**payment_data)

            order.status = 'completed'
            order.save()
            for item in order.items.all():
                item.product.stock -= item.quantity
                item.product.save()
                if payment_method != 'cod':
                    commission_amount = item.price * item.quantity * Decimal('0.05')
                    AdminCommission.objects.create(
                        product=item.product,
                        user=order.user,
                        seller=item.product.seller,
                        order=order,
                        amount=commission_amount
                    )
                if item.product.stock <= 2:
                    Notification.objects.create(
                        seller=item.product.seller,
                        product=item.product,
                        message=f"Product {item.product.name} is running low on stock. Current stock: {item.product.stock}"
                    )
            messages.success(request, "Payment successful! Your order has been placed.")
            return redirect('order_confirmation', order_id=order.id)
    
    return render(request, 'user/payment.html', {'order': order})

def order_confirmation(request, order_id):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login to view your orders")
        return redirect('login')
    
    order = get_object_or_404(Order, pk=order_id)
    if order.user.id != request.session['id']:
        messages.error(request, "You can only view your own orders")
        return redirect('user_view_products')
    
    payment = Payment.objects.filter(order=order).first()
    if not payment:
        messages.error(request, "No payment found for this order.")
        return redirect('payment', order_id=order.id)
    
    return render(request, 'user/order_confirmation.html', {
        'order': order, 
        'payment': payment,
        'user': order.user
    })



def add_to_cart(request, product_id):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login as a user to add items to cart")
        return redirect('login')
    
    product = get_object_or_404(Products, pk=product_id)
    user = tbl_register.objects.get(id=request.session['id'])
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        messages.error(request, "Invalid quantity")
        return redirect('product_detail', product_id=product_id)
    
    if product.stock < quantity:
        messages.error(request, "Not enough stock available")
        return redirect('product_detail', product_id=product_id)
    
    # Check if item already in cart
    cart_item, created = Cart.objects.get_or_create(
        user=user,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    messages.success(request, "Item added to cart successfully")
    return redirect('product_detail', product_id=product_id)

def view_cart(request):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login as a user to view your cart")
        return redirect('login')
    
    user = tbl_register.objects.get(id=request.session['id'])
    cart_items = Cart.objects.filter(user=user).select_related('product')
    
    total_price = sum(item.total_price for item in cart_items)
    
    return render(request, 'user/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })

def update_cart(request, cart_item_id):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    cart_item = get_object_or_404(Cart, pk=cart_item_id, user_id=request.session['id'])
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        Cart.objects.filter(id=cart_item_id).delete()
        return JsonResponse({'success': True, 'action': 'removed'})
    
    if cart_item.product.stock < quantity:
        return JsonResponse({'success': False, 'error': 'Not enough stock available'}, status=400)
    
    cart_item.quantity = quantity
    cart_item.save()
    
    return JsonResponse({
        'success': True,
        'action': 'updated',
        'item_total': cart_item.total_price
    })

def remove_from_cart(request, cart_item_id):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Authentication required")
        return redirect('login')
    
    cart_item = get_object_or_404(Cart, pk=cart_item_id, user_id=request.session['id'])
    cart_item.delete()
    
    messages.success(request, "Item removed from cart")
    return redirect('view_cart')


@transaction.atomic
def checkout(request):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login as a user to checkout")
        return redirect('login')
    
    user = tbl_register.objects.get(id=request.session['id'])
    cart_items = Cart.objects.filter(user=user).select_related('product')
    
    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect('product_list')
    
    # Check stock
    for item in cart_items:
        if item.product.stock < item.quantity:
            messages.error(request, f"Not enough stock for {item.product.name}")
            return redirect('view_cart')
    
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    order = Order.objects.create(
        user=user,
        total_amount=total_amount,
        status='pending'
    )
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )
        item.product.stock -= item.quantity
        item.product.save()
        if item.product.stock <= 2:
            Notification.objects.create(
                seller=item.product.seller,
                product=item.product,
                message=f"Product {item.product.name} is running low on stock. Current stock: {item.product.stock}"
            )
    cart_items.delete()
    return redirect('payment', order_id=order.id)


def order_summary(request):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login to view your orders")
        return redirect('login')
    order_ids = request.session.get('order_ids', [])
    orders = Order.objects.filter(id__in=order_ids, user_id=request.session['id'])
    return render(request, 'user/order_summary.html', {'orders': orders})




def order_history(request):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login to view your orders")
        return redirect('login')
    
    user_id = request.session['id']
    orders = Order.objects.filter(user_id=user_id).order_by('-order_date')
    
    # Get payment details for each order
    orders_with_payments = []
    for order in orders:
        try:
            payment = Payment.objects.get(order=order)
        except Payment.DoesNotExist:
            payment = None
        orders_with_payments.append({
            'order': order,
            'payment': payment
        })
    
    return render(request, 'user/order_history.html', {
        'orders_with_payments': orders_with_payments
    })

def order_detail(request, order_id):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login to view order details")
        return redirect('login')
    
    order = get_object_or_404(Order, pk=order_id, user_id=request.session['id'])
    
    try:
        payment = Payment.objects.get(order=order)
    except Payment.DoesNotExist:
        payment = None
    
    return render(request, 'user/order_detail.html', {
        'order': order,
        'payment': payment
    })



def view_video(request):
    videos = Video.objects.all()
    return render(request, 'user/videos.html', {'videos': videos})


#---------------------------------------------------- Seller  Module -------------------------------------------------------------------------------#
def seller_register(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')

        # Email validation
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format")
            return redirect('seller_register')

        # Phone number validation (10-15 digits)
        if not re.match(r'^\d{10,15}$', phone_number):
            messages.error(request, "Phone number must be 10-15 digits")
            return redirect('seller_register')

        # Password validation (min 8 chars, at least 1 letter and 1 number)
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$', password):
            messages.error(request, "Password must be at least 8 characters, include a letter and a number")
            return redirect('seller_register')

        if Seller.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('seller_register')

        if Seller.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already exists")
            return redirect('seller_register')

        seller = Seller.objects.create(
            name=name,
            email=email,
            password=password,
            phone_number=phone_number,
            address=address,
            status="pending"
        )
        seller.save()

        messages.success(request, "Registration successful. Please wait for admin approval.")
        return redirect('seller_register')

    return render(request, 'seller_register.html')


def seller_view_users(request):
    users = tbl_register.objects.all()  # Fetch all users
    return render(request, 'seller/view_users.html', {'users': users})

def view_feedback(request):
    feedbacks = Feedback.objects.all().order_by('-created_at')
    return render(request, 'seller/view_feedback.html', {'feedbacks': feedbacks})


def view_product(request):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller to view products")
        return redirect('login')
    
    seller_id = request.session['id']
    products = Products.objects.filter(seller_id=seller_id)
    return render(request, 'seller/view_product.html', {'products': products})

def add_product(request):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller to add products")
        return redirect('login')
    
    seller_id = request.session['id']
    
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        image = request.FILES.get('image')
        
        # Validate required fields
        if not all([name, description, price, stock]):
            messages.error(request, "Please fill all required fields")
            return redirect('add_product')
        
        try:
            Products.objects.create(
                name=name,
                description=description,
                price=float(price),
                stock=int(stock),
                image=image,
                seller_id=seller_id
            )
            messages.success(request, "Product added successfully")
            return redirect('view_product')
        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")
    
    return render(request, 'seller/add_product.html')

def delete_product(request, product_id):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller")
        return redirect('login')
    
    seller_id = request.session['id']
    product = get_object_or_404(Products, pk=product_id, seller_id=seller_id)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully")
        return redirect('view_product')
    
    return render(request, 'seller/confirm_delete.html', {'product': product})

def edit_product(request, product_id):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller")
        return redirect('login')
    
    seller_id = request.session['id']
    product = get_object_or_404(Products, id=product_id, seller_id=seller_id)

    if request.method == "POST":
        product.name = request.POST['name']
        product.stock = request.POST['stock']
        product.price = request.POST['price']
        product.description = request.POST['description']

        if 'image' in request.FILES:
            product.image = request.FILES['image']

        try:
            product.save()
            # Delete low stock notifications if stock is now 3 or more
            if int(product.stock) >= 3:
                Notification.objects.filter(product=product, seller=product.seller).delete()
            messages.success(request, "Product updated successfully")
            # Do NOT redirect, just render the same page
        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")

    return render(request, 'seller/edit_product.html', {'product': product})



def view_product_details(request, product_id):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller to view products")
        return redirect('login')
    
    product = get_object_or_404(Products, id=product_id)
    return render(request, 'seller/view_product_details.html', {'product': product})


def view_product_list(request):
    return render(request, 'seller/product_list.html')


def seller_view_videos(request):
    videos = Video.objects.all()
    return render(request, 'seller/seller_view_video.html', {'videos': videos})

def seller_orders(request):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller to view orders")
        return redirect('login')
    
    seller_id = request.session['id']
    orders = (
        Order.objects
             .filter(seller_id=seller_id)
             .select_related('user')                      # 1 query for each related user
             .prefetch_related(
                 Prefetch('items', queryset=OrderItem.objects.select_related('product'))
             )                                            # 1 query for all items+products
             .order_by('-order_date')
    )

    orders_with_payments = []
    for order in orders:
        payment = Payment.objects.filter(order=order).first()   # returns None if not found
        orders_with_payments.append({'order': order,
                                     'payment': payment})

    return render(request, 'seller/orders.html',
                  {'orders_with_payments': orders_with_payments})

def seller_order_detail(request, order_id):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller to view order details")
        return redirect('login')
    
    seller_id = request.session['id']
    order = get_object_or_404(Order, pk=order_id, seller_id=seller_id)
    
    try:
        payment = Payment.objects.get(order=order)
    except Payment.DoesNotExist:
        payment = None
    
    return render(request, 'seller/order_detail.html', {
        'order': order,
        'payment': payment
    })


def seller_notifications(request):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller to view notifications")
        return redirect('login')
    
    seller_id = request.session['id']
    notifications = Notification.objects.filter(seller_id=seller_id).order_by('-created_at')
    
    # Mark notifications as read when viewed (optional)
    if request.method == 'GET':
        Notification.objects.filter(seller_id=seller_id, is_read=False).update(is_read=True)
    
    return render(request, 'seller/notifications.html', {
        'notifications': notifications
    })

def view_notification(request, notification_id):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please login as a seller")
        return redirect('login')
    
    notification = get_object_or_404(
        Notification, 
        pk=notification_id, 
        seller_id=request.session['id']
    )
    
    # Mark as read when viewed
    notification.is_read = True
    notification.save()
    
    # Get current stock level (in case it changed since notification)
    current_stock = notification.product.stock
    
    return render(request, 'seller/notification_detail.html', {
        'notification': notification,
        'current_stock': current_stock
    })


def seller_profile_view(request):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please log in as a seller.")
        return redirect('login')

    seller = get_object_or_404(Seller, pk=request.session['id'])
    return render(request, 'seller/profile.html', {'seller': seller})


def seller_profile_edit(request):
    if 'id' not in request.session or request.session.get('user_type') != 'seller':
        messages.error(request, "Please log in as a seller.")
        return redirect('login')

    seller = get_object_or_404(Seller, pk=request.session['id'])

    if request.method == 'POST':
        seller.name = request.POST.get('name')
        seller.email = request.POST.get('email')
        seller.phone_number = request.POST.get('phone_number')
        seller.address = request.POST.get('address')
        seller.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('seller_profile')

    return render(request, 'seller/profile_edit.html', {'seller': seller})








#---------------------------------------------------- Admin  Module -------------------------------------------------------------------------------#




def admin_view_users(request):
    users = tbl_register.objects.all()  # Fetch all users
    return render(request, 'admin/view_users.html', {'users': users})



def admin_view_pending_sellers(request):
    pending_sellers = Seller.objects.filter(status='pending')  # Get only pending sellers
    return render(request, 'admin/view_pending_sellers.html', {'pending_sellers': pending_sellers})

def approve_seller(request, seller_id):
    seller = Seller.objects.get(id=seller_id)
    seller.status = 'approved'
    seller.save()
    messages.success(request, f"Seller {seller.name} has been approved!")
    return redirect('admin_view_approved_sellers')

def reject_seller(request, seller_id):
    seller = Seller.objects.get(id=seller_id)
    seller.status = 'rejected'
    seller.save()
    messages.error(request, f"Seller {seller.name} has been rejected!")
    return redirect('admin_view_rejected_sellers')



def admin_view_approved_sellers(request):
    approved_sellers = Seller.objects.filter(status='approved')  # Fetch approved sellers
    return render(request, 'admin/view_approved_sellers.html', {'approved_sellers': approved_sellers})

def admin_view_rejected_sellers(request):
    rejected_sellers = Seller.objects.filter(status='rejected')  # Fetch rejected sellers
    return render(request, 'admin/view_rejected_sellers.html', {'rejected_sellers': rejected_sellers})




def admin_view_feedback(request):
    if request.method == "POST":
        feedback_id = request.POST.get('feedback_id')
        admin_reply = request.POST.get('admin_reply')
        if feedback_id and admin_reply is not None:
            try:
                feedback = Feedback.objects.get(id=feedback_id)
                feedback.admin_reply = admin_reply
                feedback.save()
                messages.success(request, "Reply saved successfully.")
            except Feedback.DoesNotExist:
                messages.error(request, "Feedback not found.")
        else:
            messages.error(request, "Please provide a reply.")

    feedbacks = Feedback.objects.all().order_by('-created_at')
    return render(request, 'admin/view_feedback.html', {'feedbacks': feedbacks})


def edit_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        video_file = request.FILES.get('video_file')

        video.title = title
        video.description = description
        if video_file:
            video.video_file = video_file
        video.save()
        messages.success(request, "Video updated successfully.")
        return redirect('view_videos')  # Change to your video list view name

    return render(request, 'admin/edit_video.html', {'video': video})

    
def feedback_list(request, seller_id):
    seller = get_object_or_404(Seller, id=seller_id)
    feedbacks=seller.feedbacks.values("customer_name", "rating", "comments", "created_at")
    return JsonResponse(list(feedbacks), safe=False)




def add_video(request):
    if request.method == 'POST':
        title = request.POST.get('videoName')
        description = request.POST.get('videoDescription')
        video_file = request.FILES.get('videoInput')

        if not title or not description or not video_file:
            return render(request, 'admin/add_video.html', {'error': 'All fields are required!'})

        # Save to database
      
        Video.objects.create(title=title, description=description, video_file=video_file)
        messages.success(request, 'Video added successfully!')

        return redirect('add_video')

    videos = Video.objects.all()
    return render(request, 'admin/add_video.html', {'videos': videos})


def view_videos(request):
    videos = Video.objects.all()
    return render(request, 'admin/view_video.html', {'videos': videos})


def delete_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    video.delete()
    messages.success(request, 'Video deleted successfully!')
    return redirect('view_videos')





def products(request):
    products = Products.objects.all()
    return render(request, 'admin/products.html', {'products': products})






















# def view_products(request):
#     all_products = Products.objects.all()
#     return render(request, 'user/view_product.html', {'products': all_products})




# def product_list(request):
#     products = Products.objects.filter(stock__gt=0)
#     return render(request, 'user/view_product.html', {'products': products})

# def product_detail(request, product_id):
#     product = get_object_or_404(Products, pk=product_id)
#     return render(request, 'user/product_detail.html', {'product': product})



def is_admin_session(request):
    """Check if current session user is admin"""
    if 'id' not in request.session or request.session.get('user_type') != 'admin':
        return False
    try:
        return Admin.objects.filter(id=request.session['id']).exists()
    except:
        return False

def commission_list(request):
    # Check admin session
    if not is_admin_session(request):
        messages.error(request, "You need to login as admin to access this page")
        return redirect('login')
    
    commissions = AdminCommission.objects.all()
    
    # Calculate total commissions
    total_commissions = commissions.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'commissions': commissions,
        'total_commissions': total_commissions,
    }
    return render(request, 'admin/commission_list.html', context)

def commission_detail(request, commission_id):
    if not is_admin_session(request):
        messages.error(request, "You need to login as admin to access this page")
        return redirect('login')

    commission = get_object_or_404(AdminCommission, pk=commission_id)

    # grab all order items, including product in one query
    order_items = commission.order.items.select_related('product')

    context = {
        'commission': commission,
        'order_items': order_items,
    }
    return render(request, 'admin/commission_detail.html', context)

















def profile_view(request):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login to view your profile")
        return redirect('login')
    user = get_object_or_404(tbl_register, id=request.session['id'])
    return render(request, 'user/profile.html', {'user': user})
def edit_profile(request):
    if 'id' not in request.session or request.session.get('user_type') != 'user':
        messages.error(request, "Please login to edit your profile")
        return redirect('login')
    user = get_object_or_404(tbl_register, id=request.session['id'])
    if request.method == 'POST':
        user.name = request.POST['name']
        user.email = request.POST['email']
        user.phone_number = request.POST['phone_number']
        user.address = request.POST['address']
        try:
            user.save()
            messages.success(request, "Profile updated successfully")
            # Do NOT redirect, just render the same page so message shows
        except Exception as e:
            messages.error(request, f"Error updating profile: {e}")
    return render(request, 'user/edit_profile.html', {'user': user})