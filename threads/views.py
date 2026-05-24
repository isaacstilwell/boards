from asyncio.log import logger
from datetime import date
import json

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from .models import Thread, SavedThread, UploadedImage
from django.views.generic.edit import FormView
from .forms import ImageUpload, ThreadForm
from django.db.models import F



ALL_FILTERS = ["keyboard", "keycaps", "instock", "active", "upcoming"]
ITEM_OPTIONS = [o[0] for o in Thread.ITEM_TYPES]
THREAD_OPTIONS = [o[0] for o in Thread.THREAD_TYPES]

def home(request):
    active_filters = request.GET.getlist("filters")
    search = request.GET.get("q", "")
    page_number = request.GET.get("page", 1)
    sort = request.GET.get("sort", "latest")
    user = request.user

    print(f"{active_filters=}")
    print(f"{search=}")
    print(f"{page_number=}")
    print(f"{sort=}")
    print(f"{user=}")

    has_item_filters = any([f in active_filters for f in ITEM_OPTIONS])
    has_thread_filters = any([f in active_filters for f in THREAD_OPTIONS])

    buttons = []
    for f in ALL_FILTERS:
        if f not in active_filters:
            next_filters = active_filters + [f]
        else:
            next_filters = [af for af in active_filters if af != f]
        buttons.append({
            "label": f,
            "toggled": f in active_filters,
            "vals": json.dumps({
                "filters": next_filters,
                "q": search,
                "page": 1,
            }),
        })

    search_obj = {
        "current": search,
        "vals": json.dumps({
            "filters": active_filters,
            "page": 1,
        }),
    }

    sort_obj = {
        "current": sort,
        "vals": json.dumps({
            "filters": active_filters,
            "page": 1,
        })
    }

    if not has_item_filters:
        active_filters += ITEM_OPTIONS
    if not has_thread_filters:
        active_filters += THREAD_OPTIONS

    print(buttons)

    match sort:
        case "oldest":
            sort_key = F("post_date").asc(nulls_last=True)
        case "price-asc":
            sort_key = F("price").asc(nulls_last=True)
        case "price-desc":
            sort_key = F("price").desc(nulls_last=True)
        case "end-asc":
            sort_key = F("end_date").asc(nulls_last=True)
        case "end-desc":
            sort_key = F("end_date").desc(nulls_last=True)
        case _:
            sort_key = F("post_date").desc(nulls_last=True)

    if user.is_staff:
        threads = Thread.objects.filter(
            item_type__in=active_filters,
            thread_type__in=active_filters,
            title__icontains=search
        ).order_by(sort_key) if active_filters else Thread.objects.all().order_by(sort_key)
    else:
        threads = Thread.objects.filter(
            item_type__in=active_filters,
            thread_type__in=active_filters,
            title__icontains=search,
            status="approved",
        ).order_by(sort_key) if active_filters else Thread.objects.filter(status="approved").order_by(sort_key)

    paginator = Paginator(threads, 25)
    page = paginator.get_page(page_number)
    saved_threads = Thread.objects.filter(saved__user=request.user) if request.user.is_authenticated else Thread.objects.none()

    template_name = "partials/home_response.html" if request.htmx else "home.html"
    return render(request, template_name, {
        "page": page,
        "search": search_obj,
        "saved_threads": saved_threads,
        "buttons": buttons,
    })


def details(request, thread_id):
    try:
        thread = Thread.objects.get(pk=thread_id)
    except:
        return JsonResponse("Invalid thread id", safe=False, status=404)

    template_name = "partials/status_buttons.html" if request.htmx else "detail.html"
    return render(request, template_name, {"thread": thread})


@login_required
def wishlist(request):
    saved_threads = Thread.objects.filter(saved__user=request.user)

    template_name = "partials/wishlist_list.html" if request.htmx else "wishlist.html"

    return render(request, template_name, {"saved_threads": saved_threads})


@login_required
def compose(request):
    image_form = ImageUpload()
    thread_form = ThreadForm()
    uploaded_images = UploadedImage.objects.filter(user=request.user, thread__isnull=True)
    template_name = "partials/image_form.html" if request.htmx else "compose.html"
    return render(request, template_name, {"thread_form": thread_form, "image_form": image_form, "uploaded_images": uploaded_images})


@login_required
def save_thread(request, thread_id: int):
    if request.method == "POST":
        try:
            thread = Thread.objects.get(pk=thread_id)
        except:
            return JsonResponse("Invalid thread id", safe=False, status=404)

        try:
            saved_thread = SavedThread.objects.get(user=request.user, thread=thread)
            saved_thread.delete()
        except:
            SavedThread.objects.create(user=request.user, thread=thread)

        if "/wishlist" in request.htmx.current_url:
            return wishlist(request)
        else:
            return home(request)


# an amalgamation of multi file uploads from https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/
# and https://medium.com/@bhagyalakshmi18/uploading-multiple-files-in-django-b2f5ede55d09
# tbh i dont 100% understand either of them very well, but it works
@login_required
def upload_images(request):
    if request.method == "POST":
        form = ImageUpload(request.POST, request.FILES)
        if form.is_valid():
            images = form.cleaned_data["images"]
            for image in images:
                file_instance = UploadedImage(image=image, user=request.user)
                file_instance.save()

    return compose(request)


@login_required
def create_thread(request):
    if request.method == "POST":
        form = ThreadForm(request.POST, request.FILES)
        if form.is_valid():
            thread = form.save(commit=False)
            uploaded_images = UploadedImage.objects.filter(user=request.user, thread__isnull=True)
            thread.image_urls = [uploaded_image.image.url for uploaded_image in uploaded_images]
            thread.primary_image_url = thread.image_urls[0]
            thread.poster = request.user
            thread.post_date = date.today()
            thread.save()

            for uploaded_image in uploaded_images:
                uploaded_image.thread = thread
                uploaded_image.save()
            return redirect("thread_detail", thread_id=thread.id)
        else:
            logger.error("invalid thread! errors: %s", form.errors.as_json())


@staff_member_required
def approve_thread(request, thread_id: int):
    if request.method == "POST":
        try:
            thread = Thread.objects.get(pk=thread_id)
        except:
            return JsonResponse("Invalid thread id", safe=False, status=404)

        thread.status = "pending" if thread.status == "approved" else "approved"
        thread.save()
        return details(request, thread_id)


@staff_member_required
def reject_thread(request, thread_id: int):
    if request.method == "POST":
        try:
            thread = Thread.objects.get(pk=thread_id)
        except:
            return JsonResponse("Invalid thread id", safe=False, status=404)
        thread.status = "pending" if thread.status == "rejected" else "rejected"
        thread.save()
        return details(request, thread_id)



