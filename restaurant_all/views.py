from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from restaurant_all.forms import (
    AdminEmailLoginForm,
    BootstrapSuperuserForm,
    LoginForm,
    RegistrationForm,
)
from restaurant_all.models import CartItem, Dish, DishRating, Order, OrderItem


def _migrate_session_cart(request):
    legacy_cart = request.session.get("cart")
    if not isinstance(legacy_cart, dict):
        return

    for dish_id, quantity in legacy_cart.items():
        try:
            dish_pk = int(dish_id)
            item_quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if item_quantity < 1:
            continue
        dish = Dish.objects.filter(pk=dish_pk).first()
        if dish is not None:
            CartItem.objects.get_or_create(
                user=request.user,
                dish=dish,
                defaults={"quantity": item_quantity},
            )
    del request.session["cart"]


def auth_page(request):
    if request.user.is_authenticated:
        return redirect("home")

    registration_form = RegistrationForm()
    login_form = LoginForm(request=request)

    if request.method == "POST":
        if request.POST.get("action") == "register":
            registration_form = RegistrationForm(request.POST)
            if registration_form.is_valid():
                user = registration_form.save()
                login(request, user, backend="restaurant_all.authentication.PhoneOrEmailBackend")
                return redirect("home")
        elif request.POST.get("action") == "login":
            login_form = LoginForm(request=request, data=request.POST)
            if login_form.is_valid():
                login(request, login_form.get_user())
                return redirect("home")

    return render(
        request,
        "autentification.html",
        {
            "registration_form": registration_form,
            "login_form": login_form,
        },
    )


def admin_authentification(request):
    user_model = get_user_model()
    registration_open = not user_model._default_manager.filter(
        is_superuser=True
    ).exists()
    registration_form = BootstrapSuperuserForm()
    login_form = AdminEmailLoginForm(request=request)

    if request.method == "POST":
        if request.POST.get("action") == "register" and registration_open:
            registration_form = BootstrapSuperuserForm(request.POST)
            if registration_form.is_valid():
                try:
                    user = registration_form.save()
                except ValidationError as error:
                    registration_form.add_error(None, error)
                else:
                    login(
                        request,
                        user,
                        backend="restaurant_all.authentication.PhoneOrEmailBackend",
                    )
                    return redirect("admin:index")
        elif request.POST.get("action") == "login":
            login_form = AdminEmailLoginForm(request=request, data=request.POST)
            if login_form.is_valid():
                login(
                    request,
                    login_form.get_user(),
                    backend="restaurant_all.authentication.PhoneOrEmailBackend",
                )
                return redirect("admin:index")

    registration_open = not user_model._default_manager.filter(
        is_superuser=True
    ).exists()
    return render(
        request,
        "admin_authentification.html",
        {
            "registration_form": registration_form,
            "login_form": login_form,
            "registration_open": registration_open,
        },
    )


@login_required
def home(request):
    user = request.user
    return render(
        request,
        "main_page.html",
        {
            "display_name": user.get_full_name() or user.get_username(),
            "greeting_name": user.first_name or user.get_username(),
        },
    )


@login_required
def menu_page(request):
    selected_category = request.GET.get("category", "")
    valid_categories = dict(Dish.Category.choices)
    if selected_category not in valid_categories:
        selected_category = ""

    dishes = Dish.objects.annotate(
        average_rating=Avg("ratings__score"),
        rating_count=Count(
            "ratings",
            filter=Q(ratings__score__isnull=False),
        ),
    )
    if selected_category:
        dishes = dishes.filter(category=selected_category)
    dishes = dishes.prefetch_related(
        Prefetch(
            "ratings",
            queryset=DishRating.objects.exclude(comment="")
            .select_related("user")
            .order_by("-pk"),
            to_attr="comment_reviews",
        )
    )

    return render(
        request,
        "menu.html",
        {
            "dishes": dishes,
            "categories": Dish.Category.choices,
            "selected_category": selected_category,
        },
    )


@login_required
def order_page(request):
    _migrate_session_cart(request)
    cart_items = []
    total = 0
    for cart_item in CartItem.objects.filter(user=request.user).select_related("dish"):
        line_total = cart_item.dish.price * cart_item.quantity
        cart_items.append(
            {
                "cart_item": cart_item,
                "dish": cart_item.dish,
                "quantity": cart_item.quantity,
                "line_total": line_total,
            }
        )
        total += line_total
    return render(
        request,
        "order.html",
        {"cart_items": cart_items, "cart_total": total},
    )


