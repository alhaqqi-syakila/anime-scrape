"""
Aplikasi Scraping Anime Otakudesu
---------------------------------
Aplikasi web berbasis Flask untuk mengambil dan menampilkan konten anime dari Otakudesu.
Fitur-fitur:
- Update anime terbaru
- Detail dan episode anime
- Fungsi pencarian
- Penjelajahan berdasarkan genre

Pembuat: Al Haqqi Syakila
Dibuat: Februari 2025
"""

from flask import Flask, jsonify, render_template, request
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
from datetime import datetime, timedelta
import random

# Region Inisialisasi

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Konstanta
BASE_URL = "https://otakudesu.cloud"
CACHE_EXPIRE_TIME = 3600  # 1 jam

# User Agent untuk menghindari deteksi
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
]

# Cache
_anime_cache = {"data": None, "timestamp": None}
_anime_detail_cache = {}
_episode_video_cache = {}
_search_cache = {}

# End region

# Region Function Pembantu

def is_cache_valid(timestamp, expire_seconds=CACHE_EXPIRE_TIME):
    """Cek validitas cache"""
    if not timestamp:
        return False
    if isinstance(timestamp, datetime):
        return datetime.now() - timestamp < timedelta(seconds=expire_seconds)
    return time.time() - timestamp < expire_seconds

