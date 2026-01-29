from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from lists.models import GiftList, Item
from scraper.extractors.generic import fetch_generic_product


def create_list(request):
    """Crée une nouvelle liste et redirige vers celle-ci."""
    if request.method == "POST":
        title = request.POST.get("title", "Ma Liste")
        new_list = GiftList.objects.create(title=title)
        return redirect("list_detail", slug=new_list.slug)

    return render(request, "lists/home.html")


def list_detail(request, slug):
    """Affiche une liste et ses cadeaux."""
    gift_list = get_object_or_404(GiftList, slug=slug)
    return render(request, "lists/detail.html", {"gift_list": gift_list})


@require_http_methods(["POST"])
def add_item(request, slug):
    """Reçoit une URL, scrape les infos, et ajoute le cadeau."""
    gift_list = get_object_or_404(GiftList, slug=slug)
    url = request.POST.get("url")

    if url:
        item = Item.objects.create(gift_list=gift_list, url=url)
        try:
            data = fetch_generic_product(url)
            if data:
                item.title = data.get("title") or "Titre inconnu"
                item.image_url = data.get("image")
                item.price = data.get("price")
                item.save()
        except Exception as e:
            print(f"Erreur scraping: {e}")

    return redirect("list_detail", slug=slug)


@require_http_methods(["POST"])
def delete_item(request, slug, item_id):
    """Supprime un cadeau de la liste."""
    gift_list = get_object_or_404(GiftList, slug=slug)
    item = get_object_or_404(Item, id=item_id, gift_list=gift_list)
    item.delete()
    return redirect("list_detail", slug=slug)


@require_http_methods(["POST"])
def reserve_item(request, slug, item_id):
    """Marque un cadeau comme réservé par un invité."""
    gift_list = get_object_or_404(GiftList, slug=slug)
    item = get_object_or_404(Item, id=item_id, gift_list=gift_list)

    guest_name = request.POST.get("guest_name")

    # On ne réserve que si ce n'est pas déjà fait
    if guest_name and not item.is_reserved:
        item.is_reserved = True
        item.reserved_by_name = guest_name
        item.save()

    return redirect("list_detail", slug=slug)


@require_http_methods(["POST"])
def edit_item(request, slug, item_id):
    """Permet de corriger manuellement un cadeau."""
    gift_list = get_object_or_404(GiftList, slug=slug)
    item = get_object_or_404(Item, id=item_id, gift_list=gift_list)

    # On récupère les champs du formulaire
    item.title = request.POST.get("title", item.title)
    item.price = request.POST.get("price", item.price)
    item.image_url = request.POST.get("image_url", item.image_url)

    item.save()
    return redirect("list_detail", slug=slug)