@login_required
def dish_detail(request, dish_id):
    dish = get_object_or_404(Dish, pk=dish_id)
    return render(request, "dish_detail.html", {"dish": dish})


@login_required
@require_POST
def add_to_cart(request, dish_id):
    dish = get_object_or_404(Dish, pk=dish_id)
    if not dish.is_available:
        messages.error(request, f"«{dish.name}» наразі немає в наявності.")
        return redirect("menu")

    _migrate_session_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        dish=dish,
        defaults={"quantity": 1},
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save(update_fields=["quantity"])
    messages.success(request, f"«{dish.name}» додано до кошика.")
    return redirect("menu")


@login_required
@require_POST
def update_cart_item(request, dish_id):
    _migrate_session_cart(request)
    cart_item = get_object_or_404(
        CartItem,
        user=request.user,
        dish_id=dish_id,
    )
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if "delta" in request.POST:
        try:
            delta = int(request.POST["delta"])
        except ValueError:
            delta = 0
        if delta not in (-1, 1):
            if is_ajax:
                return JsonResponse(
                    {"error": "Некоректна зміна кількості."},
                    status=400,
                )
            messages.error(request, "Некоректна зміна кількості.")
            return redirect("order")
        quantity = max(1, cart_item.quantity + delta)
    else:
        try:
            quantity = int(request.POST.get("quantity", ""))
        except ValueError:
            if is_ajax:
                return JsonResponse(
                    {"error": "Вкажіть коректну кількість страви."},
                    status=400,
                )
            messages.error(request, "Вкажіть коректну кількість страви.")
            return redirect("order")
    if quantity < 1:
        if is_ajax:
            return JsonResponse(
                {"error": "Кількість має бути не меншою за 1."},
                status=400,
            )
        messages.error(request, "Кількість має бути не меншою за 1.")
        return redirect("order")

    cart_item.quantity = quantity
    cart_item.save(update_fields=["quantity"])
    if is_ajax:
        cart_total = sum(
            (
                item.dish.price * item.quantity
                for item in CartItem.objects.filter(user=request.user).select_related(
                    "dish"
                )
            ),
            start=cart_item.dish.price * 0,
        )
        return JsonResponse(
            {
                "quantity": cart_item.quantity,
                "line_total": f"{cart_item.dish.price * cart_item.quantity:.2f}",
                "cart_total": f"{cart_total:.2f}",
            }
        )
    messages.success(request, "Кількість страви оновлено.")
    return redirect("order")


@login_required
@require_POST
def remove_cart_item(request, dish_id):
    _migrate_session_cart(request)
    CartItem.objects.filter(user=request.user, dish_id=dish_id).delete()
    messages.success(request, "Страву видалено з кошика.")
    return redirect("order")


def _get_cart_summary(user):
    cart_items = []
    total = 0
    for cart_item in CartItem.objects.filter(user=user).select_related("dish"):
        line_total = cart_item.dish.price * cart_item.quantity
        cart_items.append(
            {
                "cart_item": cart_item,
                "dish": cart_item.dish,
                "quantity": cart_item.quantity,
                "line_total": line_total,
            }
        )
        total += line_total
    return cart_items, total


@login_required
def create_order_page(request):
    _migrate_session_cart(request)
    cart_items, total = _get_cart_summary(request.user)

    if request.method == "POST":
        if not cart_items:
            messages.error(request, "Кошик порожній. Додайте страви перед оформленням.")
            return redirect("menu")

        address = (request.POST.get("address") or "").strip()
        if not address:
            messages.error(request, "Вкажіть адресу доставки.")
            return render(
                request,
                "create_order.html",
                {
                    "cart_items": cart_items,
                    "cart_total": total,
                    "customer_name": request.POST.get("customer_name") or request.user.get_full_name() or request.user.get_username(),
                    "phone": request.POST.get("phone") or getattr(getattr(request.user, "client_profile", None), "phone", ""),
                    "delivery_address": "",
                },
            )

        order = Order.objects.create(
            user=request.user,
            customer_name=(request.POST.get("customer_name") or request.user.get_full_name() or request.user.get_username()).strip(),
            phone=(request.POST.get("phone") or getattr(getattr(request.user, "client_profile", None), "phone", "")).strip(),
            address=address,
            payment_method=(request.POST.get("payment_method") or "cash").strip(),
            comment=(request.POST.get("comment") or "").strip(),
            total_price=total,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                dish=item["dish"],
                quantity=item["quantity"],
                unit_price=item["dish"].price,
            )

        CartItem.objects.filter(user=request.user).delete()
        messages.success(request, "Замовлення успішно оформлено. Очікуйте дзвінок від оператора.")
        return redirect("order_history")

    return render(
        request,
        "create_order.html",
        {
            "cart_items": cart_items,
            "cart_total": total,
            "customer_name": request.user.get_full_name() or request.user.get_username(),
            "phone": getattr(getattr(request.user, "client_profile", None), "phone", ""),
            "delivery_address": "",
        },
    )


