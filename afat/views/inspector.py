"""
Inspector views.
"""

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, QuerySet
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
SORT_FIELDS = {
    "observed": "observed",
    "character": "fat__character__character_name",
    "event": "event",
    "location": "solar_system__name",
    "ship": "ship__name",
    "source": "source",
    "fatlink": "fat__fatlink__fleet",
}
SORT_DIRECTIONS = ("asc", "desc")


def _sorting(request: WSGIRequest) -> tuple[str, str]:
    """
    Return a sanitized sort field and direction.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    sort = request.GET.get("sort", "observed")
    direction = request.GET.get("direction", "desc")

    if sort not in SORT_FIELDS:
        sort = "observed"

    if direction not in SORT_DIRECTIONS:
        direction = "desc"

    return sort, direction


def _apply_sorting(events: QuerySet, sort: str, direction: str) -> QuerySet:
    """
    Apply inspector sorting to a tracking event queryset.

    :param events:
    :type events:
    :param sort:
    :type sort:
    :param direction:
    :type direction:
    :return:
    :rtype:
    """

    sort_field = SORT_FIELDS[sort]
    order_field = sort_field if direction == "asc" else f"-{sort_field}"

    if sort == "observed":
        return events.order_by(order_field, "id" if direction == "asc" else "-id")

    return events.order_by(order_field, "-observed", "-id")


def _sort_links(
    request: WSGIRequest, current_sort: str, current_direction: str
) -> dict:
    """
    Build sort links that preserve current filters.

    :param request:
    :type request:
    :param current_sort:
    :type current_sort:
    :param current_direction:
    :type current_direction:
    :return:
    :rtype:
    """

    sort_links = {}

    for sort in SORT_FIELDS:
        query = request.GET.copy()
        query.pop("page", None)
        direction = (
            "desc"
            if current_sort == sort and current_direction == "asc"
            else "asc"
        )

        query["sort"] = sort
        query["direction"] = direction

        icon = "fa-sort"

        if current_sort == sort:
            icon = "fa-sort-up" if current_direction == "asc" else "fa-sort-down"

        sort_links[sort] = {
            "querystring": urlencode(query, doseq=True),
            "icon": icon,
        }

    return sort_links


def _filtered_tracking_events(
    request: WSGIRequest, sort: str, direction: str
) -> QuerySet:
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
    )

    character = request.GET.get("character", "").strip()
    fatlink = request.GET.get("fatlink", "").strip()
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

    if fatlink:
        events = events.filter(
            Q(fat__fatlink__fleet__icontains=fatlink)
            | Q(fat__fatlink__hash__icontains=fatlink)
        )

    if location:
        events = events.filter(solar_system__name__icontains=location)

    if event:
        events = events.filter(event__in=event)

    if ship:
        events = events.filter(ship__name__icontains=ship)

    return _apply_sorting(events=events, sort=sort, direction=direction)


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

    current_sort, current_direction = _sorting(request=request)
    tracking_events = _filtered_tracking_events(
        request=request, sort=current_sort, direction=current_direction
    )
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
            "fatlink": request.GET.get("fatlink", "").strip(),
            "location": request.GET.get("location", "").strip(),
            "events": request.GET.getlist("event"),
            "ship": request.GET.get("ship", "").strip(),
        },
        "sort": {
            "current": current_sort,
            "direction": current_direction,
            "links": _sort_links(
                request=request,
                current_sort=current_sort,
                current_direction=current_direction,
            ),
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
