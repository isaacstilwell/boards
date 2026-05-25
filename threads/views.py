from asyncio.log import logger
from datetime import date
import json

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import F
from django.http import HttpRequest, HttpResponse

from .models import Thread, SavedThread, UploadedImage
from .forms import ImageUpload, ThreadForm


ALL_FILTERS = ["keyboard", "keycaps", "instock", "active", "upcoming"]
ITEM_OPTIONS = [o[0] for o in Thread.ITEM_TYPES]
THREAD_OPTIONS = [o[0] for o in Thread.THREAD_TYPES]


def home(request: HttpRequest) -> HttpResponse:
    """
    Renders the homepage with all of the provided filters

    Parameters
        request: HttpRequest
            http request from the client

    Returns
        HttpResponse
            http response to render a partial or the full page, depending on hx
    """

    # extract arguments from http request
    active_filters = request.GET.getlist("filters")
    search = request.GET.get("q", "")
    page_number = int(request.GET.get("page", 1))
    sort = request.GET.get("sort", "latest")
    user = request.user

    buttons = []
    for f in ALL_FILTERS:
        if f not in active_filters:
            next_filters = active_filters + [f]
        else:
            next_filters = [af for af in active_filters if af != f]
        buttons.append(
            {
                "label": f,
                "toggled": f in active_filters,
                "vals": json.dumps(
                    {
                        "filters": next_filters,
                        "q": search,
                        "page": 1,
                    }
                ),
            }
        )

    search_obj = {
        "current": search,
        "vals": json.dumps(
            {
                "filters": active_filters,
                "page": 1,
            }
        ),
    }

    sort_obj = {
        "current": sort,
        "vals": json.dumps(
            {
                "filters": active_filters,
                "page": 1,
            }
        ),
    }

    # if no filters are selected for item_type or thread_type, provide all of
    # them as active filters for the Thread obj filtration
    has_item_filters = any([f in active_filters for f in ITEM_OPTIONS])
    has_thread_filters = any([f in active_filters for f in THREAD_OPTIONS])
    if not has_item_filters:
        active_filters += ITEM_OPTIONS
    if not has_thread_filters:
        active_filters += THREAD_OPTIONS

    # match sort to an F object and keep nulls always last
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

    # ensure regular users can only see approved threads
    if user.is_staff:
        threads = (
            Thread.objects.filter(
                item_type__in=active_filters,
                thread_type__in=active_filters,
                title__icontains=search,
            ).order_by(sort_key)
            if active_filters
            else Thread.objects.all().order_by(sort_key)
        )
    else:
        threads = (
            Thread.objects.filter(
                item_type__in=active_filters,
                thread_type__in=active_filters,
                title__icontains=search,
                status="approved",
            ).order_by(sort_key)
            if active_filters
            else Thread.objects.filter(status="approved").order_by(sort_key)
        )

    paginator = Paginator(threads, 25)
    page = paginator.get_page(page_number)

    # provide user's saved threads so that the stars show up correctly
    saved_threads = (
        Thread.objects.filter(saved__user=request.user)
        if request.user.is_authenticated
        else Thread.objects.none()
    )

    # render the partial for htmx requests, otherwise render the regular html file
    template_name = "partials/home_response.html" if request.htmx else "home.html"  # ty: ignore[unresolved-attribute]

    return render(
        request,
        template_name,
        {
            "page": page,
            "search": search_obj,
            "sort": sort_obj,
            "saved_threads": saved_threads,
            "buttons": buttons,
        },
    )


def details(request: HttpRequest, thread_id: int) -> HttpResponse | JsonResponse:
    """
    Renders the details page for a given thread

    Parameters
        request: HttpRequest
            http request from the client
        thread_id: int
            id of the thread whose details are being rendered

    Returns
        HttpResponse
            http response to render a partial or the full page, depending on hx
    """

    try:
        thread = Thread.objects.get(pk=thread_id)
    except:
        return JsonResponse("Invalid thread id", safe=False, status=404)

    template_name = "partials/status_buttons.html" if request.htmx else "detail.html"  # ty: ignore[unresolved-attribute]
    return render(request, template_name, {"thread": thread})


@login_required
def wishlist(request: HttpRequest) -> HttpResponse:
    """
    Renders the wishlist page for a user

    Parameters
        request: HttpRequest
            http request from the client

    Returns
        HttpResponse
            http response to render a partial or the full page, depending on hx
    """

    saved_threads = Thread.objects.filter(saved__user=request.user)

    template_name = "partials/wishlist_list.html" if request.htmx else "wishlist.html"  # ty: ignore[unresolved-attribute]

    return render(request, template_name, {"saved_threads": saved_threads})


