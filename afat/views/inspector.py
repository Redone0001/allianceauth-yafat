"""
Inspector views.
"""

# Standard Library
from collections import OrderedDict, defaultdict
from datetime import timedelta

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, QuerySet
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import urlencode

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

# Alliance Auth AFAT
from afat.models import FatTrackingEvent
from afat.providers.applogger import AppLogger

logger = AppLogger(my_logger=get_extension_logger(name=__name__))

EVENTS_PER_PAGE = 100
DEFAULT_CORRELATION_WINDOW_MINUTES = 5
MAX_CORRELATION_WINDOW_MINUTES = 1440
MAX_CORRELATION_MATCHES = 1000
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


def _correlation_filters(request: WSGIRequest) -> dict:
    """
    Return sanitized correlation search filters.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    valid_events = dict(FatTrackingEvent.Event.choices)
    event_a = request.GET.get("event_a", FatTrackingEvent.Event.JOIN)
    event_b = request.GET.get("event_b", FatTrackingEvent.Event.LEAVE)

    if event_a not in valid_events:
        event_a = FatTrackingEvent.Event.JOIN

    if event_b not in valid_events:
        event_b = FatTrackingEvent.Event.LEAVE

    try:
        window_minutes = int(
            request.GET.get(
                "window_minutes", DEFAULT_CORRELATION_WINDOW_MINUTES
            )
        )
    except (TypeError, ValueError):
        window_minutes = DEFAULT_CORRELATION_WINDOW_MINUTES

    window_minutes = max(
        1, min(window_minutes, MAX_CORRELATION_WINDOW_MINUTES)
    )

    return {
        "character": request.GET.get("character", "").strip(),
        "event_a": event_a,
        "event_b": event_b,
        "searched": request.GET.get("search") == "1",
        "window_minutes": window_minutes,
    }


def _event_delta_minutes(event_a: FatTrackingEvent, event_b: FatTrackingEvent) -> float:
    """
    Return minutes between two tracking events.

    :param event_a:
    :type event_a:
    :param event_b:
    :type event_b:
    :return:
    :rtype:
    """

    return round((event_b.observed - event_a.observed).total_seconds() / 60, 2)


def _correlate_tracking_events(filters: dict) -> dict:
    """
    Find A -> B tracking event pairs grouped by character.

    :param filters:
    :type filters:
    :return:
    :rtype:
    """

    if not filters["searched"]:
        return {"groups": [], "match_count": 0, "truncated": False}

    window = timedelta(minutes=filters["window_minutes"])
    events = (
        FatTrackingEvent.objects.select_related(
            "fat",
            "fat__character",
            "fat__fatlink",
            "solar_system",
            "ship",
        )
        .filter(event__in=[filters["event_a"], filters["event_b"]])
        .order_by(
            "fat__character__character_name",
            "fat__character__character_id",
            "observed",
            "id",
        )
    )

    if filters["character"]:
        events = events.filter(
            fat__character__character_name__icontains=filters["character"]
        )

    grouped_matches = OrderedDict()
    pending_event_a = defaultdict(list)
    match_count = 0
    truncated = False

    for tracking_event in events:
        character = tracking_event.fat.character
        character_id = character.character_id
        pending_event_a[character_id] = [
            event_a
            for event_a in pending_event_a[character_id]
            if tracking_event.observed - event_a.observed <= window
        ]

        if tracking_event.event == filters["event_b"]:
            for index, event_a in enumerate(pending_event_a[character_id]):
                if event_a.observed >= tracking_event.observed:
                    continue

                if character_id not in grouped_matches:
                    grouped_matches[character_id] = {
                        "character": character,
                        "matches": [],
                    }

                grouped_matches[character_id]["matches"].append(
                    {
                        "event_a": event_a,
                        "event_b": tracking_event,
                        "delta_minutes": _event_delta_minutes(
                            event_a=event_a, event_b=tracking_event
                        ),
                    }
                )
                del pending_event_a[character_id][index]
                match_count += 1

                if match_count >= MAX_CORRELATION_MATCHES:
                    truncated = True
                    break

                break

        if truncated:
            break

        if tracking_event.event == filters["event_a"]:
            pending_event_a[character_id].append(tracking_event)

    return {
        "groups": list(grouped_matches.values()),
        "match_count": match_count,
        "truncated": truncated,
    }


@login_required()
@permission_required(perm="afat.inspector")
def overview(request: WSGIRequest) -> HttpResponse:
    """
    Redirect the inspector root to the event inspector.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    return redirect(to="afat:inspector_event")


@login_required()
@permission_required(perm="afat.inspector")
def event_inspector(request: WSGIRequest) -> HttpResponse:
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
        "selected_inspector_page": "events",
        "total_events": paginator.count,
    }

    logger.info(msg=f"Tracking event inspector called by {request.user}")

    return render(
        request=request,
        template_name="afat/view/inspector/inspector-overview.html",
        context=context,
    )


@login_required()
@permission_required(perm="afat.inspector")
def event_correlation(request: WSGIRequest) -> HttpResponse:
    """
    FAT tracking event correlation search.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    filters = _correlation_filters(request=request)
    correlation = _correlate_tracking_events(filters=filters)

    context = {
        "correlation": correlation,
        "event_choices": FatTrackingEvent.Event.choices,
        "filters": filters,
        "max_correlation_matches": MAX_CORRELATION_MATCHES,
        "max_correlation_window_minutes": MAX_CORRELATION_WINDOW_MINUTES,
        "selected_inspector_page": "correlation",
    }

    logger.info(msg=f"Tracking event correlation called by {request.user}")

    return render(
        request=request,
        template_name="afat/view/inspector/inspector-correlation.html",
        context=context,
    )
