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