@login_required
def compose(request: HttpRequest) -> HttpResponse:
    """
    Renders the compose page for a new thread

    Parameters
        request: HttpRequest
            http request from the client

    Returns
        HttpResponse
            http response to render a partial or the full page, depending on hx
    """

    image_form = ImageUpload()
    thread_form = ThreadForm()

    # uploaded images by this user that aren't mapped to a thread yet are the
    # images that should be added to the next thread
    uploaded_images = UploadedImage.objects.filter(
        user=request.user, thread__isnull=True
    )
    template_name = "partials/image_form.html" if request.htmx else "compose.html"  # ty: ignore[unresolved-attribute]
    return render(
        request,
        template_name,
        {
            "thread_form": thread_form,
            "image_form": image_form,
            "uploaded_images": uploaded_images,
        },
    )


@login_required
def save_thread(request: HttpRequest, thread_id: int) -> HttpResponse | JsonResponse:
    """
    Creates or deletes a SavedThread for the user and a given thread

    Parameters
        request: HttpRequest
            http request from the client
        thread_id: int
            id of the thread being saved/removed from saves

    Returns
        HttpResponse
            http response to render a partial or the full page, depending on hx
    """

    if request.method == "POST":
        try:
            thread = Thread.objects.get(pk=thread_id)
        except:
            return JsonResponse("Invalid thread id", safe=False, status=404)

        try:
            # if intersection of user and thread_id already exists in SavedThread,
            # delete
            saved_thread = SavedThread.objects.get(user=request.user, thread=thread)
            saved_thread.delete()
        except:
            # otherwise, create a new one
            SavedThread.objects.create(user=request.user, thread=thread)

    if "/wishlist" in request.htmx.current_url:  # ty: ignore[unresolved-attribute]
        return wishlist(request)
    else:
        return home(request)


# an amalgamation of multi file uploads from https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/
# and https://medium.com/@bhagyalakshmi18/uploading-multiple-files-in-django-b2f5ede55d09
@login_required
def upload_images(request: HttpRequest) -> HttpResponse:
    """
    Creates UploadedImages for all images that a user uploaded

    Parameters
        request: HttpRequest
            http request from the client

    Returns
        HttpResponse
            http response to render a partial or the full page, depending on hx
    """

    if request.method == "POST":
        form = ImageUpload(request.POST, request.FILES)
        if form.is_valid():
            images = form.cleaned_data["images"]
            for image in images:
                file_instance = UploadedImage(image=image, user=request.user)
                file_instance.save()

    return compose(request)


@login_required
def create_thread(request: HttpRequest) -> HttpResponse:
    """
    Creates a Thread with a valid ThreadForm, or routes user back to the
    compose screen

    Parameters
        request: HttpRequest
            http request from the client
        thread_id: int
            id of the thread being saved/removed from saves

    Returns
        HttpResponse
            http response to render a partial or the full page, depending on hx
    """

    if request.method == "POST":
        form = ThreadForm(request.POST, request.FILES)
        if form.is_valid():
            thread = form.save(commit=False)

            # get uploaded images and add them to the thread, but do not add the
            # backward link yet
            uploaded_images = UploadedImage.objects.filter(
                user=request.user, thread__isnull=True
            )
            thread.image_urls = [
                uploaded_image.image.url for uploaded_image in uploaded_images
            ]

            thread.primary_image_url = thread.image_urls[0]
            thread.poster = request.user
            thread.post_date = date.today()
            thread.save()

            # now that thread is saved, add the backward link
            for uploaded_image in uploaded_images:
                uploaded_image.thread = thread
                uploaded_image.save()
            # for a valid form, redirect to the new thread after creation
            return redirect("thread_detail", thread_id=thread.id)
        else:
            logger.error("invalid thread! errors: %s", form.errors.as_json())
    return compose(request)


@staff_member_required
def approve_thread(request: HttpRequest, thread_id: int) -> HttpResponse | JsonResponse:
    """
    Approves a non-approved thread or marks an already approved thread as pending

    Parameters
        request: HttpRequest
            http request from the client
        thread_id: int
            id of the thread being approved

    Returns
        HttpResponse
            http response to render the page
    """

    if request.method == "POST":
        try:
            thread = Thread.objects.get(pk=thread_id)
        except:
            return JsonResponse("Invalid thread id", safe=False, status=404)

        thread.status = "pending" if thread.status == "approved" else "approved"
        thread.save()

    return details(request, thread_id)


@staff_member_required
def reject_thread(request: HttpRequest, thread_id: int) -> HttpResponse | JsonResponse:
    """
    Approves a non-approved thread or marks an already approved thread as pending

    Parameters
        request: HttpRequest
            http request from the client
        thread_id: int
            id of the thread being approved

    Returns
        HttpResponse | JsonResponse
            http response to render the page
    """
    if request.method == "POST":
        try:
            thread = Thread.objects.get(pk=thread_id)
        except:
            return JsonResponse("Invalid thread id", safe=False, status=404)
        thread.status = "pending" if thread.status == "rejected" else "rejected"
        thread.save()

    return details(request, thread_id)
