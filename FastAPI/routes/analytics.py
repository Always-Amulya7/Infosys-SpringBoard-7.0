import os
import django
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from django.db.models import Sum, Count
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FocusGuard.settings")
django.setup()

from WebApp.models import ActivityLog, User
from ..auth import get_current_user
from ..schemas import (
    AnalyticsResponseSchema,
    WeeklyAnalyticsResponseSchema,
    MonthlyAnalyticsResponseSchema,
    HistoryAnalyticsResponseSchema,
    WebsiteUsageItemSchema,
    WeeklyDaySchema,
    MonthlyDaySchema,
    HistoryDataPointSchema,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

DISTRACTING_DOMAINS = {
    "youtube.com", "www.youtube.com", "facebook.com", "www.facebook.com",
    "twitter.com", "x.com", "www.x.com", "instagram.com", "www.instagram.com",
    "tiktok.com", "www.tiktok.com", "reddit.com", "www.reddit.com",
    "netflix.com", "www.netflix.com", "twitch.tv", "www.twitch.tv",
    "discord.com", "www.discord.com",
    "snapchat.com", "www.snapchat.com", "pinterest.com", "www.pinterest.com",
    "amazon.com", "www.amazon.com", "ebay.com", "www.ebay.com",
    "bing.com", "www.bing.com", "duckduckgo.com", "www.duckduckgo.com",
}


def classify_domain(domain):
    if not domain:
        return "productive"
    domain_lower = domain.lower().strip()
    if domain_lower in DISTRACTING_DOMAINS:
        return "distraction"
    for d in DISTRACTING_DOMAINS:
        if domain_lower == d or domain_lower.endswith("." + d):
            return "distraction"
    return "productive"


def build_website_aggregation(activities):
    website_map = {}
    for activity in activities:
        domain = activity.domain or "Unknown"
        if domain not in website_map:
            website_map[domain] = {
                "domain": domain,
                "duration": 0,
                "active_duration": 0,
                "classification": classify_domain(domain),
                "title": activity.title or domain,
            }
        website_map[domain]["duration"] += activity.duration or 0
        website_map[domain]["active_duration"] += activity.active_duration or 0
        if activity.title and activity.title != domain:
            website_map[domain]["title"] = activity.title

    websites = list(website_map.values())
    websites.sort(key=lambda x: x["duration"], reverse=True)
    return websites


def calculate_scores(websites, active_time, total_time):
    distraction_time = sum(w["active_duration"] for w in websites if w["classification"] == "distraction")
    productive_time = sum(w["active_duration"] for w in websites if w["classification"] == "productive")
    idle_time = (total_time or 0) - (active_time or 0)
    if idle_time < 0:
        idle_time = 0

    if active_time and active_time > 0 and productive_time > 0:
        focus_score = round((productive_time / active_time) * 100)
    else:
        focus_score = 0

    denom = productive_time + distraction_time
    if denom > 0:
        productivity_score = round((productive_time / denom) * 100)
    else:
        productivity_score = 0

    return {
        "idle_time": idle_time,
        "productive_time": productive_time,
        "distraction_time": distraction_time,
        "focus_score": focus_score,
        "productivity_score": productivity_score,
    }


@router.get("/today", response_model=AnalyticsResponseSchema)
def get_today_analytics(current_user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    user = User.objects.get(username=current_user["username"])
    today = timezone.localdate()
    logger.info(f"[ANALYTICS] today user={user.username} date={today}")
    activities = ActivityLog.objects.filter(user=user, activity_date=today)
    logger.info(f"[ANALYTICS] today activities count={activities.count()}")

    summary = activities.aggregate(
        total_time=Sum("duration"),
        active_time=Sum("active_duration"),
    )
    total_time = summary["total_time"] or 0
    active_time = summary["active_time"] or 0

    websites = build_website_aggregation(activities)
    scores = calculate_scores(websites, active_time, total_time)

    recent = list(activities.order_by("-created_at")[:20].values(
        "tab_id", "event_type", "domain", "url", "title", "opened_at", "closed_at", "duration", "active_duration"
    ))

    logger.info(f"[ANALYTICS] today response total_time={total_time} active_time={active_time} websites={len(websites)} recent={len(recent)}")
    return {
        "date": str(today),
        "total_time": total_time,
        "active_time": active_time,
        **scores,
        "websites": websites,
        "most_used_websites": websites[:10],
        "recent_activities": recent,
    }


@router.get("/week", response_model=WeeklyAnalyticsResponseSchema)
def get_week_analytics(current_user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    user = User.objects.get(username=current_user["username"])
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    logger.info(f"[ANALYTICS] week user={user.username} start={start_of_week} end={today}")

    week_days = []
    total_productive = 0
    total_distraction = 0
    total_focus_sum = 0
    total_time_sum = 0

    for i in range(7):
        day = start_of_week + timedelta(days=i)
        if day > today:
            continue
        day_activities = ActivityLog.objects.filter(user=user, activity_date=day)
        summary = day_activities.aggregate(
            total_time=Sum("duration"),
            active_time=Sum("active_duration"),
        )
        day_total = summary["total_time"] or 0
        day_active = summary["active_time"] or 0
        websites = build_website_aggregation(day_activities)
        scores = calculate_scores(websites, day_active, day_total)

        total_productive += scores["productive_time"]
        total_distraction += scores["distraction_time"]
        total_focus_sum += scores["focus_score"]
        total_time_sum += day_total

        week_days.append(WeeklyDaySchema(
            date=str(day),
            total_time=day_total,
            active_time=day_active,
            **{k: scores[k] for k in ["idle_time", "productive_time", "distraction_time", "focus_score", "productivity_score"]},
        ))

    avg_focus = round(total_focus_sum / len(week_days), 1) if week_days else 0.0

    logger.info(f"[ANALYTICS] week response days={len(week_days)} total_time={total_time_sum}")
    return WeeklyAnalyticsResponseSchema(
        week=week_days,
        total_productive_time=total_productive,
        total_distraction_time=total_distraction,
        average_focus_score=avg_focus,
        total_time=total_time_sum,
    )


@router.get("/month", response_model=MonthlyAnalyticsResponseSchema)
def get_month_analytics(current_user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    user = User.objects.get(username=current_user["username"])
    today = timezone.localdate()
    start_of_month = today.replace(day=1)
    logger.info(f"[ANALYTICS] month user={user.username} start={start_of_month} end={today}")

    month_days = []
    total_productive = 0
    total_distraction = 0
    total_focus_sum = 0
    total_time_sum = 0

    current_day = start_of_month
    while current_day <= today:
        day_activities = ActivityLog.objects.filter(user=user, activity_date=current_day)
        summary = day_activities.aggregate(
            total_time=Sum("duration"),
            active_time=Sum("active_duration"),
        )
        day_total = summary["total_time"] or 0
        day_active = summary["active_time"] or 0
        websites = build_website_aggregation(day_activities)
        scores = calculate_scores(websites, day_active, day_total)

        total_productive += scores["productive_time"]
        total_distraction += scores["distraction_time"]
        total_focus_sum += scores["focus_score"]
        total_time_sum += day_total

        month_days.append(MonthlyDaySchema(
            date=str(current_day),
            total_time=day_total,
            active_time=day_active,
            **{k: scores[k] for k in ["idle_time", "productive_time", "distraction_time", "focus_score", "productivity_score"]},
        ))
        current_day += timedelta(days=1)

    avg_focus = round(total_focus_sum / len(month_days), 1) if month_days else 0.0

    logger.info(f"[ANALYTICS] month response days={len(month_days)} total_time={total_time_sum}")
    return MonthlyAnalyticsResponseSchema(
        month=month_days,
        total_productive_time=total_productive,
        total_distraction_time=total_distraction,
        average_focus_score=avg_focus,
        total_time=total_time_sum,
    )


@router.get("/history", response_model=HistoryAnalyticsResponseSchema)
def get_history_analytics(
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user=Depends(get_current_user),
):
    user = User.objects.get(username=current_user["username"])
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    if start > end:
        raise HTTPException(400, "start_date must be before end_date")

    activities = ActivityLog.objects.filter(
        user=user, activity_date__gte=start, activity_date__lte=end
    )

    summary = activities.aggregate(
        total_time=Sum("duration"),
        active_time=Sum("active_duration"),
    )
    total_time = summary["total_time"] or 0
    active_time = summary["active_time"] or 0

    websites = build_website_aggregation(activities)
    scores = calculate_scores(websites, active_time, total_time)

    data_points = []
    current = start
    while current <= end:
        day_acts = ActivityLog.objects.filter(user=user, activity_date=current)
        day_summary = day_acts.aggregate(
            total_time=Sum("duration"),
            active_time=Sum("active_duration"),
        )
        day_total = day_summary["total_time"] or 0
        day_active = day_summary["active_time"] or 0
        day_websites = build_website_aggregation(day_acts)
        day_scores = calculate_scores(day_websites, day_active, day_total)
        data_points.append(HistoryDataPointSchema(
            date=str(current),
            total_time=day_total,
            active_time=day_active,
            **{k: day_scores[k] for k in ["productive_time", "distraction_time", "focus_score", "productivity_score"]},
        ))
        current += timedelta(days=1)

    avg_focus = round(sum(d.focus_score for d in data_points) / len(data_points), 1) if data_points else 0.0
    avg_prod = round(sum(d.productivity_score for d in data_points) / len(data_points), 1) if data_points else 0.0

    logger.info(f"[ANALYTICS] history response start={start} end={end} days={len(data_points)}")
    return HistoryAnalyticsResponseSchema(
        start_date=str(start),
        end_date=str(end),
        total_time=total_time,
        active_time=active_time,
        **scores,
        average_focus_score=avg_focus,
        average_productivity_score=avg_prod,
        data=data_points,
    )
