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


def download_album_cover(url, cover_size):
    """Потокобезопасная загрузка обложки альбома"""
    try:
        response = requests.get(url, timeout=3)
        cover_image = Image.open(BytesIO(response.content))
        return cover_image.resize((cover_size-10, cover_size-10))
    except:
        return None

def analyze_listening_habits(sp, top_tracks, time_range='2024'):
    """Анализирует привычки прослушивания и возвращает статистику"""
    # Счетчики для различных категорий
    artist_counter = Counter()
    album_counter = Counter()
    genre_counter = Counter()
    
    for track in top_tracks:
        # Подсчет артистов
        for artist in track['artists']:
            artist_counter[artist['name']] += 1
        
        # Подсчет альбомов
        album_counter[track['album']['name']] += 1
    
    # Получаем информацию о жанрах от артистов
    artist_ids = list(set([artist['id'] for track in top_tracks for artist in track['artists']]))
    artist_chunks = [artist_ids[i:i+50] for i in range(0, len(artist_ids), 50)]
    artists_info = []
    
    for chunk in artist_chunks:
        artists_info.extend(sp.artists(chunk)['artists'])
    
    for artist in artists_info:
        for genre in artist.get('genres', []):
            genre_counter[genre] += 1
    
    # Собираем и возвращаем статистику
    stats = {
        'top_artists': artist_counter.most_common(5),
        'top_albums': album_counter.most_common(3),
        'top_genres': genre_counter.most_common(5),
        'total_top_artists': len(artist_counter),
        'total_top_albums': len(album_counter),
        'total_top_genres': len(genre_counter)
    }
    
    return stats


