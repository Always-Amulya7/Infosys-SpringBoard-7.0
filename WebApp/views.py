from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import jwt
from .models import ActivityLog

SECRET_KEY = "FOCUSGUARD_SECRET"
User = get_user_model()
def home(request):
    token = request.session.get("access_token")
    if not token:
        return redirect("/login")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception:
        request.session.flush()
        return redirect("/login")
    username = payload.get("username")
    user = User.objects.filter(username=username).first()
    if not user:
        request.session.flush()
        return redirect("/login")
    return render(
        request,
        "Home.html",
        {
            "username": user.username,
            "role": user.role,
            "organization": (user.organization.name if user.organization else None),
        },
    )

def user_activity_dashboard(request):
    token = request.session.get("access_token")
    if not token:
        return redirect("/login")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        request.session.flush()
        return redirect("/login")
    username = payload.get("username")
    user = User.objects.filter(username=username).first()
    if not user:
        return redirect("/login")
    activities = ActivityLog.objects.filter(user=user).order_by("-created_at")
    total_time = sum(activity.duration for activity in activities)
    return render(
        request,
        "Activity.html",
        {"user": user, "activities": activities, "total_time": total_time},
    )

def organization_monitor(request, user_id):
    token = request.session.get("access_token")
    if not token:
        return redirect("/login")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        request.session.flush()
        return redirect("/login")
    admin_username = payload.get("username")
    admin = User.objects.filter(username=admin_username).first()
    if not admin or admin.role != "Organization Admin":
        return redirect("/")
    employee = User.objects.filter(id=user_id, organization=admin.organization).first()
    if not employee:
        return redirect("/")
    activities = ActivityLog.objects.filter(user=employee).order_by("-created_at")
    total_time = sum(activity.duration for activity in activities)
    return render(
        request,
        "Monitor.html",
        {"employee": employee, "activities": activities, "total_time": total_time},
    )
