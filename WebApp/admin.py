from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Goal,
    Organization,
    Department,
    Invitation,
    ActivityLog,
    Analytics,
)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        "username",
        "email",
        "organization",
        "department",
        "role",
        "last_login_time",
        "is_staff",
        "is_active",
    ]
    list_filter = [
        "organization",
        "department",
        "role",
        "is_staff",
        "is_active",
    ]
    search_fields = [
        "username",
        "email",
    ]
    ordering = ["-date_joined"]
    fieldsets = UserAdmin.fieldsets + (
        (
            "Organization Information",
            {
                "fields": (
                    "organization",
                    "department",
                    "role",
                    "phone",
                    "bio",
                    "last_login_time",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Organization Information",
            {
                "fields": (
                    "organization",
                    "department",
                    "role",
                    "phone",
                    "bio",
                )
            },
        ),
    )

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "name",
    ]
    ordering = ["name"]

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "organization",
        "created_at",
    ]
    list_filter = [
        "organization",
        "name",
    ]
    search_fields = [
        "name",
        "organization__name",
    ]

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "organization",
        "department",
        "role",
        "status",
        "accepted_user",
        "created_at",
    ]
    list_filter = [
        "status",
        "organization",
        "role",
    ]
    search_fields = [
        "email",
        "organization__name",
    ]

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "daily_focus_hours",
        "distraction_limit",
        "created_at",
    ]
    search_fields = [
        "user__username",
    ]

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "event_type",
        "domain",
        "tab_id",
        "duration",
        "active_duration",
        "activity_date",
        "opened_at",
        "closed_at",
    ]
    list_filter = [
        "event_type",
        "organization",
        "activity_date",
        "domain",
    ]
    search_fields = [
        "user__username",
        "domain",
        "url",
        "title",
        "session_id",
    ]
    readonly_fields = [
        "session_id",
        "created_at",
        "last_seen",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "activity_date"

@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "category",
        "total_time",
        "date",
    ]
    list_filter = [
        "organization",
        "category",
        "date",
    ]
    search_fields = [
        "user__username",
    ]
    ordering = ["-date"]
