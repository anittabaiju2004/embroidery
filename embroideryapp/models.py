from django.db import models
from django.core.validators import MinValueValidator

class Admin(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class tbl_register(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, max_length=191)
    password = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    address = models.TextField()

    def __str__(self):
        return self.name

class Seller(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return self.name

class Products(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    price = models.DecimalField(decimal_places=2, max_digits=10)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.name} (Seller ID: {self.seller.id})"

class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(tbl_register, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, null=True, blank=True)  # Optional, or remove if not needed
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Order #{self.id} by {self.user.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
class Payment(models.Model):
    PAYMENT_METHODS = [
        ('upi', 'UPI'),
        ('card', 'Credit/Debit Card'),
        ('cod', 'Cash on Delivery'),
    ]
    
    user = models.ForeignKey(tbl_register, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    # seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)
    
    # Card payment fields
    card_holder_name = models.CharField(max_length=100, null=True, blank=True)
    card_number = models.CharField(max_length=16, null=True, blank=True)
    card_expiry = models.CharField(max_length=5, null=True, blank=True)  # MM/YY format
    card_cvv = models.CharField(max_length=4, null=True, blank=True)
    
    # UPI payment fields
    upi_id = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return f"Payment for Order #{self.order.id}"

class Notification(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Notification for {self.seller.name} - {self.message[:50]}"

class AdminCommission(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    user = models.ForeignKey(tbl_register, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"Commission for Order #{self.order.id} - {self.amount}"


class Cart(models.Model):
    user = models.ForeignKey(tbl_register, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')  # Prevent duplicate items in cart
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} for {self.user.name}"
    
    @property
    def total_price(self):
        return self.product.price * self.quantity
    
class Feedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]

    user = models.ForeignKey('tbl_register', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, default="Anonymous")
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    admin_reply = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.rating} Stars"
    
class Video(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title