from django import forms
from django.forms import ClearableFileInput
from .models import UploadedImage, Thread


# https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/#uploading-multiple-files
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class ImageUpload(forms.Form):
    images = MultipleFileField()


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = [
            "title",
            "designer",
            "external_url",
            "vendors",
            "currency",
            "price",
            "item_type",
            "thread_type",
            "start_date",
            "end_date",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "title", "placeholder": "Title"}),
            "designer": forms.TextInput(
                attrs={"class": "designer", "placeholder": "Designer"}
            ),
            "external_url": forms.URLInput(
                attrs={"class": "external_url", "placeholder": "External Link"}
            ),
            "vendors": forms.TextInput(
                attrs={"class": "vendors", "placeholder": "Vendors (comma separated)"}
            ),
            "currency": forms.Select(attrs={"class": "currency"}),
            "price": forms.NumberInput(attrs={"class": "price", "placeholder": 0.00}),
            "item_type": forms.Select(attrs={"class": "item_type"}),
            "thread_type": forms.Select(attrs={"class": "thread_type"}),
            "start_date": forms.DateInput(
                attrs={"class": "start_date", "type": "date"},
                format="%Y-%m-%d",
            ),
            "end_date": forms.DateInput(
                attrs={"class": "start_date", "type": "date"},
                format="%Y-%m-%d",
            ),
        }
