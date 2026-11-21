"""
URL configuration for Restaurant project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from restaurant_all import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.auth_page, name='auth'),
    path('authentification/', views.auth_page, name='authentification'),
    path(
        'admin-authentification/',
        views.admin_authentification,
        name='admin_authentification',
    ),
    path('home/', views.home, name='home'),
    path('menu/', views.menu_page, name='menu'),
    path('menu/dish/<int:dish_id>/', views.dish_detail, name='dish_detail'),
    path('cart/add/<int:dish_id>/', views.add_to_cart, name='add_to_cart'),
    path(
        'cart/update/<int:dish_id>/',
        views.update_cart_item,
        name='update_cart_item',
    ),
    path(
        'cart/remove/<int:dish_id>/',
        views.remove_cart_item,
        name='remove_cart_item',
    ),
    path('order/', views.order_page, name='order'),
    path('create-order/', views.create_order_page, name='create_order'),
    path('logout/', views.logout_view, name='logout'),
    path('order-history/', views.order_history, name='order_history'),
    path(
        'order-history/reorder/<int:order_id>/',
        views.reorder_order,
        name='reorder_order',
    ),
    path('raiting/', views.raiting_page, name='raiting'),
    path('raiting/comment/', views.comment_dish, name='comment_dish'),
    path('raiting/comment/<int:dish_id>/', views.comment_dish, name='comment_dish_for'),
    path('raiting/<int:dish_id>/', views.rate_dish, name='rate_dish'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
