from django.contrib import admin
from restaurant_all.models import ClientProfile, Dish


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available")
    list_editable = ("category", "is_available")


admin.site.register(ClientProfile)