@login_required
def order_history(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items__dish")
        .order_by("-created_at")
    )
    return render(request, "order_history.html", {"orders": orders})


@login_required
@require_POST
def reorder_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    for item in order.items.select_related("dish"):
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            dish=item.dish,
            defaults={"quantity": item.quantity},
        )
        if not created and cart_item.quantity != item.quantity:
            cart_item.quantity = item.quantity
            cart_item.save(update_fields=["quantity"])

    messages.success(request, "Замовлення повторно додано до кошика.")
    return redirect("order")


@login_required
def raiting_page(request):
    user = request.user
    selected_rating = request.GET.get("rating", "")
    if selected_rating not in {"", "1", "2", "3", "4", "5"}:
        selected_rating = ""

    dishes = Dish.objects.annotate(
        average_rating=Avg("ratings__score"),
        rating_count=Count(
            "ratings",
            filter=Q(ratings__score__isnull=False),
        ),
    )
    if selected_rating:
        dishes = dishes.filter(average_rating__gte=int(selected_rating))

    dishes = list(dishes)
    ratings_by_dish = {}
    for rating in DishRating.objects.filter(dish__in=dishes).select_related("user"):
        ratings_by_dish.setdefault(rating.dish_id, []).append(rating)
    for dish in dishes:
        dish.user_rating = None
        dish.user_comment = ""
        dish.comments = []
        for current_rating in ratings_by_dish.get(dish.pk, []):
            if current_rating.user_id == user.pk:
                dish.user_rating = current_rating.score
                dish.user_comment = current_rating.comment
            if current_rating.comment.strip():
                dish.comments.append(current_rating)

    return render(
        request,
        "raiting.html",
        {
            "display_name": user.get_full_name() or user.get_username(),
            "dishes": dishes,
            "selected_rating": selected_rating,
            "rating_options": range(1, 6),
        },
    )


@login_required
@require_POST
def rate_dish(request, dish_id):
    dish = get_object_or_404(Dish, pk=dish_id)
    rating_filter = request.POST.get("rating_filter", "")
    if rating_filter not in {"", "1", "2", "3", "4", "5"}:
        rating_filter = ""

    comment = request.POST.get("comment", "").strip()
    try:
        score = int(request.POST.get("score", ""))
    except (TypeError, ValueError):
        score = 0

    if score not in range(1, 6) and not comment:
        messages.error(request, "Оберіть оцінку від 1 до 5 зірок.")
    else:
        if score in range(1, 6):
            rating, _ = DishRating.objects.get_or_create(
                user=request.user,
                dish=dish,
            )
            rating.score = score
            if comment:
                rating.comment = comment
            rating.save(update_fields=["score", "comment"])
        else:
            rating, _ = DishRating.objects.get_or_create(
                user=request.user,
                dish=dish,
            )
            rating.comment = comment
            rating.save(update_fields=["comment"])
        if comment:
            messages.success(request, f"Відгук для «{dish.name}» збережено.")
        else:
            messages.success(request, f"Оцінку для «{dish.name}» збережено.")

    redirect_url = reverse("raiting")
    if rating_filter:
        redirect_url = f"{redirect_url}?rating={rating_filter}"
    return redirect(redirect_url)


@login_required
@require_POST
def comment_dish(request, dish_id=None):
    if dish_id is None:
        try:
            dish_id = int(request.POST.get("dish_id", ""))
        except (TypeError, ValueError):
            dish_id = 0

    dish = get_object_or_404(Dish, pk=dish_id)
    comment = request.POST.get("comment", "").strip()
    if not comment:
        messages.error(request, "Напишіть текст відгуку.")
        return redirect("raiting")

    rating, _ = DishRating.objects.get_or_create(
        user=request.user,
        dish=dish,
    )
    rating.comment = comment
    rating.save(update_fields=["comment"])
    messages.success(request, f"Відгук для «{dish.name}» збережено.")
    return redirect("raiting")


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Ви вийшли з облікового запису.")
    return redirect("auth")
