import re

from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from restaurant_all.authentication import normalize_phone
from restaurant_all.models import ClientProfile


class RegistrationForm(forms.Form):
    first_name = forms.CharField(
        label="Ім’я",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        label="Прізвище",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    phone = forms.CharField(
        label="Номер телефону",
        max_length=32,
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "autocomplete": "tel",
                "placeholder": "+380...",
            }
        ),
    )
    email = forms.EmailField(
        label="Електронна пошта",
        max_length=150,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password_confirm = forms.CharField(
        label="Підтвердіть пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_model = get_user_model()
        if user_model._default_manager.filter(email__iexact=email).exists():
            raise ValidationError("Ця електронна адреса вже зареєстрована.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        normalized_phone = normalize_phone(phone)
        if not normalized_phone or len(re.sub(r"\D", "", normalized_phone)) < 7:
            raise ValidationError("Введіть коректний номер телефону.")
        if ClientProfile.objects.filter(phone=normalized_phone).exists():
            raise ValidationError("Цей номер телефону вже зареєстрований.")
        return normalized_phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Паролі не збігаються.")
        elif password and "email" in cleaned_data:
            user = get_user_model()(
                username=cleaned_data["email"],
                email=cleaned_data["email"],
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
            )
            try:
                validate_password(password, user=user)
            except ValidationError as error:
                self.add_error("password", error)
        return cleaned_data

    @transaction.atomic
    def save(self):
        user_model = get_user_model()
        email = self.cleaned_data["email"]
        user = user_model._default_manager.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )
        ClientProfile.objects.create(user=user, phone=self.cleaned_data["phone"])
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Пошта або номер телефону",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["autofocus"] = True


class AdminEmailLoginForm(AdminAuthenticationForm):
    username = forms.CharField(
        label="Нікнейм",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )

    def confirm_login_allowed(self, user):
        if not user.is_superuser:
            raise ValidationError("Доступ дозволено лише superuser.")
        super().confirm_login_allowed(user)

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if username and password:
            self.user_cache = ModelBackend().authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user_cache is None:
                raise ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                    params={"username": self.username_field.verbose_name},
                )
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class BootstrapSuperuserForm(forms.Form):
    email = forms.EmailField(
        label="Електронна пошта",
        max_length=150,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_model = get_user_model()
        if user_model._default_manager.filter(email__iexact=email).exists():
            raise ValidationError("Ця електронна адреса вже використовується.")
        if user_model._default_manager.filter(username__iexact=email).exists():
            raise ValidationError("Ця електронна адреса вже використовується.")
        if user_model._default_manager.filter(is_superuser=True).exists():
            raise ValidationError("Першого superuser вже створено.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        email = cleaned_data.get("email")
        if password and email:
            user = get_user_model()(username=email, email=email)
            try:
                validate_password(password, user=user)
            except ValidationError as error:
                self.add_error("password", error)
        return cleaned_data

    @transaction.atomic
    def save(self):
        user_model = get_user_model()
        if user_model._default_manager.filter(is_superuser=True).exists():
            raise ValidationError("Першого superuser вже створено.")

        email = self.cleaned_data["email"]
        return user_model._default_manager.create_superuser(
            username=email,
            email=email,
            password=self.cleaned_data["password"],
        )
