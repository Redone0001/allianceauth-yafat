"""
Inspector views.
"""

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import QuerySet
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.http import urlencode

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

# Alliance Auth AFAT
from afat.models import FatTrackingEvent
from afat.providers.applogger import AppLogger

logger = AppLogger(my_logger=get_extension_logger(name=__name__))

EVENTS_PER_PAGE = 100


def _filtered_tracking_events(request: WSGIRequest) -> QuerySet:
    """
    Return tracking events filtered from inspector query parameters.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    events = FatTrackingEvent.objects.select_related(
        "fat",
        "fat__character",
        "fat__fatlink",
        "solar_system",
        "ship",
    ).order_by("-observed", "-id")

    character = request.GET.get("character", "").strip()
    location = request.GET.get("location", "").strip()
    valid_events = dict(FatTrackingEvent.Event.choices)
    event = [
        event_type
        for event_type in request.GET.getlist("event")
        if event_type in valid_events
    ]
    ship = request.GET.get("ship", "").strip()

    if character:
        events = events.filter(fat__character__character_name__icontains=character)

    if location:
        events = events.filter(solar_system__name__icontains=location)

    if event:
        events = events.filter(event__in=event)

    if ship:
        events = events.filter(ship__name__icontains=ship)

    return events


@login_required()
@permission_required(perm="afat.inspector")
def overview(request: WSGIRequest) -> HttpResponse:
    """
    FAT tracking event inspector.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    tracking_events = _filtered_tracking_events(request=request)
    paginator = Paginator(tracking_events, EVENTS_PER_PAGE)
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    filter_query = request.GET.copy()
    filter_query.pop("page", None)

    context = {
        "event_choices": FatTrackingEvent.Event.choices,
        "filters": {
            "character": request.GET.get("character", "").strip(),
            "location": request.GET.get("location", "").strip(),
            "events": request.GET.getlist("event"),
            "ship": request.GET.get("ship", "").strip(),
        },
        "page_obj": page_obj,
        "querystring": urlencode(filter_query, doseq=True),
        "total_events": paginator.count,
    }

    logger.info(msg=f"Tracking event inspector called by {request.user}")

    return render(
        request=request,
        template_name="afat/view/inspector/inspector-overview.html",
        context=context,
    )
