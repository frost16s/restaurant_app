import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from restaurant_all.models import ClientProfile


def normalize_phone(phone):
    value = phone.strip()
    if not re.fullmatch(r"\+?[\d\s().-]+", value):
        return None

    digits = re.sub(r"\D", "", value)
    return f"+{digits}" if value.startswith("+") else digits


class PhoneOrEmailBackend(ModelBackend):
    def authenticate(self, _request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email") or kwargs.get("phone")
        if not identifier or not password:
            return None

        user_model = get_user_model()
        user = user_model._default_manager.filter(email__iexact=identifier).first()
        if user is None:
            phone = normalize_phone(identifier)
            profile = (
                ClientProfile.objects.select_related("user")
                .filter(phone=phone)
                .first()
            ) if phone else None
            user = profile.user if profile else None

        if user is None:
            return super().authenticate(
                _request,
                username=identifier,
                password=password,
                **kwargs,
            )

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