def get_random_headers():
    """Generate header acak untuk request"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

def get_soup(url):
    """Ambil dan parse HTML dari URL"""
    headers = get_random_headers()
    try:
        logger.info(f"Mengambil URL: {url}")
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
        logger.error(f"Error {response.status_code}: {url}")
        return None
    except Exception as e:
        logger.error(f"Error: {url}: {e}")
        return None

def extract_text(element, default="Data tidak tersedia"):
    """Ambil teks dari elemen BS4"""
    return element.text.strip() if element else default

def extract_attribute(element, attr, default=""):
    """Ambil atribut dari elemen BS4"""
    return element[attr] if element and attr in element.attrs else default

def clean_text(text, pattern, replacement=""):
    """Bersihkan teks dengan regex"""
    return re.sub(pattern, replacement, text).strip()

# End region

# Region Function Scraping

def get_anime():

    """Ambil daftar anime terbaru"""

    global _anime_cache
    
    # Mengembalikan data cache jika masih valid
    if is_cache_valid(_anime_cache["timestamp"]):
        return _anime_cache["data"]
    
    url = f"{BASE_URL}/"    
    soup = get_soup(url)
    if not soup:
        logger.warning("Failed to get soup for homepage")
        return []

    anime_list = []
    
    try:
        anime_items = soup.find_all("div", class_="detpost")
        
        for anime in anime_items:
            # Mengambil informasi dasar
            title_tag = anime.find("h2", class_="jdlflm")
            date_tag = anime.find("div", class_="newnime")
            episode_tag = anime.find("div", class_="epz")
            image_tag = anime.find("img", class_="attachment-thumb size-thumb wp-post-image")
            link_tag = anime.find("a")

            # Memproses data yang diambil
            title = extract_text(title_tag, "Judul tidak ditemukan")
            date = extract_text(date_tag, "Tanggal tidak ditemukan")
            episode = extract_text(episode_tag, "Episode tidak ditemukan")
            image_url = extract_attribute(image_tag, "src", "https://via.placeholder.com/150")
            link = extract_attribute(link_tag, "href", "#")

             # Mengambil slug dari link
            slug_match = re.search(r"/anime/([^/]+)-sub-indo", link)
            title_slug = slug_match.group(1) if slug_match else ""
            
            # Menyusun informasi anime
            anime_list.append({
                "title": title,
                "date": date,
                "episode": episode,
                "image_url": image_url,
                "link": f"/anime/{title_slug}-sub-indo",
                "slug": title_slug
            })
    except Exception as e:
        logger.error(f"Error scraping news: {e}")

    # Memperbarui cache dengan data baru
    _anime_cache = {"data": anime_list, "timestamp": datetime.now()}
    return anime_list

def scrape_completed_anime(page=1):

    """Ambil daftar anime completed dengan pagination"""

    url = f"{BASE_URL}/complete-anime"
    if page > 1:
        url = f"{url}/page/{page}"
    
    soup = get_soup(url)
    if not soup:
        logger.warning(f"Failed to get soup for completed anime page {page}")
        return []

    anime_list = []
    try:
        anime_items = soup.find_all("div", class_="detpost")

        for anime in anime_items:
            title_tag = anime.find("h2", class_="jdlflm")
            date_tag = anime.find("div", class_="newnime")
            status_tag = anime.find("div", class_="epz")
            image_tag = anime.find("img", class_="attachment-thumb size-thumb wp-post-image")
            link_tag = anime.find("a")

            title = extract_text(title_tag, "Judul tidak ditemukan")
            date = extract_text(date_tag, "Tanggal tidak ditemukan")
            status = extract_text(status_tag, "Status tidak ditemukan")
            image_url = extract_attribute(image_tag, "src", "https://via.placeholder.com/150")
            link = extract_attribute(link_tag, "href", "#")

            # Mengambil slug dari link
            slug_match = re.search(r"/anime/([^/]+)-sub-indo", link)
            title_slug = slug_match.group(1) if slug_match else ""

            anime_list.append({
                "title": title,
                "date": date,
                "status": status,
                "image_url": image_url,
                "link": f"/anime/{title_slug}-sub-indo",
                "slug": title_slug
            })

        # Hitung total Halaman
        pagination = soup.find("div", class_="pagination")
        last_page = 1
        if pagination:
            page_links = pagination.find_all("a")
            for link in page_links:
                try:
                    page_num = int(link.text)
                    last_page = max(last_page, page_num)
                except ValueError:
                    continue

        return {
            "anime_list": anime_list,
            "current_page": page,
            "last_page": last_page
        }

    except Exception as e:
        logger.error(f"Error scraping completed anime page {page}: {e}")
        return {"anime_list": [], "current_page": page, "last_page": 1}

def search_anime(query):
    """Cari anime berdasarkan query"""
    global _search_cache
    
    cache_key = query.lower()
    if cache_key in _search_cache and is_cache_valid(_search_cache[cache_key]["timestamp"]):
        return _search_cache[cache_key]["data"]
    
    formatted_query = query.replace(" ", "+")
    url = f"{BASE_URL}/?s={formatted_query}&post_type=anime"
    
    logger.info(f"Fetching search URL: {url}")
    soup = get_soup(url)
    if not soup:
        logger.warning(f"Failed to get soup for search query: {query}")
        return []

    search_results = []
    try:
        anime_items = soup.select("ul.chivsrc")
        
        for ul in anime_items:
            li_items = ul.select("li")
            for item in li_items:
                # Mengambil Image
                image_tag = item.select_one("img.attachment-post-thumbnail")
                image_url = extract_attribute(image_tag, "src", "https://via.placeholder.com/150")
                
                # Mengambil title dan link
                title_tag = item.select_one("h2 a")
                title = extract_text(title_tag, "Judul tidak ditemukan")
                original_link = extract_attribute(title_tag, "href", "#")
                
                # Mengambil anime slug dari link asli
                slug_match = re.search(r"/anime/([^/]+)-sub-indo/?", original_link)
                anime_slug = slug_match.group(1) if slug_match else ""
                # Create local link
                link = f"/anime/{anime_slug}-sub-indo" if anime_slug else "#"
                
                # Mengambil semua genre
                info_divs = item.select("div.set")
                genres = []
                if len(info_divs) > 0:
                    genre_links = info_divs[0].select("a")
                    genres = [extract_text(a) for a in genre_links]
                genre = ", ".join(genres) if genres else "Genre tidak ditemukan"
                
                # Bersihkan teks status
                status = extract_text(info_divs[1], "Status tidak ditemukan") if len(info_divs) > 1 else "Status tidak ditemukan"
                status = re.sub(r'^Status\s*:\s*', '', status)
                
                # Bersihkan teks rating
                rating = extract_text(info_divs[2], "Rating tidak ditemukan") if len(info_divs) > 2 else "Rating tidak ditemukan"
                rating = re.sub(r'^Rating\s*:\s*', '', rating)
                
                search_results.append({
                    "title": title,
                    "image_url": image_url,
                    "link": link,
                    "genre": genre,
                    "status": status,
                    "rating": rating
                })
        
        # Update cache
        _search_cache[cache_key] = {
            "data": search_results,
            "timestamp": datetime.now()
        }
        
        return search_results
    
    except Exception as e:
        logger.error(f"Error searching anime: {e}")
        return []

def scrape_anime_detail(title_slug):
    """ Ambil data detail anime"""
    global _anime_detail_cache
    
    # Check cache first
    if title_slug in _anime_detail_cache and is_cache_valid(_anime_detail_cache[title_slug]["timestamp"]):
        return _anime_detail_cache[title_slug]["data"]
    
    # Jika slug asli sudah ada "-sub-indo" atau "-subtitle-indonesia", simpan
    original_slug = title_slug

    # Bersihkan suffix
    title_slug = title_slug.replace("-sub-indo", "").replace("-subtitle-indonesia", "")

    # Coba fetch dengan format sesuai slug asli dulu
    urls_to_try = [
        f"{BASE_URL}/anime/{original_slug}/",  # Coba URL sesuai slug awal
        f"{BASE_URL}/anime/{title_slug}-sub-indo/",
        f"{BASE_URL}/anime/{title_slug}-subtitle-indonesia/"
    ]

    soup = None
    for url in urls_to_try:
        logger.info(f"Trying URL: {url}")
        temp_soup = get_soup(url)
        if temp_soup and temp_soup.find("div", class_="jdlrx"):  # Verify we got a valid anime page
            soup = temp_soup
            break
    
    if not soup:
        logger.warning(f"Failed to get valid soup for anime: {title_slug}")
        return {}

    try:
        # Ambil title
        title_tag_div = soup.find("div", class_="jdlrx")
        title_tag = extract_text(title_tag_div, "Judul tidak ditemukan")
        title_tag = clean_text(title_tag, r"\s*[\|\-]?\s*(Subtitle Indonesia|Sub Indo).*")

        # Ambil synopsis
        sinopsis_tag = soup.find("div", class_="sinopc")
        sinopsis = extract_text(sinopsis_tag, "Sinopsis tidak ditemukan.")

        # Ambil image
        image_tag = soup.find("img", class_="attachment-post-thumbnail size-post-thumbnail wp-post-image")
        image_url = extract_attribute(image_tag, "src", "https://via.placeholder.com/150")

        # Ambil anime info dari infozingle div
        div_info = soup.find('div', class_="infozingle")
        
        anime_info = {
            "score": "Data tidak ada",
            "genre": "Data tidak ada",
            "producer": "Data tidak ada",
            "release_date": "Data tidak ada",
            "studio": "Data tidak ada"
        }
        
        if div_info:
            all_p = div_info.find_all("p")
            if len(all_p) >= 3:
                anime_info["score"] = clean_text(all_p[2].text, r'Skor?:\s*')
            if len(all_p) >= 4:
                anime_info["producer"] = clean_text(all_p[3].text, r'Produser?:\s*')
            if len(all_p) >= 9:
                anime_info["release_date"] = clean_text(all_p[8].text, r'Tanggal Rilis?:\s*')
            if len(all_p) >= 10:
                anime_info["studio"] = clean_text(all_p[9].text, r'Studio?:\s*')
            if len(all_p) >= 11:
                anime_info["genre"] = clean_text(all_p[10].text, r'Genre?:\s*')

        # Ambil daftar episode
        episodes = []
        episode_lists = soup.find_all("div", class_="episodelist")
        episode_list_div = episode_lists[1] if len(episode_lists) >= 3 else (episode_lists[0] if episode_lists else None)

        if episode_list_div:
            ep_items = episode_list_div.find_all("li")
            for ep in ep_items:
                ep_link_tag = ep.find("a")
                if ep_link_tag and "href" in ep_link_tag.attrs:
                    full_ep_link = ep_link_tag["href"]
                    ep_slug_match = re.search(r"/episode/([^/]+)/", full_ep_link)
                    ep_slug = ep_slug_match.group(1) if ep_slug_match else ""
                    ep_title = extract_text(ep_link_tag)
                    episodes.append({"title": ep_title, "link": f"/episode/{ep_slug}"})

        result = {
            "title": title_tag,
            "image_url": image_url,
            "score": anime_info["score"],
            "genre": anime_info["genre"],
            "producer": anime_info["producer"],
            "studio": anime_info["studio"],
            "release_date": anime_info["release_date"],
            "sinopsis": sinopsis,
            "episodes": episodes
        }
        
        # Update cache
        _anime_detail_cache[title_slug] = {"data": result, "timestamp": datetime.now()}
        return result
        
    except Exception as e:
        logger.error(f"Error scraping anime detail for {title_slug}: {e}")
        return {}
    

def scrape_episode_video(episode_slug):
    """Ambil data video episode"""
    global _episode_video_cache
    
    if episode_slug in _episode_video_cache and is_cache_valid(_episode_video_cache[episode_slug]["timestamp"]):
        return _episode_video_cache[episode_slug]["data"]
    
    urls_to_try = [
        f"{BASE_URL}/episode/{episode_slug}/",
        f"{BASE_URL}/episode/{episode_slug}-subtitle-indonesia/"
    ]
    
    for url in urls_to_try:
        soup = get_soup(url)
        if soup:
            break
    else:
        logger.warning(f"Failed to get soup for episode: {episode_slug}")
        return {}

    try:
        # Ambil title
        title_tag = soup.find("title")
        episode_title = extract_text(title_tag, "Judul tidak ditemukan")
        episode_title = clean_text(episode_title, r"(Subtitle Indonesia|Otaku Desu)(\.|\s*\|)?|\s*\|$")

        # Ambil video URL
        video_tag = soup.find("iframe")
        video_url = extract_attribute(video_tag, "src")

        if not video_url:
            video_source = soup.find("source")
            video_url = extract_attribute(video_source, "src", "https://via.placeholder.com/560x315")

        # Ambil genre
        div_info = soup.find('div', class_="infozingle")
        genre = "Genre tidak ada"
        if div_info:
            all_p = div_info.find_all("p")
            if len(all_p) >= 3:
                genre = clean_text(all_p[2].text, r'Genres?:\s*')

        # Cari parent halaman anime untuk mendapatkan semua episodea
        anime_link_tag = soup.find("a", href=re.compile(r"/anime/"))
        anime_slug_match = re.search(r"/anime/([^/]+)-sub-indo|subtitle-indonesia", extract_attribute(anime_link_tag, "href", "")) if anime_link_tag else None
        anime_slug = anime_slug_match.group(1) if anime_slug_match else ""

        all_episodes = []
        if anime_slug:
            anime_data = scrape_anime_detail(anime_slug)
            all_episodes = anime_data.get("episodes", [])
            
        result = {
            "episode_title": episode_title,
            "video_url": video_url,
            "genre": genre,
            "all_episodes": all_episodes
        }
        
        # Update cache
        _episode_video_cache[episode_slug] = {"data": result, "timestamp": datetime.now()}
        return result

    except Exception as e:
        logger.error(f"Error scraping episode video for {episode_slug}: {e}")
        return {}

def scrape_anime_by_genre(genre_slug):

    """Ambil semua data list genre"""

    url = f"{BASE_URL}/genres/{genre_slug}/"
    soup = get_soup(url)

    if not soup:
        logger.warning(f"Failed to get soup for genre: {genre_slug}")
        return []

    anime_list = []
    try:
        # Cari container utama yang berisi daftar anime
        anime_containers = soup.select(".page .col-md-4.col-anime-con")

        for anime_div in anime_containers:
            anime_info = {}

            # Ambil judul
            title_div = anime_div.select_one(".col-anime-title")
            anime_info["title"] = extract_text(title_div, "Judul tidak ditemukan")

            # Ambil jumlah episode
            eps_div = anime_div.select_one(".col-anime-eps")
            anime_info["episodes"] = extract_text(eps_div, "N/A")

            # Ambil rating
            rating_div = anime_div.select_one(".col-anime-rating")
            anime_info["rating"] = extract_text(rating_div, "N/A")

            # Ambil genre
            genre_div = anime_div.select_one(".col-anime-genre")
            anime_info["genre"] = extract_text(genre_div, "N/A")

            # Ambil cover image
            cover_div = anime_div.select_one(".col-anime-cover img")
            anime_info["cover_url"] = extract_attribute(cover_div, "src", "https://via.placeholder.com/150")

            # Ambil tanggal rilis
            date_div = anime_div.select_one(".col-anime-date")
            anime_info["release_date"] = extract_text(date_div, "N/A")

            # Ambil link detail anime
            link_tag = anime_div.select_one(".col-anime-title a")
            original_link = extract_attribute(link_tag, "href", "#")

            # Debug: Log original link
            logger.info(f"Original link: {original_link}")

            # Ambil slug dari link asli
            slug_match = re.search(r"/anime/([^/]+)-sub-indo", original_link)
            anime_slug = slug_match.group(1) if slug_match else ""  # Get the slug or set to empty if not found

            # Debug: Log extracted slug
            logger.info(f"Extracted slug: {anime_slug}")

            # Buat detail URL
            anime_info["detail_url"] = f"/anime/{anime_slug}-sub-indo" if anime_slug else "#"

            anime_list.append(anime_info)

        return anime_list

    except Exception as e:
        logger.error(f"Error scraping anime genre {genre_slug}: {e}")
        return []

def scrape_anime_by_genre(genre_slug, page=1):
    """Scrape anime list by genre from Otakudesu"""
    url = f"{BASE_URL}/genres/{genre_slug}"
    if page > 1:
        url = f"{url}/page/{page}"
    soup = get_soup(url)

    if not soup:
        logger.warning(f"Failed to get soup for genre: {genre_slug}")
        return []

    anime_list = []
    try:
        # Cari container utama yang berisi daftar anime
        anime_containers = soup.select(".page .col-md-4.col-anime-con")

        for anime_div in anime_containers:
            anime_info = {}

            # Ambil judul
            title_div = anime_div.select_one(".col-anime-title")
            anime_info["title"] = extract_text(title_div, "Judul tidak ditemukan")

            # Ambil jumlah episode
            eps_div = anime_div.select_one(".col-anime-eps")
            anime_info["episodes"] = extract_text(eps_div, "N/A")

            # Ambil rating
            rating_div = anime_div.select_one(".col-anime-rating")
            anime_info["rating"] = extract_text(rating_div, "N/A")

            # Ambil genre
            genre_div = anime_div.select_one(".col-anime-genre")
            anime_info["genre"] = extract_text(genre_div, "N/A")

            # Ambil cover image
            cover_div = anime_div.select_one(".col-anime-cover img")
            anime_info["cover_url"] = extract_attribute(cover_div, "src", "https://via.placeholder.com/150")

            # Ambil tanggal rilis
            date_div = anime_div.select_one(".col-anime-date")
            anime_info["release_date"] = extract_text(date_div, "N/A")

            # Ambil link detail anime
            link_tag = anime_div.select_one(".col-anime-title a")
            original_link = extract_attribute(link_tag, "href", "#")

            # Debug: Log original link
            logger.info(f"Original link: {original_link}")

            # Ambil slug dari link asli
            slug_match = re.search(r"/anime/([^/]+)-sub-indo", original_link)
            anime_slug = slug_match.group(1) if slug_match else ""  # Get the slug or set to empty if not found

            # Debug: Log extracted slug
            logger.info(f"Extracted slug: {anime_slug}")

            # Buat detail URL
            anime_info["detail_url"] = f"/anime/{anime_slug}-sub-indo" if anime_slug else "#"

            anime_list.append(anime_info)
        # Dapatkan total halaman
        pagination = soup.find("div", class_="pagenavix")
        last_page = 1
        if pagination:
            page_links = pagination.find_all("a")
            for link in page_links:
                try:
                    page_num = int(link.text)
                    last_page = max(last_page, page_num)
                except ValueError:
                    continue

        return {
            "anime_list": anime_list,
            "current_page": page,
            "last_page": last_page
        }

    except Exception as e:
        logger.error(f"Error scraping anime genre {genre_slug}: {e}")
        return {"anime_list": [], "current_page": page, "last_page": 1}

def scrape_genre_list():
    """
    Scrape all available genres from otakudesu.cloud/genre-list/
    Returns a list of dictionaries containing genre names and their slugs
    """
    url = f"{BASE_URL}/genre-list/"
    soup = get_soup(url)

    if not soup:
        logger.warning("Failed to get soup for genre list page")
        return []

    genres = []
    try:
        # Cari elemen <ul class="genres">
        genre_ul = soup.find('ul', class_='genres')

        if not genre_ul:
            logger.warning("Could not find genres list container")
            return []

        # Ambil semua <a> yang ada dalam <li> pertama
        genre_links = genre_ul.find('li').find_all('a')

        for link in genre_links:
            href = extract_attribute(link, 'href', '')
            slug_match = re.search(r'/genres/([^/]+)', href)
            slug = slug_match.group(1) if slug_match else ''

            name = extract_text(link, 'Unknown Genre')

            if slug:  # Pastikan hanya menambahkan jika slug ada
                genres.append({
                    'name': name,
                    'slug': slug,
                    'url': f'/genre/{slug}'
                })

        return genres

    except Exception as e:
        logger.error(f"Error scraping genre list: {e}")
        return []

# End Region

# Region Routes dan Error Handlers
@app.route("/")
def main():
    # Periksa apakah ini permintaan pencarian
    search_query = request.args.get('s')
    post_type = request.args.get('post_type')
    
    if search_query and post_type == 'anime':
        try:
            results = search_anime(search_query)
            return render_template("search.html", results=results, query=search_query)
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return render_template("error.html", message="Failed to perform search")
    
    # Jika bukan permintaan pencarian, tampilkan halaman utama
    try:
        result = get_anime()
        return render_template("index.html", data=result)
    except Exception as e:
        logger.error(f"Error in main route: {e}")
        return render_template("error.html", message="Terjadi kesalahan saat memuat halaman utama")
    

@app.route("/api/completed-anime/<int:page>")
def get_completed_anime(page):
    try:
        result = scrape_completed_anime(page)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in completed anime API: {e}")
        return jsonify({"error": "Failed to fetch completed anime"}), 500
    

@app.route('/api/genre/<genre_slug>')
def get_anime_by_genre(genre_slug):
    data = scrape_anime_by_genre(genre_slug)
    return jsonify(data)


@app.route("/anime/<title_slug>")
def anime_detail(title_slug):
    try:
        anime_data = scrape_anime_detail(title_slug)
        if not anime_data:
            return render_template("error.html", message="Anime not found"), 404
        return render_template("anime_detail.html", anime=anime_data)
    except Exception as e:
        logger.error(f"Error in anime_detail route for {title_slug}: {e}")
        return render_template("error.html", message="An error occurred while loading anime details")


@app.route("/episode/<episode_slug>")
def episode_detail(episode_slug):
    try:
        video_data = scrape_episode_video(episode_slug)
        if not video_data:
            return render_template("error.html", message="Episodes not found"), 404
        return render_template("episode_detail.html", video=video_data)
    except Exception as e:
        logger.error(f"Error in episode_detail route for {episode_slug}: {e}")
        return render_template("error.html", message="An error occurred while loading the episode")


@app.route("/genre/<genre_slug>")
def genre_page(genre_slug):
    try:
        # Dapatkan nomor halaman dari parameter kueri, defaultnya adalah 1
        page = request.args.get('page', 1, type=int)
        
        # Dapatkan daftar anime berdasarkan genre menggunakan fungsi scrape_anime_by_genre yang ada
        result = scrape_anime_by_genre(genre_slug, page)
        
        if not result or not result.get('anime_list'):
            return render_template("error.html", message="Genre is no longer available"), 404
            
        # Format nama genre untuk tampilan (ganti tanda hubung dengan spasi dan gunakan huruf besar)
        genre_name = genre_slug.replace('-', ' ').title()
        
        return render_template(
            "genre.html",
            anime_list=result['anime_list'],
            genre_name=genre_name,
            current_page=result['current_page'],
            last_page=result['last_page'],
            genre_slug=genre_slug
        )
    except Exception as e:
        logger.error(f"Error in genre_page route for {genre_slug}: {e}")
        return render_template("error.html", message="An error occurred while loading the genre page")
    

@app.route("/genre-list")
def genre_list():
    try:
        genres = scrape_genre_list()
        if not genres:
            return render_template("error.html", message="Genre list not found"), 404
        return render_template("genre_list.html", genres=genres)
    except Exception as e:
        logger.error(f"Error in genre_list route: {e}")
        return render_template("error.html", message="An error occurred while loading the genre list")


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'public, max-age=300'
    return response

@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", message="An error occurred on the server"), 500

app.debug = True  # Enable debug mode for local development

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000) 
