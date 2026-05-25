from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.http import HttpRequest, HttpResponse


class SignUpView(CreateView):
    # https://learndjango.com/tutorials/django-login-and-logout-tutorial
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """
    Renders the profile page

    Parameters
        request: HttpRequest
            http request from the client

    Returns
        HttpResponse
            http response to render the page
    """

    return render(request, "registration/profile.html")
