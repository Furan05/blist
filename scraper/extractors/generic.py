import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from duckduckgo_search import DDGS


def clean_price(price_str):
    """Nettoie un prix brut (ex: '1 299,99 €' -> '1299.99 €')"""
    if not price_str:
        return None
    # On ne garde que les chiffres, points et virgules
    clean = re.sub(r"[^\d.,]", "", str(price_str).strip())
    # Uniformisation : virgule devient point
    clean = clean.replace(",", ".")
    # S'il y a plusieurs points (ex: 1.299.00), on ne garde que le dernier pour les décimales
    if clean.count(".") > 1:
        parts = clean.split(".")
        clean = "".join(parts[:-1]) + "." + parts[-1]

    if not clean:
        return None
    return f"{clean} €"


def fetch_generic_product(url):
    print(f"🕵️‍♂️ Analyse : {url}")

    data = {
        "title": None,
        "image": None,
        "price": None,
        "url": url,
    }

    # --- 1. TENTATIVE DE SCRAPING DIRECT (cffi) ---
    try:
        # Imitation Chrome pour passer les protections
        response = cffi_requests.get(
            url,
            impersonate="chrome110",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            timeout=12,
        )

        soup = BeautifulSoup(response.content, "html.parser")

        # A. TITRE & IMAGE (Méthode Standard OG tags)
        if soup.find("meta", property="og:title"):
            data["title"] = soup.find("meta", property="og:title")["content"]
        if soup.find("meta", property="og:image"):
            data["image"] = soup.find("meta", property="og:image")["content"]

        # ### SPÉCIFIQUE FNAC ###
        # Si c'est la Fnac et qu'on n'a pas d'image, on force un sélecteur CSS connu
        if "fnac.com" in url and not data["image"]:
            print("🎯 Application du patch spécifique FNAC pour l'image...")
            # Sélecteur actuel de l'image principale sur la Fnac
            fnac_img = soup.select_one(".f-productHeader-viewVisual img")
            if fnac_img and fnac_img.get("src"):
                data["image"] = fnac_img.get("src")
                print(f"✅ Image Fnac trouvée via sélecteur dédié.")

        # B. PRIX & INFO (Méthode JSON-LD - Très fiable pour le prix)
        if not data["price"]:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    js_content = script.string
                    if not js_content:
                        continue
                    js_data = json.loads(js_content)
                    if isinstance(js_data, list):
                        js_data = js_data[0]

                    # Recherche du prix
                    if "offers" in js_data:
                        offers = js_data["offers"]
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        if isinstance(offers, dict) and "price" in offers:
                            data["price"] = clean_price(str(offers["price"]))
                            print(f"💰 Prix trouvé (JSON-LD) : {data['price']}")

                    # Fallback image via JSON-LD si toujours rien
                    if not data["image"] and "image" in js_data:
                        img = js_data["image"]
                        if isinstance(img, list):
                            data["image"] = img[0]
                        elif isinstance(img, dict):
                            data["image"] = img.get("url")
                        else:
                            data["image"] = img
                except:
                    continue

        # C. PRIX (Fallback Sélecteurs CSS spécifiques)
        if not data["price"]:
            # Fnac (classe du prix actuel)
            fnac_price = soup.select_one(".f-price__amount")
            # Amazon (partie entière + fraction)
            amz_whole = soup.select_one(".a-price-whole")
            amz_frac = soup.select_one(".a-price-fraction")

            if fnac_price:
                data["price"] = clean_price(fnac_price.get_text())
            elif amz_whole:
                frac = amz_frac.get_text() if amz_frac else "00"
                data["price"] = clean_price(f"{amz_whole.get_text()},{frac}")

        # D. FILTRE ANTI-TITRE "CHARABIA"
        # Si le site nous a bloqué, il envoie souvent un titre générique. On le rejette.
        bad_titles = [
            "fnac.com",
            "fnac",
            "amazon",
            "captcha",
            "vérification",
            "access denied",
            "momentarily unavailable",
        ]
        if data["title"]:
            is_bad = any(bad in data["title"].lower() for bad in bad_titles)
            if len(data["title"]) < 5 or is_bad:
                print(f"⚠️ Titre rejeté ('{data['title']}'), passage au plan B.")
                data["title"] = None

    except Exception as e:
        print(f"⚠️ Erreur scraping direct : {e}")

    # --- 2. PLAN B : DÉDUCTION VIA URL (Si titre manquant) ---
    if not data["title"]:
        try:
            path = urlparse(url).path
            # On cherche le segment le plus long qui ressemble à un nom
            candidates = [s for s in path.split("/") if len(s) > 4 and not s.isdigit()]
            if candidates:
                raw = max(candidates, key=len)
                # Nettoyage (enlève tirets, .html, et les IDs à la fin)
                clean = re.sub(r"[-_.]|html", " ", raw)
                clean = re.sub(r"\s[a-zA-Z0-9]+$", "", clean).strip()
                data["title"] = clean.capitalize()
                print(f"🧠 Titre déduit de l'URL : {data['title']}")
        except:
            data["title"] = "Lien ajouté"

    # --- 3. PLAN C : CHASSE À L'IMAGE EXTERNE (Si toujours rien) ---
    if not data["image"] and data["title"] and data["title"] != "Lien ajouté":
        print(f"🔍 Recherche image externe pour : '{data['title']}'...")
        try:
            with DDGS() as ddgs:
                # On prend les 6 premiers mots pour la recherche
                query = " ".join(data["title"].split()[:6])
                results = list(ddgs.images(query, max_results=1))
                if results and results[0].get("image"):
                    data["image"] = results[0].get("image")
                    print("✅ Image trouvée via DuckDuckGo.")
        except Exception as e:
            print(f"❌ Échec recherche externe : {e}")

    # Dernier filet de sécurité pour le prix
    if not data["price"]:
        data["price"] = "Prix libre"

    print(f"📦 RÉSULTAT FINAL : {data}")
    return data
