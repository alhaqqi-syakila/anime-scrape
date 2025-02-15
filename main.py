from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
from datetime import datetime, timedelta
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Constants
BASE_URL = "https://otakudesu.cloud"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
    # Add more User-Agent strings as needed
]
CACHE_EXPIRE_TIME = 3600  # 1 hour cache expiration

# Cache variables
_news_cache = {"data": None, "timestamp": None}
_anime_detail_cache = {}
_episode_video_cache = {} 

def is_cache_valid(timestamp, expire_seconds=CACHE_EXPIRE_TIME):
    """Check if cache is still valid"""
    if not timestamp:
        return False
    if isinstance(timestamp, datetime):
        return datetime.now() - timestamp < timedelta(seconds=expire_seconds)
    else:
        return time.time() - timestamp < expire_seconds

def get_soup(url):
    """Helper function to fetch HTML with error handling and caching"""
    headers = {"User -Agent": random.choice(USER_AGENTS)}  # Randomly select a User-Agent
    try:
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=5)  # Reduced timeout for Vercel
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")  # Using html.parser instead of lxml
            return soup
        else:
            logger.error(f"Error {response.status_code}: Failed to fetch page {url}")
            return None
    except requests.RequestException as e:
        logger.error(f"Request Error for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error for {url}: {e}")
        return None

def extract_text(element, default="Data tidak tersedia"):
    """Safely extract text from a BS4 element"""
    return element.text.strip() if element else default

def extract_attribute(element, attr, default=""):
    """Safely extract attribute from a BS4 element"""
    return element[attr] if element and attr in element.attrs else default

def clean_text(text, pattern, replacement=""):
    """Clean text using regex pattern"""
    return re.sub(pattern, replacement, text).strip()

def scrape_news():
    """Scrape the latest anime news with caching"""
    global _news_cache
    
    # Check cache first
    if is_cache_valid(_news_cache["timestamp"]):
        return _news_cache["data"]
    
    url = f"{BASE_URL}/"
    soup = get_soup(url)
    if not soup:
        logger.warning("Failed to get soup for homepage")
        return []

    anime_list = []
    try:
        anime_items = soup.find_all("div", class_="detpost")

        for anime in anime_items:
            title_tag = anime.find("h2", class_="jdlflm")
            date_tag = anime.find("div", class_="newnime")
            episode_tag = anime.find("div", class_="epz")
            image_tag = anime.find("img", class_="attachment-thumb size-thumb wp-post-image")
            link_tag = anime.find("a")

            title = extract_text(title_tag, "Judul tidak ditemukan")
            date = extract_text(date_tag, "Tanggal tidak ditemukan")
            episode = extract_text(episode_tag, "Episode tidak ditemukan")
            image_url = extract_attribute(image_tag, "src", "https://via.placeholder.com/150")
            link = extract_attribute(link_tag, "href", "#")

            # Extract slug from link
            slug_match = re.search(r"/anime/([^/]+)-sub-indo", link)
            title_slug = slug_match.group(1) if slug_match else ""

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

    # Update cache
    _news_cache = {"data": anime_list, "timestamp": datetime.now()}
    return anime_list

def scrape_anime_detail(title_slug):
    """Scrape anime details with caching"""
    global _anime_detail_cache
    
    # Check cache first
    if title_slug in _anime_detail_cache and is_cache_valid(_anime_detail_cache[title_slug]["timestamp"]):
        return _anime_detail_cache[title_slug]["data"]
    
    title_slug = title_slug.replace("-sub-indo", "")
    url = f"{BASE_URL}/anime/{title_slug}-sub-indo/"
    soup = get_soup(url)
    if not soup:
        logger.warning(f"Failed to get soup for anime: {title_slug}")
        return {}

    try:
        # Extract title
        title_tag_div = soup.find("div", class_="jdlrx")
        title_tag = extract_text(title_tag_div, "Judul tidak ditemukan")
        title_tag = clean_text(title_tag, r"\s*[\|\-]?\s*Subtitle Indonesia.*")

        # Extract synopsis
        sinopsis_tag = soup.find("div", class_="sinopc")
        sinopsis = extract_text(sinopsis_tag, "Sinopsis tidak ditemukan.")

        # Extract image
        image_tag = soup.find("img", class_="attachment-post-thumbnail size-post-thumbnail wp-post-image")
        image_url = extract_attribute(image_tag, "src", "https://via.placeholder.com/150")

        # Extract anime info from infozingle div
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

        # Extract episode list
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
    """Scrape episode video with caching"""
    global _episode_video_cache
    
    # Check cache first
    if episode_slug in _episode_video_cache and is_cache_valid(_episode_video_cache[episode_slug]["timestamp"]):
        return _episode_video_cache[episode_slug]["data"]
    
    url = f"{BASE_URL}/episode/{episode_slug}/"
    soup = get_soup(url)
    if not soup:
        logger.warning(f"Failed to get soup for episode: {episode_slug}")
        return {}

    try:
        # Extract title
        title_tag = soup.find("title")
        episode_title = extract_text(title_tag, "Judul tidak ditemukan")
        episode_title = clean_text(episode_title, r"(Subtitle Indonesia|Otaku Desu)(\.|\s*\|)?|\s*\|$")

        # Extract video URL
        video_tag = soup.find("iframe")
        video_url = extract_attribute(video_tag, "src")

        if not video_url:
            video_source = soup.find("source")
            video_url = extract_attribute(video_source, "src", "https://via.placeholder.com/560x315")

        # Extract genre
        div_info = soup.find('div', class_="infozingle")
        genre = "Genre tidak ada"
        if div_info:
            all_p = div_info.find_all("p")
            if len(all_p) >= 3:
                genre = clean_text(all_p[2].text, r'Genres?:\s*')

        # Find parent anime page to get all episodes
        anime_link_tag = soup.find("a", href=re.compile(r"/anime/"))
        anime_slug_match = re.search(r"/anime/([^/]+)-sub-indo", extract_attribute(anime_link_tag, "href", "")) if anime_link_tag else None
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

# Routes
@app.route("/")
def main():
    try:
        result = scrape_news()
        return render_template("index.html", data=result)
    except Exception as e:
        logger.error(f"Error in main route: {e}")
        return render_template("error.html", message="Terjadi kesalahan saat memuat halaman utama")

@app.route("/anime/<title_slug>")
def anime_detail(title_slug):
    try:
        anime_data = scrape_anime_detail(title_slug)
        if not anime_data:
            return render_template("error.html", message="Anime tidak ditemukan"), 404
        return render_template("anime_detail.html", anime=anime_data)
    except Exception as e:
        logger.error(f"Error in anime_detail route for {title_slug}: {e}")
        return render_template("error.html", message="Terjadi kesalahan saat memuat detail anime")

@app.route("/episode/<episode_slug>")
def episode_detail(episode_slug):
    try:
        video_data = scrape_episode_video(episode_slug)
        if not video_data:
            return render_template("error.html", message="Episode tidak ditemukan"), 404
        return render_template("episode_detail.html", video=video_data)
    except Exception as e:
        logger.error(f"Error in episode_detail route for {episode_slug}: {e}")
        return render_template("error.html", message="Terjadi kesalahan saat memuat episode")

# Add cache-control headers
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'public, max-age=300'  # cache for 5 minutes
    return response

@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", message="Halaman tidak ditemukan"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", message="Terjadi kesalahan pada server"), 500

# Configuration for Vercel
app.debug = False

# Original run block
if __name__ == "__main__":
    app.run()