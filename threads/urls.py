from django.urls import path

from .views import home, wishlist, compose, save_thread, details


urlpatterns = [
    path("", home, name="home"),
    path("wishlist", wishlist, name="wishlist"), #TODO: maybe migrate wishlist, home, compose out of threads app? if we want threads app to focus on the model
    path("compose", compose, name="compose"),
    path("threads/<int:thread_id>/save", save_thread, name="thread_save"),
    path("threads/<int:thread_id>/detail", details, name="thread_detail")
]
