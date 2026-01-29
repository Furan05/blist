import re
import json
from urllib.parse import urlparse
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

def clean_price(price_str):
    if not price_str: return None
    clean = re.sub(r'[^\d.,]', '', str(price_str).strip())
    clean = clean.replace(',', '.')
    if clean.count('.') > 1:
        parts = clean.split('.')
        clean = "".join(parts[:-1]) + "." + parts[-1]
    if not clean: return None
    return f"{clean} €"

def get_amazon_asin(url):
    """Extrait le code ASIN (ex: B0FKFCM9J3) de l'URL Amazon"""
    # Cherche un motif de 10 lettres/chiffres qui commence par B0
    match = re.search(r'/(dp|gp/product)/([A-Z0-9]{10})', url)
    if match:
        return match.group(2)
    return None

def fetch_generic_product(url):
    print(f"🕵️‍♂️ Analyse : {url}")

    data = {"title": None, "image": None, "price": None, "url": url}

    # --- 1. STRATÉGIE SPÉCIALE AMAZON (ASIN) ---
    # On tente de deviner l'image AVANT même de scraper la page
    if "amazon" in url:
        asin = get_amazon_asin(url)
        if asin:
            # URL magique d'Amazon qui renvoie toujours l'image principale
            data["image"] = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SCLZZZZZZZ_.jpg"
            print(f"✅ Image Amazon générée via ASIN : {asin}")

    # --- 2. SCRAPING CLASSIQUE ---
    try:
        response = cffi_requests.get(
            url,
            impersonate="chrome110",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9",
            },
            timeout=10
        )

        soup = BeautifulSoup(response.content, "html.parser")

        # Titre (OpenGraph)
        if soup.find("meta", property="og:title"):
            data["title"] = soup.find("meta", property="og:title")["content"]

        # Image (OpenGraph) - Seulement si on n'a pas déjà trouvé via ASIN
        if not data["image"] and soup.find("meta", property="og:image"):
            data["image"] = soup.find("meta", property="og:image")["content"]

        # Nettoyage Titre Amazon
        if "amazon" in url and data["title"]:
            data["title"] = data["title"].split(':')[0].strip()

        # Spécifique FNAC (Image)
        if "fnac.com" in url and not data["image"]:
            fnac_img = soup.select_one(".f-productHeader-viewVisual img")
            if fnac_img and fnac_img.get("src"):
                 data["image"] = fnac_img.get("src")

        # Prix (JSON-LD)
        if not data["price"]:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    js = json.loads(script.string)
                    if isinstance(js, list): js = js[0]
                    if "offers" in js:
                        offers = js["offers"]
                        if isinstance(offers, list) and offers: offers = offers[0]
                        if isinstance(offers, dict) and "price" in offers:
                            data["price"] = clean_price(str(offers["price"]))
                except: continue

        # Titres rejetés (Anti-bot)
        bad_titles = ["fnac.com", "fnac", "amazon", "captcha", "robot check", "access denied"]
        if data["title"]:
            is_bad = any(bad in data["title"].lower() for bad in bad_titles)
            if len(data["title"]) < 4 or is_bad:
                data["title"] = None

    except Exception as e:
        print(f"⚠️ Erreur scraping : {e}")

    # --- 3. DÉDUCTION TITRE VIA URL (Dernier recours) ---
    if not data["title"]:
        try:
            path = urlparse(url).path
            candidates = [s for s in path.split('/') if len(s) > 4 and not s.isdigit()]
            if candidates:
                raw = max(candidates, key=len)
                clean = re.sub(r'[-_.]|html|dp', ' ', raw)
                data["title"] = clean.capitalize()
                print(f"🧠 Titre déduit URL : {data['title']}")
        except:
            data["title"] = "Lien ajouté"

    return data
