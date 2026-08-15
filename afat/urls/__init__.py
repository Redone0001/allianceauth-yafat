"""
URLs for the AFAT app
"""

# Django
from django.urls import include, path

# Alliance Auth AFAT
from afat.constants import INTERNAL_URL_PREFIX
from afat.urls import statistics  # pylint: disable=W0406 E0611
from afat.urls import ajax, dashboard, fatlinks, inspector, logs

app_name: str = "afat"  # pylint: disable=invalid-name

urlpatterns = [
    # Dashboard
    path(route="", view=include(dashboard.urls)),
    # Log urls
    path(route="logs/", view=include(logs.urls)),
    # Inspector urls
    path(route="inspector/", view=include(inspector.urls)),
    # FAT Links urls
    path(route="fatlinks/", view=include(fatlinks.urls)),
    # Statistics urls
    path(route="statistics/", view=include(statistics.urls)),
    # Ajax calls urls
    path(route=f"{INTERNAL_URL_PREFIX}/ajax/", view=include(ajax.urls)),
]
