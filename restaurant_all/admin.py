from django.contrib import admin
from restaurant_all.models import ClientProfile, Dish, DishRating


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available")
    list_editable = ("category", "is_available")
    search_fields = ("name", "description")


@admin.register(DishRating)
class DishRatingAdmin(admin.ModelAdmin):
    list_display = ("dish", "user", "score", "comment_preview")
    list_filter = ("dish", "score")
    search_fields = (
        "dish__name",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "comment",
    )
    autocomplete_fields = ("dish", "user")
    list_select_related = ("dish", "user")
    list_per_page = 25

    fieldsets = (
        ("Відгук гостя", {
            "fields": ("dish", "user", "score", "comment"),
        }),
    )

    @admin.display(description="Відгук")
    def comment_preview(self, obj):
        if not obj.comment:
            return "—"
        return obj.comment[:80] + ("…" if len(obj.comment) > 80 else "")


admin.site.register(ClientProfile)
