import os
import django
from fastapi import APIRouter, Depends, HTTPException
from django.db import models
from django.utils import timezone
from WebApp.models import ActivityLog, User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FocusGuard.settings")
django.setup()

from ..auth import get_current_user
from ..prompt_builder import build_daily_prompt
from ..ai_service import get_ai_summary

router = APIRouter(prefix="/api/summary", tags=["ai"])


@router.get("/today")
def get_today_summary(current_user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    user = User.objects.get(username=current_user["username"])
    today = timezone.localdate()
    logger.info(f"[AI] summary user={user.username} date={today}")
    activities = list(ActivityLog.objects.filter(user=user, activity_date=today))

    summary = ActivityLog.objects.filter(user=user, activity_date=today).aggregate(
        total_time=models.Sum("duration"),
        active_time=models.Sum("active_duration"),
    )
    total_time = summary["total_time"] or 0
    active_time = summary["active_time"] or 0
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
        d = (domain or "").lower().strip()
        return "distraction" if d in distracting_domains else "productive"

    distracting = [(d, v) for d, v in websites_sorted if classify_domain(d) == "distraction"]
    productive = [(d, v) for d, v in websites_sorted if classify_domain(d) == "productive"]

    distraction_time = sum(v["active_duration"] for _, v in distracting)
    productive_time = sum(v["active_duration"] for _, v in productive)
    focus_score = round((productive_time / active_time) * 100) if active_time > 0 else 0
    productivity_score = round((productive_time / (productive_time + distraction_time)) * 100) if (productive_time + distraction_time) > 0 else 0

    most_distracting = [d for d, _ in distracting[:5]]
    most_productive_apps = [d for d, _ in productive[:5]]

    context = {
        "total_time": total_time,
        "active_time": active_time,
        "idle_time": idle_time,
        "distraction_time": distraction_time,
        "working_time": active_time,
        "focus_score": focus_score,
        "productivity_score": productivity_score,
        "most_distracting_websites": most_distracting,
        "most_productive_applications": most_productive_apps,
        "applications": [{"name": d, "time": v["active_duration"]} for d, v in websites_sorted],
        "website_usage": [{"domain": d, "time": v["active_duration"]} for d, v in websites_sorted],
    }

    prompt = build_daily_prompt(context)

    try:
        ai_result = get_ai_summary(prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI summary failed: {exc}")

    if not ai_result:
        raise HTTPException(status_code=502, detail="AI summary unavailable")

    logger.info(f"[AI] summary success keys={list(ai_result.keys()) if isinstance(ai_result, dict) else type(ai_result)}")
    return ai_result
