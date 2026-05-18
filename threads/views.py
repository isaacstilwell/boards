from asyncio.log import logger

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Thread, SavedThread

def home(request):
    # TODO: read filters & sorting from request
    # TODO: use django_filters to handle filtering
    threads = Thread.objects.all()
    page_number = request.GET.get('page', 1)
    paginator = Paginator(threads, 25)
    page = paginator.get_page(page_number)
    saved_threads = Thread.objects.filter(saved__user=request.user) if request.user.is_authenticated else Thread.objects.none()

    template_name = "partials/thread_list.html" if request.htmx else "home.html"
    return render(request, template_name, {"page": page, "saved_threads": saved_threads})

def details(request, thread_id):
    try:
        thread = Thread.objects.get(pk=thread_id)
    except:
        return JsonResponse("Invalid thread id", safe=False, status=404)
    return render(request, "detail.html", {"thread": thread})

@login_required
def save_thread(request, thread_id):
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

@login_required
def wishlist(request):
    saved_threads = Thread.objects.filter(saved__user=request.user)

    template_name = "partials/wishlist_list.html" if request.htmx else "wishlist.html"

    return render(request, template_name, {"saved_threads": saved_threads})


@login_required
def compose(request):
    return render(request, "compose.html")