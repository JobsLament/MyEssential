from django.shortcuts import render, redirect
from io import BytesIO
from django.http import HttpResponse, HttpResponseBadRequest
from urllib.parse import urlencode
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageDraw, ImageFont
import requests
from django.conf import settings
import concurrent.futures
from collections import Counter
from datetime import datetime

def main(request):
    return render(request, 'index.html')


def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        # Добавляем scope для получения истории прослушиваний
        scope="user-top-read user-read-recently-played",
        cache_path=None
    )

def spotify_login(request):
    try:
        sp_oauth = get_spotify_oauth()
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    except Exception as e:
        return HttpResponse(f"Error generating auth URL: {str(e)}", status=500)


def spotify_callback(request):
    try:
        code = request.GET.get('code')
        if not code:
            return HttpResponseBadRequest("Authorization code missing")

        sp_oauth = get_spotify_oauth()
        token_info = sp_oauth.get_access_token(code)
        
        if not token_info:
            return HttpResponseBadRequest("Failed to get access token")

        # Добавляем параметр year для выбора года
        return redirect(f'/album-matrix/?token={token_info["access_token"]}&year=2024')
    
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)