def generate_album_matrix(request):
    try:
        # ===== НАСТРОЙКИ =====
        COVER_SIZE = 520
        COLS = 5
        ROWS = 5
        TOTAL_TRACKS = COLS * ROWS  # 25 треков
        LEGEND_WIDTH = 700
        BG_COLOR = (18, 18, 18)  # Spotify-черный
        BLACK_COLOR = (18, 18, 18) # Чистый черный для блоков
        HEADER_HEIGHT = 200  # Высота черного блока сверху
        LEFT_PADDING = 100  # Дополнительное пространство слева
        RIGHT_PADDING = 100  # Дополнительное пространство справа
        BOTTOM_PADDING = 100  # Дополнительное пространство снизу
        
        # ===== ПОЛУЧЕНИЕ ДАННЫХ =====
        access_token = request.GET.get('token')
        if not access_token:
            return HttpResponseBadRequest("Token required")
        
        # Получаем год для анализа (по умолчанию 2024)
        year = request.GET.get('year', '2024')
        
        sp = spotipy.Spotify(auth=access_token)
        
        # Определяем временной диапазон в зависимости от запрошенного года
        current_year = datetime.now().year
        if year == str(current_year):
            # Если запрошен текущий год, используем short_term (4 недели)
            time_range = 'short_term'
            title_year = f"{year} (последние 4 недели)"
        elif year == '2024':
            # Если запрошен 2024, используем medium_term (6 месяцев)
            time_range = 'medium_term'
            title_year = "2024"
        else:
            # Для других лет используем long_term (несколько лет)
            time_range = 'long_term'
            title_year = "All Time"
        
        # Получаем топ треки за выбранный период
        top_tracks = sp.current_user_top_tracks(
            limit=TOTAL_TRACKS,
            time_range=time_range
        )['items']

        if len(top_tracks) < 10:
            return HttpResponseBadRequest("Not enough listening history for the selected period")

        # Анализируем привычки прослушивания
        listening_stats = analyze_listening_habits(sp, top_tracks, year)

        # ===== ВИЗУАЛИЗАЦИЯ =====
        # Создаем изображение с учетом дополнительного пространства
        img_width = LEFT_PADDING + COVER_SIZE * COLS + LEGEND_WIDTH + RIGHT_PADDING
        img_height = COVER_SIZE * ROWS + HEADER_HEIGHT + BOTTOM_PADDING
        img = Image.new('RGB', (img_width, img_height), BLACK_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Добавляем основной фон Spotify-черный (не заполняет черные области)
        main_area = Image.new('RGB', (COVER_SIZE * COLS + LEGEND_WIDTH, COVER_SIZE * ROWS), BG_COLOR)
        img.paste(main_area, (LEFT_PADDING, HEADER_HEIGHT))

        # Создаем черный блок сверху (уже есть, так как весь фон черный)
        # Заголовок посередине черного блока
        try:
            # Пробуем загрузить шрифт Cormorant Garamond или Libre Baskerville
            # В системе должны быть установлены эти шрифты, иначе используем Arial
            header_font = ImageFont.truetype("CormorantGaramond-Bold.ttf", 72)
        except:
            try:
                header_font = ImageFont.truetype("LibreBaskerville-Regular.ttf", 72)
            except:
                header_font = ImageFont.truetype("arialbd.ttf", 72)
                
        header_text = "/MY/ ESSENTIAL"
        text_width = draw.textlength(header_text, font=header_font)
        draw.text(
            ((img_width - text_width) // 2, (HEADER_HEIGHT - 72) // 2),
            header_text,
            font=header_font,
            fill=(255, 255, 255)
        )

        # Параллельная загрузка обложек
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            cover_futures = {}
            for idx, track in enumerate(top_tracks):
                if track['album']['images']:
                    cover_url = track['album']['images'][0]['url']
                    future = executor.submit(download_album_cover, cover_url, COVER_SIZE)
                    cover_futures[idx] = future

            # Заполняем сетку обложек
            for row in range(ROWS):
                for col in range(COLS):
                    idx = row * COLS + col
                    if idx >= len(top_tracks):
                        continue
                    
                    track = top_tracks[idx]
                    # Отображаем с учетом смещения из-за черного блока сверху
                    x, y = LEFT_PADDING + col * COVER_SIZE, row * COVER_SIZE + HEADER_HEIGHT
                    
                    # Обложка альбома
                    if idx in cover_futures:
                        cover_image = cover_futures[idx].result()
                        if cover_image:
                            img.paste(cover_image, (x+5, y+5))
                        else:
                            draw.rectangle(
                                [x+5, y+5, x+COVER_SIZE-5, y+COVER_SIZE-5],
                                fill=(40, 40, 40)
                            )
                    else:
                        draw.rectangle(
                            [x+5, y+5, x+COVER_SIZE-5, y+COVER_SIZE-5],
                            fill=(40, 40, 40)
                        )
                    
                    # Номер в топе
                    draw.text(
                        (x + 15, y + 15),
                        f"{idx+1}",
                        font=ImageFont.truetype("arial.ttf", 20),
                        fill=(255, 255, 255)
                    )

        # Легенда с аналитикой (смещена из-за черного блока сверху)
        legend_x = LEFT_PADDING + COVER_SIZE * COLS + 20
        legend_y = HEADER_HEIGHT + 30
        
        # Показываем музыкальный профиль
        draw.text(
            ((img_width - text_width) // 2, (HEADER_HEIGHT - 72) // 2),
            header_text,
            font=header_font,
            fill=(255, 255, 255)
        )
        legend_y += 50
        
        # Топ артисты
        draw.text(
            (legend_x, legend_y),
            f"Топ артисты:",
            font=ImageFont.truetype("arialbd.ttf", 24),
            fill=(255, 255, 255)
        )
        legend_y += 40
        
        for i, (artist, count) in enumerate(listening_stats['top_artists']):
            draw.text(
                (legend_x + 20, legend_y),
                f"{i+1}. {artist} - {count} треков в топе",
                font=ImageFont.truetype("arial.ttf", 20),
                fill=(200, 200, 200)
            )
            legend_y += 30
        
        legend_y += 20
        
        # Топ жанры
        if listening_stats['top_genres']:
            draw.text(
                (legend_x, legend_y),
                f"Любимые жанры:",
                font=ImageFont.truetype("arialbd.ttf", 24),
                fill=(255, 255, 255)
            )
            legend_y += 40
            
            for i, (genre, count) in enumerate(listening_stats['top_genres']):
                draw.text(
                    (legend_x + 20, legend_y),
                    f"{i+1}. {genre.title()}",
                    font=ImageFont.truetype("arial.ttf", 20),
                    fill=(200, 200, 200)
                )
                legend_y += 30
        
        legend_y += 20
        
        # Список треков
        draw.text(
            (legend_x, legend_y),
            f"Ваши любимые треки ({title_year}):",
            font=ImageFont.truetype("arialbd.ttf", 24),
            fill=(255, 255, 255)
        )
        legend_y += 40
        
        for idx, track in enumerate(top_tracks[:25]):
            # Ограничиваем длину строки
            artist_name = track['artists'][0]['name'] if track['artists'] else "Unknown"
            track_name = track['name']
            
            if len(track_name) > 25:
                track_name = track_name[:22] + "..."
            
            if len(artist_name) > 15:
                artist_name = artist_name[:12] + "..."
                
            # Форматируем строку
            text = f"{idx+1}. {track_name} - {artist_name}"
            
            draw.text(
                (legend_x + 20, legend_y),
                text,
                font=ImageFont.truetype("arial.ttf", 18),
                fill=(200, 200, 200)
            )
            
            legend_y += 30

        # Добавляем информацию о шрифтах в HTML
        # Примечание: Это будет включено в HTML-страницу, которая использует этот код
        font_link = """<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300..700;1,300..700&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">"""
        
        # Сохранение
        buffer = BytesIO()
        img.save(buffer, format="PNG", quality=95, optimize=True)
        response = HttpResponse(buffer.getvalue(), content_type="image/png")
        response['Content-Disposition'] = f'attachment; filename="spotify_legacy_{year}.png"'
        return response

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)