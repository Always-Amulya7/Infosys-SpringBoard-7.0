import os
import django
import uuid
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FocusGuard.settings")
django.setup()
try:
    from FocusGuard.celery import app as celery_app
except Exception:
    celery_app = None
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from .schemas import *
from .jwt_handler import create_token, verify_token
from .auth import get_current_user, get_org_admin, get_employee_user
from .redis_client import redis_client
from .email_service import send_invite
from .routes import analytics as analytics_routes, ai as ai_routes
from WebApp.models import (
    User,
    Goal,
    Organization,
    Department,
    Invitation,
    ActivityLog,
    Analytics,
)
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="FocusGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory="Templates/assets"), name="assets")
app.include_router(analytics_routes.router)
app.include_router(ai_routes.router)
templates = Jinja2Templates(directory="Templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    import logging
    logger = logging.getLogger(__name__)
    token = request.cookies.get("access_token")
    logger.info(f"[HOME] path=/ token_present={token is not None}")
    if not token:
        logger.info("[HOME] No token cookie, serving Login.html")
        return templates.TemplateResponse(request=request, name="Login.html")
    payload = verify_token(token)
    if not payload:
        logger.info("[HOME] Invalid token, serving Login.html")
        return templates.TemplateResponse(request=request, name="Login.html")
    username = payload.get("username")
    session = redis_client.get(f"user_session:{username}")
    if not session:
        logger.info(f"[HOME] No Redis session for {username}, serving Login.html")
        return templates.TemplateResponse(request=request, name="Login.html")
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.info(f"[HOME] User {username} not found, serving Login.html")
        return templates.TemplateResponse(request=request, name="Login.html")
    logger.info(f"[HOME] User {username} authenticated, serving Home.html")
    response = templates.TemplateResponse(
        request=request,
        name="Home.html",
        context={
            "username": user.username,
            "role": user.role,
            "organization": (user.organization.name if user.organization else None),
        },
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="Register.html")

@app.post("/register")
def register(data: RegisterSchema):
    if User.objects.filter(username=data.username).exists():
        raise HTTPException(400, "Username already exists")
    organization, _ = Organization.objects.get_or_create(name=data.organization)
    department, _ = Department.objects.get_or_create(
        organization=organization, name=data.department
    )
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=make_password(data.password),
        organization=organization,
        department=department,
        role="Employee",
    )
    token = create_token(
        {
            "username": user.username,
            "role": user.role,
            "organization_id": organization.id,
        }
    )
    redis_client.setex(f"user_session:{user.username}", 604800, token)
    return {
        "message": "Registration successful",
        "access_token": token,
        "token_type": "bearer",
    }

@app.post("/login", response_model=TokenSchema)
def login(data: LoginSchema):
    user = User.objects.filter(username=data.username).first()
    if not user:
        raise HTTPException(404, "User not found")
    if not check_password(data.password, user.password):
        raise HTTPException(401, "Invalid password")
    user.last_login_time = timezone.now()
    user.save()
    token = create_token(
        {
            "username": user.username,
            "role": user.role,
            "organization_id": user.organization.id if user.organization else None,
        }
    )
    redis_client.setex(f"user_session:{user.username}", 604800, token)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/create-orgadmin")
def create_orgadmin(data: OrgAdminCreateSchema):
    organization, _ = Organization.objects.get_or_create(name=data.organization)
    department, _ = Department.objects.get_or_create(
        organization=organization, name=data.department
    )
    if User.objects.filter(username=data.username).exists():
        raise HTTPException(400, "Username already exists")
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=make_password(data.password),
        organization=organization,
        department=department,
        role="Organization Admin",
    )
    return {"message": "Organization Admin Created", "username": user.username}

@app.post("/orgadminlogin", response_model=TokenSchema)
def org_admin_login(data: OrgAdminLoginSchema):
    user = User.objects.filter(username=data.username).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role != "Organization Admin":
        raise HTTPException(403, "Organization Admin required")
    if not check_password(data.password, user.password):
        raise HTTPException(401, "Invalid password")
    token = create_token(
        {
            "username": user.username,
            "role": user.role,
            "organization_id": user.organization.id,
        }
    )
    redis_client.setex(f"user_session:{user.username}", 604800, token)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/invite")
def invite_employee(data: InviteSchema, current_user=Depends(get_org_admin)):
    admin = User.objects.get(username=current_user["username"])
    department, _ = Department.objects.get_or_create(
        organization=admin.organization, name=data.department
    )
    invitation = Invitation.objects.create(
        organization=admin.organization,
        department=department,
        invited_by=admin,
        email=data.email,
        role=data.role,
    )
    send_invite(data.email, str(invitation.token))
    return {"message": "Invitation sent", "token": str(invitation.token)}

