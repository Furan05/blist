from django.urls import path

from . import views

urlpatterns = [
    path("", views.create_list, name="home"),
    path("list/<slug:slug>/", views.list_detail, name="list_detail"),
    path("list/<slug:slug>/add/", views.add_item, name="add_item"),
    path(
        "list/<slug:slug>/delete/<int:item_id>/", views.delete_item, name="delete_item"
    ),
    path(
        "list/<slug:slug>/reserve/<int:item_id>/",
        views.reserve_item,
        name="reserve_item",
    ),
    path("list/<slug:slug>/edit/<int:item_id>/", views.edit_item, name="edit_item"),
]
