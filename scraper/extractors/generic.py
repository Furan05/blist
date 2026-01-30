import json
import re

import requests
from bs4 import BeautifulSoup


def extract(url):
    """
    Extracteur générique qui tente de récupérer titre, image et prix
    via les balises OpenGraph (OG), Twitter Cards ou JSON-LD.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.114 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception:  # Correction E722 : on capture une exception explicite
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    data = {"url": url, "title": None, "image": None, "price": None}

    # --- 1. Titre ---
    if soup.find("meta", property="og:title"):
        data["title"] = soup.find("meta", property="og:title")["content"]
    elif soup.find("title"):
        data["title"] = soup.find("title").string

    # --- 2. Image ---
    if soup.find("meta", property="og:image"):
        data["image"] = soup.find("meta", property="og:image")["content"]
    elif soup.find("meta", property="twitter:image"):
        data["image"] = soup.find("meta", property="twitter:image")["content"]
    else:
        # Fallback : trouver la première image pertinente
        images = soup.find_all("img")
        for img in images:
            src = img.get("src")
            # On ignore les petites icônes ou les images sans URL absolue
            if src and src.startswith("http") and "logo" not in src.lower():
                data["image"] = src
                break

    # --- 3. Prix (Le plus complexe) ---
    # Stratégie A : JSON-LD (Souvent utilisé par Shopify, etc.)
    json_ld = soup.find("script", type="application/ld+json")
    if json_ld:
        try:
            content = json.loads(json_ld.string)
            # Parfois c'est une liste, parfois un dict
            if isinstance(content, list):
                content = content[0]

            # Correction E501 : On découpe la logique pour éviter les lignes longues
            if "offers" in content:
                offers = content["offers"]
                if isinstance(offers, list):
                    data["price"] = offers[0].get("price")
                elif isinstance(offers, dict):
                    data["price"] = offers.get("price")
        except Exception:  # Correction E722
            pass

    # Stratégie B : Regex dans le texte (si JSON-LD échoue)
    if not data["price"]:
        # Cherche des motifs comme "19.99 €" ou "19,99€"
        # Correction E501 : Regex découpée pour la lisibilité
        price_pattern = re.compile(r"(\d+[\.,]\d{2})\s?[\€$]|[\€$]\s?(\d+[\.,]\d{2})")

        # On cherche d'abord dans les balises de prix classiques
        price_candidates = soup.find_all(
            class_=re.compile(r"price|amount|offer", re.IGNORECASE)
        )

        for candidate in price_candidates:
            text = candidate.get_text().strip()
            match = price_pattern.search(text)
            if match:
                # Prend le premier groupe non nul
                data["price"] = match.group(1) or match.group(2)
                break

    # Nettoyage final du titre
    if data["title"]:
        data["title"] = data["title"].strip()
    else:
        data["title"] = "Objet sans nom"

    return data