@app.post("/acceptinvited")
def accept_invitation(data: AcceptInviteSchema):
    invitation = Invitation.objects.filter(token=data.invite_token).first()
    if not invitation:
        raise HTTPException(404, "Invalid invitation")
    if invitation.status != "Pending":
        raise HTTPException(400, "Invitation already used")
    if invitation.is_expired():
        invitation.status = "Expired"
        invitation.save()
        raise HTTPException(400, "Invitation expired")
    if User.objects.filter(username=data.username).exists():
        raise HTTPException(400, "Username exists")
    user = User.objects.create(
        username=data.username,
        email=invitation.email,
        password=make_password(data.password),
        organization=invitation.organization,
        department=invitation.department,
        role=invitation.role,
    )
    invitation.accept(user)
    return {"message": "Invitation accepted", "username": user.username}

@app.post("/colleguelogin", response_model=TokenSchema)
def colleague_login(data: ColleagueLoginSchema):
    user = User.objects.filter(username=data.username).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role != "Employee":
        raise HTTPException(403, "Only employees can login")
    if not check_password(data.password, user.password):
        raise HTTPException(401, "Invalid password")
    user.last_login_time = timezone.now()
    user.save()
    token = create_token(
        {
            "username": user.username,
            "role": user.role,
            "organization_id": user.organization.id,
        }
    )
    redis_client.setex(f"user_session:{user.username}", 604800, token)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/profile")
def profile(current_user=Depends(get_current_user)):
    return {"user": current_user}

@app.get("/colleague/profile")
def colleague_profile(current_user=Depends(get_employee_user)):
    user = User.objects.get(username=current_user["username"])
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "organization": user.organization.name,
    }

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@app.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    redis_client.delete(f"user_session:{payload['username']}")
    return {"message": "Logged out"}
@app.post("/goal")
def create_goal(goal: GoalSchema, current_user=Depends(get_current_user)):
    user = User.objects.get(username=current_user["username"])
    Goal.objects.update_or_create(
        user=user,
        defaults={
            "daily_focus_hours": goal.daily_focus_hours,
            "distraction_limit": goal.distraction_limit,
            "goal_description": goal.goal_description,
        },
    )
    return {"message": "Goal saved successfully"}
@app.get("/goal")
def get_goal(current_user=Depends(get_current_user)):
    user = User.objects.get(username=current_user["username"])
    goal = Goal.objects.filter(user=user).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    return {
        "daily_focus_hours": goal.daily_focus_hours,
        "distraction_limit": goal.distraction_limit,
        "goal_description": goal.goal_description,
    }
@app.post("/activities")
def create_activity(
    data: ActivitySchema,
    current_user=Depends(get_current_user)
):
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[ACTIVITY] Received event={data.event_type} for user={current_user['username']} tab_id={data.tab_id} payload={data.model_dump()}")

    user = User.objects.get(
        username=current_user["username"]
    )
    session_id = (
        data.session_id
        if data.session_id
        else uuid.uuid4()
    )
    activity = ActivityLog.objects.filter(
        user=user,
        tab_id=data.tab_id,
        closed_at__isnull=True
    ).order_by(
        "-created_at"
    ).first()

    if activity:
        logger.info(f"[ACTIVITY] Updating existing activity id={activity.id} event={data.event_type}")
        activity.url = data.url
        activity.title = data.title
        activity.domain = data.domain
        activity.event_type = data.event_type
        activity.last_seen = timezone.now()

        if data.duration:
            if data.event_type == "tab_closed":
                activity.duration = data.duration
            else:
                activity.duration += data.duration

        if data.active_duration:
            activity.active_duration = data.active_duration

        if data.event_type == "tab_closed":
            activity.closed_at = (
                data.end_time
                if data.end_time
                else timezone.now()
            )
        activity.save()
        logger.info(f"[ACTIVITY] Saved activity id={activity.id} duration={activity.duration} active_duration={activity.active_duration}")
    else:
        opened_at = data.start_time if data.start_time else timezone.now()
        activity = ActivityLog.objects.create(
            user=user,
            organization=user.organization,
            event_type=data.event_type,
            tab_id=data.tab_id,
            url=data.url,
            title=data.title,
            domain=data.domain,
            opened_at=opened_at,
            closed_at=data.end_time,
            duration=data.duration or 0,
            active_duration=data.active_duration or 0,
            session_id=session_id,
            activity_date=opened_at.date()
        )
        logger.info(f"[ACTIVITY] Created new activity id={activity.id} event={data.event_type} duration={activity.duration} active_duration={activity.active_duration}")

    return {
        "username": user.username,
        "activity": {
            "id": activity.id,
            "tab_id": activity.tab_id,
            "event": activity.event_type,
            "website": activity.domain,
            "title": activity.title,
            "start_time": activity.opened_at,
            "end_time": activity.closed_at,
            "elapsed_time": activity.duration,
            "active_time": activity.active_duration
        }
    }
