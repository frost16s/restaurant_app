from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from restaurant_all.models import CartItem, ClientProfile, Dish, DishRating, Order


class AuthenticationFlowTests(TestCase):
    registration_data = {
        "action": "register",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "phone": "+380 501234567",
        "email": "ada@example.com",
        "password": "B0b!C4t#R8v$M2x",
        "password_confirm": "B0b!C4t#R8v$M2x",
    }

    def test_root_displays_authentication_page(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Номер телефону")
        self.assertContains(response, "Електронна пошта")
        self.assertContains(response, "Ім’я")
        self.assertContains(response, "Прізвище")
        self.assertContains(response, reverse("admin_authentification"))

    def test_first_superuser_can_register_with_email_and_password(self):
        response = self.client.get(reverse("admin_authentification"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Створити superuser")

        response = self.client.post(
            reverse("admin_authentification"),
            {
                "action": "register",
                "email": "admin@example.com",
                "password": "B0b!C4t#R8v$M2x",
            },
        )

        self.assertRedirects(response, reverse("admin:index"))
        self.assertTrue(self.client.session.get("_auth_user_id"))
        user = get_user_model().objects.get(email="admin@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("B0b!C4t#R8v$M2x"))

        self.client.post(reverse("logout"))
        response = self.client.post(
            reverse("admin_authentification"),
            {
                "action": "login",
                "username": "admin@example.com",
                "password": "B0b!C4t#R8v$M2x",
            },
        )
        self.assertRedirects(response, reverse("admin:index"))

    def test_superuser_registration_closes_after_first_account(self):
        get_user_model().objects.create_superuser(
            username="first-admin@example.com",
            email="first-admin@example.com",
            password="B0b!C4t#R8v$M2x",
        )

        response = self.client.get(reverse("admin_authentification"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Створити superuser")

        response = self.client.post(
            reverse("admin_authentification"),
            {
                "action": "register",
                "email": "second-admin@example.com",
                "password": "B0b!C4t#R8v$M2x",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(email="second-admin@example.com").exists()
        )

    def test_admin_login_requires_superuser(self):
        get_user_model().objects.create_user(
            username="regular@example.com",
            email="regular@example.com",
            password="B0b!C4t#R8v$M2x",
        )

        response = self.client.post(
            reverse("admin_authentification"),
            {
                "action": "login",
                "username": "regular@example.com",
                "password": "B0b!C4t#R8v$M2x",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_admin_login_uses_nickname_instead_of_email(self):
        get_user_model().objects.create_superuser(
            username="Admin_frost",
            email="admin@example.com",
            password="B0b!C4t#R8v$M2x",
        )

        response = self.client.get(reverse("admin_authentification"))
        self.assertContains(response, "Нікнейм")
        self.assertContains(response, "Введіть нікнейм та пароль superuser.")

        response = self.client.post(
            reverse("admin_authentification"),
            {
                "action": "login",
                "username": "Admin_frost",
                "password": "B0b!C4t#R8v$M2x",
            },
        )
        self.assertRedirects(response, reverse("admin:index"))

        self.client.post(reverse("logout"))
        response = self.client.post(
            reverse("admin_authentification"),
            {
                "action": "login",
                "username": "admin@example.com",
                "password": "B0b!C4t#R8v$M2x",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("_auth_user_id"))


    def test_registration_creates_account_and_opens_home(self):
        response = self.client.post("/", self.registration_data)

        self.assertRedirects(response, "/home/")
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertContains(self.client.get("/home/"), "Вітаємо, Ada!")

        user = get_user_model().objects.get(email="ada@example.com")
        self.assertTrue(user.check_password(self.registration_data["password"]))
        self.assertEqual(user.client_profile.phone, "+380501234567")
        self.assertTrue(ClientProfile.objects.filter(user=user).exists())

    def test_login_accepts_email_or_phone(self):
        self.client.post("/", self.registration_data)
        self.client.post("/logout/")

        for identifier in ("ada@example.com", " +380 (50) 123-45-67 "):
            response = self.client.post(
                "/",
                {
                    "action": "login",
                    "username": identifier,
                    "password": self.registration_data["password"],
                },
            )
            self.assertRedirects(response, "/home/")
            self.client.post("/logout/")

    def test_home_requires_authentication(self):
        response = self.client.get("/home/")

        self.assertRedirects(response, "/?next=/home/")

    def test_home_shows_account_and_navigation(self):
        self.client.post("/", self.registration_data)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Ada Lovelace")
        self.assertContains(response, reverse("logout"))
        self.assertContains(response, reverse("menu"))
        self.assertContains(response, reverse("order"))
        self.assertContains(response, reverse("create_order"))
        self.assertContains(response, reverse("raiting"))

    def test_home_navigation_pages_require_login_and_render(self):
        for page_name in ("menu", "order", "create_order", "order_history", "raiting"):
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertRedirects(response, f"/?next={reverse(page_name)}")

        self.client.post("/", self.registration_data)
        for page_name in ("menu", "order", "create_order", "order_history", "raiting"):
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 200)
                if page_name == "raiting":
                    self.assertContains(response, "Рейтинг страв")
                    self.assertContains(response, "Оцінок поки немає")

    def test_menu_shows_dish_card_recipe_link_and_add_to_cart(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)

        response = self.client.get(reverse("menu"))

        self.assertContains(response, "Борщ")
        self.assertContains(response, "120.00")
        self.assertContains(response, "Є в наявності")
        self.assertContains(response, reverse("dish_detail", args=[dish.pk]))
        self.assertContains(response, reverse("add_to_cart", args=[dish.pk]))
        self.assertContains(response, "Ще немає оцінок")

    def test_rating_can_be_added_and_updated_by_user(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)

        response = self.client.post(
            reverse("rate_dish", args=[dish.pk]),
            {"score": "3"},
        )
        self.assertRedirects(response, reverse("raiting"))
        rating = DishRating.objects.get(dish=dish)
        self.assertEqual(rating.score, 3)

        self.client.post(
            reverse("rate_dish", args=[dish.pk]),
            {"score": "5"},
        )
        self.assertEqual(DishRating.objects.filter(dish=dish).count(), 1)
        self.assertEqual(DishRating.objects.get(dish=dish).score, 5)

    def test_rating_rejects_scores_outside_one_to_five(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)

        response = self.client.post(
            reverse("rate_dish", args=[dish.pk]),
            {"score": "6"},
            follow=True,
        )

        self.assertContains(response, "Оберіть оцінку від 1 до 5 зірок.")
        self.assertFalse(DishRating.objects.filter(dish=dish).exists())

    def test_rating_filter_uses_average_and_menu_displays_it(self):
        highest = Dish.objects.create(
            name="Вареники",
            description="З картоплею",
            price="150.00",
        )
        four_average = Dish.objects.create(
            name="Банош",
            description="З бринзою",
            price="130.00",
        )
        self.client.post("/", self.registration_data)
        current_user = get_user_model().objects.get(email=self.registration_data["email"])
        another_user = get_user_model().objects.create_user(
            username="second@example.com",
            email="second@example.com",
            password="B0b!C4t#R8v$M2x",
        )
        DishRating.objects.create(user=current_user, dish=highest, score=5)
        DishRating.objects.create(user=current_user, dish=four_average, score=3)
        DishRating.objects.create(user=another_user, dish=four_average, score=5)

        four_star_response = self.client.get(reverse("raiting"), {"rating": "4"})
        self.assertContains(four_star_response, "Банош")
        self.assertContains(four_star_response, "Вареники")

        five_star_response = self.client.get(reverse("raiting"), {"rating": "5"})
        self.assertContains(five_star_response, "Вареники")
        self.assertNotContains(five_star_response, "Банош")

        menu_response = self.client.get(reverse("menu"))
        self.assertContains(menu_response, "4.0 / 5")

    def test_menu_category_filter_shows_matching_dishes(self):
        salad = Dish.objects.create(
            name="Салат",
            description="Свіжий салат",
            price="100.00",
            category=Dish.Category.SALADS,
        )
        Dish.objects.create(
            name="Борщ",
            description="Основна страва",
            price="120.00",
            category=Dish.Category.MAIN,
        )
        self.client.post("/", self.registration_data)

        response = self.client.get(
            reverse("menu"),
            {"category": Dish.Category.SALADS},
        )

        self.assertContains(response, salad.name)
        self.assertNotContains(response, "Борщ")
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, "Усі страви")

    def test_empty_menu_category_offers_all_dishes(self):
        self.client.post("/", self.registration_data)

        response = self.client.get(
            reverse("menu"),
            {"category": Dish.Category.DESSERTS},
        )

        self.assertContains(response, "У цій категорії поки немає страв")
        self.assertContains(response, reverse("menu"))

    def test_unavailable_dish_is_labeled_and_cannot_be_added_to_cart(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
            is_available=False,
        )
        self.client.post("/", self.registration_data)

        response = self.client.get(reverse("menu"))

        self.assertContains(response, "Немає в наявності")
        self.assertContains(response, 'type="submit" disabled')

        response = self.client.post(reverse("add_to_cart", args=[dish.pk]), follow=True)

        self.assertContains(response, "«Борщ» наразі немає в наявності.")
        self.assertFalse(CartItem.objects.filter(dish=dish).exists())

    def test_add_to_cart_and_display_cart(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)

        response = self.client.post(
            reverse("add_to_cart", args=[dish.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        cart_response = self.client.get(reverse("order"))
        self.assertContains(cart_response, "Борщ")
        self.assertContains(cart_response, "120.00")
        self.assertContains(
            cart_response,
            f'href="{reverse("create_order")}"',
        )
        self.assertContains(cart_response, "Редагувати кошик")
        self.assertContains(cart_response, 'class="cart-item-controls" hidden')
        self.assertContains(cart_response, reverse("update_cart_item", args=[dish.pk]))
        self.assertContains(cart_response, reverse("remove_cart_item", args=[dish.pk]))

    def test_cart_quantity_can_be_updated_and_item_removed(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)
        self.client.post(reverse("add_to_cart", args=[dish.pk]))
        cart_item = CartItem.objects.get(dish=dish)

        response = self.client.post(
            reverse("update_cart_item", args=[dish.pk]),
            {"quantity": "3"},
        )

        self.assertRedirects(response, reverse("order"))
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)
        self.assertContains(self.client.get(reverse("order")), "360.00")

        response = self.client.post(reverse("remove_cart_item", args=[dish.pk]))

        self.assertRedirects(response, reverse("order"))
        self.assertFalse(CartItem.objects.filter(dish=dish).exists())

    def test_cart_quantity_ajax_update_returns_updated_totals(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)
        self.client.post(reverse("add_to_cart", args=[dish.pk]))

        response = self.client.post(
            reverse("update_cart_item", args=[dish.pk]),
            {"delta": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"quantity": 2, "line_total": "240.00", "cart_total": "240.00"},
        )
        self.assertEqual(CartItem.objects.get(dish=dish).quantity, 2)

        response = self.client.post(
            reverse("update_cart_item", args=[dish.pk]),
            {"delta": "-1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"quantity": 1, "line_total": "120.00", "cart_total": "120.00"},
        )

    def test_cart_is_preserved_after_logout_and_login(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)
        self.client.post(reverse("add_to_cart", args=[dish.pk]))
        self.client.post(reverse("logout"))
        self.client.post(
            "/",
            {
                "action": "login",
                "username": self.registration_data["email"],
                "password": self.registration_data["password"],
            },
        )

        response = self.client.get(reverse("order"))

        self.assertContains(response, "Борщ")
        self.assertEqual(
            CartItem.objects.get(user__email=self.registration_data["email"]).quantity,
            1,
        )

    def test_existing_session_cart_is_migrated_to_persistent_cart(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)
        session = self.client.session
        session["cart"] = {str(dish.pk): 2}
        session.save()

        response = self.client.get(reverse("order"))

        self.assertContains(response, "data-item-quantity>2</span>")
        self.assertContains(response, "120.00 ₴")
        self.assertEqual(CartItem.objects.get(dish=dish).quantity, 2)
        self.assertNotIn("cart", self.client.session)

    def test_dish_detail_requires_login_and_shows_description(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        response = self.client.get(reverse("dish_detail", args=[dish.pk]))
        self.assertRedirects(
            response,
            f"/?next={reverse('dish_detail', args=[dish.pk])}",
        )

        self.client.post("/", self.registration_data)
        response = self.client.get(reverse("dish_detail", args=[dish.pk]))
        self.assertContains(response, "Домашній рецепт")

    def test_order_history_lists_order_details_and_reorder(self):
        dish = Dish.objects.create(
            name="Борщ",
            description="Домашній рецепт",
            price="120.00",
        )
        self.client.post("/", self.registration_data)
        self.client.post(reverse("add_to_cart", args=[dish.pk]))

        response = self.client.post(
            reverse("create_order"),
            {
                "customer_name": "Ada Lovelace",
                "phone": "+380501234567",
                "address": "вул. Хрещатик 1, 5",
                "payment_method": "card",
                "comment": "Без лука",
            },
        )

        self.assertRedirects(response, reverse("order_history"))

        history_response = self.client.get(reverse("order_history"))
        self.assertContains(history_response, "Ada Lovelace")
        self.assertContains(history_response, "вул. Хрещатик 1, 5")
        self.assertContains(history_response, "Борщ")
        self.assertContains(history_response, "Замовити ще раз")

        order = Order.objects.get(user__email=self.registration_data["email"])
        reorder_response = self.client.post(
            reverse("reorder_order", args=[order.pk]),
            follow=True,
        )

        self.assertContains(reorder_response, "Замовлення повторно додано до кошика.")
        self.assertContains(self.client.get(reverse("order")), "Борщ")

        self.client.post(reverse("reorder_order", args=[order.pk]))
        cart_item = CartItem.objects.get(
            user__email=self.registration_data["email"],
            dish=dish,
        )
        self.assertEqual(cart_item.quantity, 1)

        self.client.post(
            reverse("create_order"),
            {
                "customer_name": "Ada Lovelace",
                "phone": "+380501234567",
                "address": "вул. Хрещатик 1, 5",
                "payment_method": "card",
                "comment": "Без лука",
            },
        )
        repeated_order = Order.objects.order_by("-created_at").first()
        self.assertEqual(repeated_order.total_price, Decimal("120.00"))
        self.assertEqual(repeated_order.items.get(dish=dish).quantity, 1)

    def test_registration_rejects_mismatched_passwords(self):
        data = self.registration_data | {"password_confirm": "different"}
        response = self.client.post("/", data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Паролі не збігаються.")
