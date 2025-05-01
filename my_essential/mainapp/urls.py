from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.main, name='home'),
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('album-matrix/', views.generate_album_matrix, name='album_matrix'),
]   
