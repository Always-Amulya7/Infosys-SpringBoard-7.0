import os
import django
import django.db.models
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from WebApp.models import ActivityLog, User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FocusGuard.settings")
django.setup()


def _build_context_for_user(user, date):
    activities = list(ActivityLog.objects.filter(user=user, activity_date=date))
    summary = ActivityLog.objects.filter(user=user, activity_date=date).aggregate(
        total_time=django.db.models.Sum("duration"),
        active_time=django.db.models.Sum("active_duration"),
    )
    total_time = summary.get("total_time") or 0
    active_time = summary.get("active_time") or 0
    idle_time = total_time - active_time
    if idle_time < 0:
        idle_time = 0

    website_map = {}
    for activity in activities:
        domain = getattr(activity, "domain", None) or "Unknown"
        if domain not in website_map:
            website_map[domain] = {"duration": 0, "active_duration": 0}
        website_map[domain]["duration"] += activity.duration or 0
        website_map[domain]["active_duration"] += activity.active_duration or 0

    websites_sorted = sorted(website_map.items(), key=lambda x: x[1]["duration"], reverse=True)
    distracting_domains = {
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
        d = domain.lower().strip()
        return "distraction" if d in distracting_domains else "productive"

    distracting = [(d, v) for d, v in websites_sorted if classify_domain(d) == "distraction"]
    productive = [(d, v) for d, v in websites_sorted if classify_domain(d) == "productive"]

    distraction_time = sum(v["active_duration"] for _, v in distracting)
    productive_time = sum(v["active_duration"] for _, v in productive)
    focus_score = round((productive_time / active_time) * 100) if active_time > 0 else 0
    productivity_score = round((productive_time / (productive_time + distraction_time)) * 100) if (productive_time + distraction_time) > 0 else 0

    return {
        "total_time": total_time,
        "working_time": active_time,
        "idle_time": idle_time,
        "distraction_time": distraction_time,
        "focus_score": focus_score,
        "productivity_score": productivity_score,
        "most_distracting_websites": [d for d, _ in distracting[:5]],
        "most_productive_applications": [d for d, _ in productive[:5]],
        "applications": [{"name": d, "time": v["active_duration"]} for d, v in websites_sorted[:30]],
        "website_usage": [{"domain": d, "time": v["active_duration"]} for d, v in websites_sorted[:30]],
    }


@shared_task
def generate_daily_summary_for_user(user_id: int, date_str: str):
    user = User.objects.get(id=user_id)
    activity_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
    context = _build_context_for_user(user, activity_date)
    from FastAPI.prompt_builder import build_daily_prompt
    from FastAPI.ai_service import get_ai_summary
    prompt = build_daily_prompt(context)
    try:
        summary_text = get_ai_summary(prompt)
    except Exception:
        summary_text = "AI summary unavailable at this time."
    return {
        "user_id": user_id,
        "date": date_str,
        "summary": summary_text,
        "productivity_score": context["productivity_score"],
        "focus_score": context["focus_score"],
    }


@shared_task
def daily_summary_task():
    today = timezone.localdate()
    for user in User.objects.filter(is_active=True):
        generate_daily_summary_for_user.delay(user.id, str(today))


@shared_task
def weekly_summary_task():
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    for user in User.objects.filter(is_active=True):
        context = _build_context_for_user(user, start_of_week)
        # For weekly, aggregate over 7 days by summing durations per domain
        # Here simplified: use start_of_week context from last day only or build more precisely
        generate_daily_summary_for_user.delay(user.id, str(start_of_week))


@shared_task
def monthly_summary_task():
    today = timezone.localdate()
    start_of_month = today.replace(day=1)
    for user in User.objects.filter(is_active=True):
        generate_daily_summary_for_user.delay(user.id, str(start_of_month))


@shared_task
def cleanup_old_activity_logs():
    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = ActivityLog.objects.filter(created_at__lt=cutoff).delete()
    return {"deleted": deleted}
