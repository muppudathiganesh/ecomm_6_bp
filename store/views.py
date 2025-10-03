from django.shortcuts import render, redirect, get_object_or_404
from .models import Category, Product, CartItem, Order
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import razorpay
from django.conf import settings
from reportlab.pdfgen import canvas
from django.http import HttpResponse

# Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def home(request):
    categories = Category.objects.all()
    products = Product.objects.all()
    return render(request, 'store/home.html', {'categories': categories, 'products': products})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('cart')

@login_required
def cart(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum([item.product.price * item.quantity for item in items])
    return render(request, 'store/cart.html', {'items': items, 'total': total})



# Payment success webhook
@login_required
def payment_success(request, order_id, payment_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(request, "store/payment_success.html", {
        "order": order,
        "payment_id": payment_id
    })


# Generate PDF invoice
def generate_invoice(order):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

    c = canvas.Canvas(response)
    c.drawString(100, 800, f"GST Invoice for Order #{order.id}")
    c.drawString(100, 780, f"Customer: {order.user.username}")
    c.drawString(100, 760, f"Total Amount: ₹{order.total_amount}")
    c.drawString(100, 740, "Products:")
    y = 720
    for item in order.products.all():
        c.drawString(120, y, f"{item.product.name} x {item.quantity} = ₹{item.product.price*item.quantity}")
        y -= 20
    c.showPage()
    c.save()
    return response



def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "increase":
            item.quantity += 1
        elif action == "decrease" and item.quantity > 1:
            item.quantity -= 1
        item.save()
    return redirect('cart')


def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.method == "POST":
        item.delete()
    return redirect('cart')

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Order, CartItem

@login_required
def checkout(request):
    # Get cart items
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        return redirect('cart')  # No items in cart

    # Calculate total
    total_amount = sum(item.product.price * item.quantity for item in cart_items)

    # Create a test order
    order = Order.objects.create(
        user=request.user,
        total_amount=total_amount,
        status="Pending"
    )
    order.products.set(cart_items)

    # Simulate successful payment
    order.status = "Paid"
    order.razorpay_order_id = "TEST_ORDER_123"
    order.razorpay_payment_id = "TEST_PAY_456"
    order.save()

    return render(request, "store/payment_success.html", {"order": order})

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .forms import RegisterForm, LoginForm

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])  # hash password
            user.save()
            messages.success(request, "Account created successfully! Please login.")
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, "store/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome {user.username}!")
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password")
    else:
        form = LoginForm()
    return render(request, "store/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have logged out successfully.")
    return redirect('login')
