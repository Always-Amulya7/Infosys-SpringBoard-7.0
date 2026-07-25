from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime, date
from uuid import UUID


class RegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    organization: str
    department: str


class LoginSchema(BaseModel):
    username: str
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponseSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    organization: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class OrgAdminCreateSchema(BaseModel):
    organization: str
    username: str
    email: EmailStr
    password: str
    department: str


class OrgAdminLoginSchema(BaseModel):
    username: str
    password: str
    organization: str
    department: str


class ColleagueLoginSchema(BaseModel):
    username: str
    password: str


class OrganizationSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class DepartmentSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class InviteSchema(BaseModel):
    email: EmailStr
    department: str
    role: str = "Employee"


class InviteResponseSchema(BaseModel):
    message: str
    email: EmailStr
    department: Optional[str] = None
    token: Optional[str] = None
    status: Optional[str] = None


class AcceptInviteSchema(BaseModel):
    invite_token: str
    username: str
    password: str
    email: Optional[EmailStr] = None


class OrgUserSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    department: Optional[str] = None
    last_login_time: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class InvitationStatusSchema(BaseModel):
    id: int
    email: EmailStr
    status: str
    role: str
    created_at: datetime
    accepted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ColleagueSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    department: Optional[str] = None
    last_login_time: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class GoalSchema(BaseModel):
    daily_focus_hours: int
    distraction_limit: int
    goal_description: str


class GoalResponseSchema(BaseModel):
    daily_focus_hours: int
    distraction_limit: int
    goal_description: str
    model_config = ConfigDict(from_attributes=True)


class ActivitySchema(BaseModel):
    event_type: str
    tab_id: int
    url: Optional[str] = ""
    title: Optional[str] = ""
    domain: Optional[str] = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: int = 0
    active_duration: int = 0
    session_id: Optional[UUID] = None


class ActivityResponseSchema(BaseModel):
    id: int
    user_id: int
    session_id: UUID
    event_type: str
    tab_id: int
    url: Optional[str] = None
    title: Optional[str] = None
    domain: Optional[str] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    duration: int
    active_duration: int
    activity_date: date
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DailyActivityResponseSchema(BaseModel):
    username: str
    date: date
    total_activities: int
    activities: List[ActivityResponseSchema]


class OrgActivityResponseSchema(BaseModel):
    user_id: int
    username: str
    activities: List[ActivityResponseSchema]


class SyncTabsSchema(BaseModel):
    tabs: list


class AnalyticsRequestSchema(BaseModel):
    date: Optional[date] = None


class DateRangeAnalyticsSchema(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AnalyticsSchema(BaseModel):
    total_time: int = 0
    active_time: int = 0
    tabs_opened: int = 0
    tabs_closed: int = 0
    date: Optional[date] = None
    websites: Dict[str, int] = {}


class UserAnalyticsSchema(BaseModel):
    username: str
    analytics: AnalyticsSchema


class AnalyticsCreateSchema(BaseModel):
    category: str
    total_time: int
    date: Optional[date] = None

class TimelineSchema(BaseModel):
    event: str
    tab_id: int
    website: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    elapsed: int= 0
    active_time: int = 0

class MonitoringAnalyticsSchema(BaseModel):
    username: str
    date: date
    total_time: int
    active_time: int
    tabs_opened: int
    tabs_closed: int
    timeline: List[TimelineSchema]

class WebsiteUsageSchema(BaseModel):
    website: str
    duration: int

class AdminMonitoringSchema(BaseModel):
    username: str
    date: date
    total_time: int
    active_time: int
    tabs_opened: int
    tabs_closed: int
    websites: Dict[str, int]
    timeline: List[TimelineSchema]

class WebsiteUsageItemSchema(BaseModel):
    domain: str
    duration: int
    active_duration: int
    classification: str

class AnalyticsResponseSchema(BaseModel):
    date: str
    total_time: int
    active_time: int
    idle_time: int
    productive_time: int
    distraction_time: int
    focus_score: int
    productivity_score: int
    websites: List[WebsiteUsageItemSchema]
    most_used_websites: List[WebsiteUsageItemSchema]
    recent_activities: List[dict]

class WeeklyDaySchema(BaseModel):
    date: str
    total_time: int
    active_time: int
    idle_time: int
    productive_time: int
    distraction_time: int
    focus_score: int
    productivity_score: int

class WeeklyAnalyticsResponseSchema(BaseModel):
    week: List[WeeklyDaySchema]
    total_productive_time: int
    total_distraction_time: int
    average_focus_score: float
    total_time: int

class MonthlyDaySchema(BaseModel):
    date: str
    total_time: int
    active_time: int
    idle_time: int
    productive_time: int
    distraction_time: int
    focus_score: int
    productivity_score: int

class MonthlyAnalyticsResponseSchema(BaseModel):
    month: List[MonthlyDaySchema]
    total_productive_time: int
    total_distraction_time: int
    average_focus_score: float
    total_time: int

class HistoryDataPointSchema(BaseModel):
    date: str
    total_time: int
    active_time: int
    productive_time: int
    distraction_time: int
    focus_score: int
    productivity_score: int

class HistoryAnalyticsResponseSchema(BaseModel):
    start_date: str
    end_date: str
    total_time: int
    active_time: int
    idle_time: int
    productive_time: int
    distraction_time: int
    average_focus_score: float
    average_productivity_score: float
    data: List[HistoryDataPointSchema]

class ReportGenerateSchema(BaseModel):
    report_type: str
    format: str

class AISummaryResponseSchema(BaseModel):
    summary: str
    productivity_analysis: str
    most_distracting_websites: List[str]
    most_productive_applications: List[str]
    areas_of_improvement: List[str]
    recommendations: List[str]
    motivational_message: str
    focus_score_explanation: str

class MessageSchema(BaseModel):
    message: str
