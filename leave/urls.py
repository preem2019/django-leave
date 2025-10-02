from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Include all URLs from the 'app' application
    # This makes the root of the website (e.g., http://127.0.0.1:8000/)
    # start with the patterns from 'app.urls'
    path('', include('app.urls')), 
]

