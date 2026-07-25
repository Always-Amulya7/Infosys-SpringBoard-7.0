import os
import django
from django.db.models import Sum, Count
from django.utils import timezone
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FocusGuard.settings")
django.setup()

from WebApp.models import (
    User,
    Goal,
    Organization,
    Department,
    Invitation,
    ActivityLog,
    Analytics,
)
def get_user_by_username(username):
    return User.objects.filter(username=username).first()

def get_user_by_email(email):
    return User.objects.filter(email=email).first()

def get_org_users(organization_id):
    return User.objects.filter(organization_id=organization_id)

def get_colleagues(organization_id):
    return User.objects.filter(organization_id=organization_id, role="Employee")

def get_organization(name):
    return Organization.objects.filter(name=name).first()

def get_department(organization_id, department_name):
    return Department.objects.filter(
        organization_id=organization_id, name=department_name
    ).first()

def get_pending_invitations(organization_id):
    return Invitation.objects.filter(organization_id=organization_id)

def get_invitation_by_token(token):
    return Invitation.objects.filter(token=token).first()

def get_user_goal(user_id):
    return Goal.objects.filter(user_id=user_id).first()

def get_user_activity(user_id):
    return ActivityLog.objects.filter(user_id=user_id).order_by("-created_at")

def get_today_activity(user_id):
    today = timezone.now().date()
    return ActivityLog.objects.filter(user_id=user_id, activity_date=today).order_by(
        "-created_at"
    )

def get_activity_by_date(user_id, activity_date):
    return ActivityLog.objects.filter(
        user_id=user_id, activity_date=activity_date
    ).order_by("-created_at")

def get_org_activity(organization_id):
    return ActivityLog.objects.filter(organization_id=organization_id).order_by(
        "-created_at"
    )

def get_user_tab_history(user_id, activity_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id)
    if activity_date:
        queryset = queryset.filter(activity_date=activity_date)
    return queryset.values(
        "session_id",
        "event_type",
        "tab_id",
        "url",
        "title",
        "domain",
        "opened_at",
        "closed_at",
        "duration",
        "active_duration",
        "activity_date",
    ).order_by("-created_at")

def get_tab_session(session_id):
    return ActivityLog.objects.filter(session_id=session_id).first()

def get_current_active_tabs(user_id):
    return ActivityLog.objects.filter(user_id=user_id, closed_at__isnull=True).order_by(
        "-created_at"
    )

def get_open_tabs_count(user_id, activity_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id, event_type="tab_opened")
    if activity_date:
        queryset = queryset.filter(activity_date=activity_date)
    return queryset.count()

def get_closed_tabs_count(user_id, activity_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id, event_type="tab_closed")
    if activity_date:
        queryset = queryset.filter(activity_date=activity_date)
    return queryset.count()

def get_user_analytics(user_id, start_date=None, end_date=None):
    queryset = Analytics.objects.filter(user_id=user_id)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    return queryset

def calculate_user_total_time(user_id, start_date=None, end_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id)
    if start_date:
        queryset = queryset.filter(activity_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(activity_date__lte=end_date)
    result = queryset.aggregate(total=Sum("duration"))
    return result["total"] or 0

def calculate_user_active_time(user_id, start_date=None, end_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id)
    if start_date:
        queryset = queryset.filter(activity_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(activity_date__lte=end_date)
    result = queryset.aggregate(total=Sum("active_duration"))
    return result["total"] or 0

def calculate_org_total_time(organization_id):
    result = ActivityLog.objects.filter(organization_id=organization_id).aggregate(
        total=Sum("duration")
    )
    return result["total"] or 0

def get_website_usage(user_id, activity_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id)
    if activity_date:
        queryset = queryset.filter(activity_date=activity_date)
    return (
        queryset.values("domain")
        .annotate(total_time=Sum("duration"))
        .order_by("-total_time")
    )

def get_website_active_usage(user_id, activity_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id)
    if activity_date:
        queryset = queryset.filter(activity_date=activity_date)
    return (
        queryset.values("domain")
        .annotate(active_time=Sum("active_duration"))
        .order_by("-active_time")
    )

def get_user_activity_summary(user_id, activity_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id)
    if activity_date:
        queryset = queryset.filter(activity_date=activity_date)
    return {
        "total_time": queryset.aggregate(total=Sum("duration"))["total"] or 0,
        "active_time": queryset.aggregate(total=Sum("active_duration"))["total"] or 0,
        "tabs_opened": queryset.filter(event_type="tab_opened").count(),
        "tabs_closed": queryset.filter(event_type="tab_closed").count(),
    }

def get_organization_activity_summary(organization_id):
    activities = ActivityLog.objects.filter(organization_id=organization_id)
    return {
        "total_time": activities.aggregate(total=Sum("duration"))["total"] or 0,
        "employees": activities.values("user").distinct().count(),
        "tabs": activities.count(),
    }


def get_weekly_activity_summary(user_id):
    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday())
    queryset = ActivityLog.objects.filter(
        user_id=user_id, activity_date__gte=start_of_week, activity_date__lte=today
    )
    return queryset


def get_monthly_activity_summary(user_id):
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    queryset = ActivityLog.objects.filter(
        user_id=user_id, activity_date__gte=start_of_month, activity_date__lte=today
    )
    return queryset


def get_date_range_activity_summary(user_id, start_date, end_date):
    return ActivityLog.objects.filter(
        user_id=user_id, activity_date__gte=start_date, activity_date__lte=end_date
    )


def get_website_usage_aggregated(user_id, start_date=None, end_date=None):
    queryset = ActivityLog.objects.filter(user_id=user_id)
    if start_date:
        queryset = queryset.filter(activity_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(activity_date__lte=end_date)
    return (
        queryset.values("domain", "title")
        .annotate(total_duration=Sum("duration"), total_active=Sum("active_duration"))
        .order_by("-total_duration")
    )

