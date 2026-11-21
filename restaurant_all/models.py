from django.db import models
from django.conf import settings

class Dish(models.Model):
    class Category(models.TextChoices):
        SALADS = "salads", "Салати"
        MAIN = "main", "Основні страви"
        DESSERTS = "desserts", "Десерти"
        DRINKS = "drinks", "Напої"

    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(upload_to='dish_images/', blank=True, null=True)
    is_available = models.BooleanField("Є в наявності", default=True)
    category = models.CharField(
        "Категорія",
        max_length=16,
        choices=Category.choices,
        default=Category.MAIN,
    )

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )
    customer_name = models.CharField(max_length=150, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    payment_method = models.CharField(max_length=32, default="cash")
    comment = models.TextField(blank=True, default="")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name or self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    dish = models.ForeignKey(Dish, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} × {self.dish.name}"


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "dish"),
                name="unique_user_cart_dish",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.dish.name} ({self.user})"


class DishRating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dish_ratings",
    )
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    score = models.PositiveSmallIntegerField(blank=True, null=True)
    comment = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "dish"),
                name="unique_user_dish_rating",
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=1, score__lte=5),
                name="dish_rating_score_1_to_5",
            ),
        ]

    def __str__(self):
        return f"{self.score} зірок — {self.dish.name} ({self.user})"


class Administarator(models.Model):
    username = models.CharField(max_length=50)
    email = models.EmailField()
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.username

class Client(models.Model):
    username = models.CharField(max_length=50)
    email = models.EmailField()
    password = models.CharField(max_length=100)
    home_address = models.CharField(max_length=200)

    def __str__(self):
        return self.username


class ClientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_profile",
    )
    phone = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email
