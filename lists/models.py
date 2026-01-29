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
        """Extrait 'Fnac' de 'https://www.fnac.com/produit...'"""
        try:
            if not self.url:
                return ""
            # On recupere le domaine (ex: www.amazon.fr)
            domain = urlparse(self.url).netloc
            # On enleve le 'www.'
            domain = domain.replace("www.", "")
            # On garde juste ce qu'il y a avant le premier point
            name = domain.split(".")[0]
            # On met une majuscule (fnac -> Fnac)
            return name.capitalize()
        except Exception:
            return ""

    def __str__(self):
        return self.title or "Item sans titre"