@app.get("/activities")
def get_today_activities(current_user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    user = User.objects.get(username=current_user["username"])
    today = timezone.localdate()
    activities = ActivityLog.objects.filter(user=user, activity_date=today).order_by(
        "-opened_at"
    )
    logger.info(f"[ACTIVITIES] user={user.username} date={today} count={activities.count()}")
    return {
        "username": user.username,
        "date": today,
        "activities": [
            {
                "tab_id": activity.tab_id,
                "event": activity.event_type,
                "website": activity.domain,
                "url": activity.url,
                "title": activity.title,
                "start_time": activity.opened_at,
                "end_time": activity.closed_at,
                "elapsed_time": activity.duration,
                "active_time": activity.active_duration,
            }
            for activity in activities
        ],
    }
@app.get("/analytics")
def analytics(date: str = None, current_user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    user = User.objects.get(username=current_user["username"])
    if date:
        try:
            selected_date = timezone.datetime.strptime(date, "%Y-%m-%d").date()
        except:
            raise HTTPException(400, "Invalid date format")
    else:
        selected_date = timezone.localdate()
    activities = ActivityLog.objects.filter(
        user=user, activity_date=selected_date
    ).order_by("-opened_at")
    logger.info(f"[ANALYTICS] user={user.username} date={selected_date} count={activities.count()}")
    response = {
        "username": user.username,
        "date": selected_date,
        "summary": {
            "total_time": 0,
            "active_time": 0,
            "tabs_opened": 0,
            "tabs_closed": 0,
        },
        "websites": {},
        "timeline": [],
    }
    for activity in activities:
        response["summary"]["total_time"] += activity.duration
        response["summary"]["active_time"] += activity.active_duration
        if activity.event_type == "tab_opened":
            response["summary"]["tabs_opened"] += 1
        if activity.event_type == "tab_closed":
            response["summary"]["tabs_closed"] += 1
        if activity.domain:
            if activity.domain not in response["websites"]:
                response["websites"][activity.domain] = 0
            response["websites"][activity.domain] += activity.duration
        response["timeline"].append(
            {
                "tab_id": activity.tab_id,
                "event": activity.event_type,
                "website": activity.domain,
                "url": activity.url,
                "title": activity.title,
                "start_time": activity.opened_at,
                "end_time": activity.closed_at,
                "elapsed": activity.duration,
                "active_time": activity.active_duration,
            }
        )
    return response
@app.get("/org/users")
def organization_users(current_user=Depends(get_org_admin)):
    users = User.objects.filter(organization_id=current_user["organization_id"])
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "department": (user.department.name if user.department else None),
            "last_login": user.last_login_time,
        }
        for user in users
    ]
@app.get("/org/activity/{user_id}")
def organization_activity(user_id: int, current_user=Depends(get_org_admin)):
    import logging
    logger = logging.getLogger(__name__)
    employee = User.objects.filter(
        id=user_id, organization_id=current_user["organization_id"]
    ).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    today = timezone.localdate()
    activities = ActivityLog.objects.filter(
        user=employee, activity_date=today
    ).order_by("-opened_at")
    logger.info(f"[ORG_ACTIVITY] admin={current_user['username']} employee={employee.username} date={today} count={activities.count()}")
    return {
        "employee": {
            "id": employee.id,
            "username": employee.username,
            "email": employee.email,
        },
        "date": today,
        "activities": [
            {
                "tab_id": activity.tab_id,
                "website": activity.domain,
                "url": activity.url,
                "title": activity.title,
                "event": activity.event_type,
                "start_time": activity.opened_at,
                "end_time": activity.closed_at,
                "duration": activity.duration,
                "active_duration": activity.active_duration,
            }
            for activity in activities
        ],
    }
@app.get("/org/analytics/{user_id}")
def organization_analytics(user_id: int, current_user=Depends(get_org_admin)):
    import logging
    logger = logging.getLogger(__name__)
    employee = User.objects.filter(
        id=user_id, organization_id=current_user["organization_id"]
    ).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    today = timezone.localdate()
    activities = ActivityLog.objects.filter(user=employee, activity_date=today)
    logger.info(f"[ORG_ANALYTICS] admin={current_user['username']} employee={employee.username} date={today} count={activities.count()}")
    result = {
        "username": employee.username,
        "date": today,
        "total_time": 0,
        "active_time": 0,
        "tabs_opened": 0,
        "tabs_closed": 0,
        "websites": {},
        "timeline": [],
    }
    for activity in activities:
        result["total_time"] += activity.duration
        result["active_time"] += activity.active_duration
        if activity.event_type == "tab_opened":
            result["tabs_opened"] += 1
        if activity.event_type == "tab_closed":
            result["tabs_closed"] += 1
        if activity.domain:
            if activity.domain not in result["websites"]:
                result["websites"][activity.domain] = 0
            result["websites"][activity.domain] += activity.duration
        result["timeline"].append(
            {
                "tab_id": activity.tab_id,
                "website": activity.domain,
                "title": activity.title,
                "url": activity.url,
                "event": activity.event_type,
                "start_time": activity.opened_at,
                "end_time": activity.closed_at,
                "duration": activity.duration,
                "active_duration": activity.active_duration,
            }
        )
    return result
