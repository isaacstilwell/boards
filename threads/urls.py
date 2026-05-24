from django.urls import path

from .views import home, wishlist, compose, save_thread, details, upload_images, create_thread, approve_thread, reject_thread


urlpatterns = [
    path("", home, name="home"),
    path("wishlist", wishlist, name="wishlist"), #TODO: maybe migrate wishlist, home, compose out of threads app? if we want threads app to focus on the model
    path("compose/upload_images", upload_images, name="upload_images"),
    path("compose", compose, name="compose"),
    path("threads/<int:thread_id>/save", save_thread, name="thread_save"),
    path("threads/<int:thread_id>/detail", details, name="thread_detail"),
    path("threads/create", create_thread, name="thread_create"),
    path("threads/<int:thread_id>/approve", approve_thread, name="thread_approve"),
    path("threads/<int:thread_id>/reject", reject_thread, name="thread_reject")
]
