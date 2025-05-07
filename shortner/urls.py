from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_api, name='create_api'), # Primary AJAX endpoint
    path('create_form/', views.create, name='create_form'), # Fallback/alternative form submission
    path('qr/<str:pk>/', views.generate_qr, name='generate_qr'), # Ensure trailing slash if needed by JS
    path('stats/<str:pk>/', views.get_url_stats, name='get_url_stats'),
    path('captcha/', include('captcha.urls')),
    path('captcha/refresh/', views.captcha_refresh, name='captcha_refresh'),
    path('<str:pk>/', views.go, name='go'), # This should be last as it's a catch-all for short codes
]

# Custom 404 handler
handler404 = 'shortener.views.custom_404' # Assuming 'shortener' is your app name