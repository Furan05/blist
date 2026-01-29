from urllib.parse import urlparse

from django.db import models
from django.utils.text import slugify


class GiftList(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Item(models.Model):
    gift_list = models.ForeignKey(
        GiftList, related_name="items", on_delete=models.CASCADE
    )
    url = models.URLField()
    title = models.CharField(max_length=500, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    price = models.CharField(max_length=50, blank=True, null=True)
    is_reserved = models.BooleanField(default=False)
    reserved_by_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def site_name(self):
        """
        Extrait le nom du site proprement.
        Ex: 'https://fr.gymshark.com/...' -> 'Gymshark'
        Ex: 'https://www.fnac.com/...' -> 'Fnac'
        """
        try:
            if not self.url:
                return ""

            # On récupère le domaine (ex: fr.gymshark.com)
            domain = urlparse(self.url).netloc

            # On enlève le port si présent (ex: :8000)
            if ":" in domain:
                domain = domain.split(":")[0]

            parts = domain.split(".")

            # Liste des préfixes à ignorer
            ignore_list = [
                "www",
                "fr",
                "en",
                "m",
                "shop",
                "store",
                "secure",
                "checkout",
                "boutique",
            ]

            # Si le premier bout est dans la liste (ex: 'fr'), on prend le suivant
            if len(parts) > 1 and parts[0] in ignore_list:
                name = parts[1]
            else:
                name = parts[0]

            return name.capitalize()
        except Exception:
            return ""

    def __str__(self):
        return self.title or "Item sans titre"
