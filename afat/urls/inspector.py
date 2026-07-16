"""
Inspector URLs.
These URLs are prefixed with `inspector/`
"""

# Django
from django.urls import path

# Alliance Auth AFAT
from afat.views import inspector

urls = [
    path(route="", view=inspector.overview, name="inspector_overview"),
]
