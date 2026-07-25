from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Department(models.Model):
    TECHNICAL = "Technical"
    MANAGERIAL = "Managerial"
    OPERATIONAL = "Operational"
    DEPARTMENT_CHOICES = [
        (TECHNICAL, "Technical"),
        (MANAGERIAL, "Managerial"),
        (OPERATIONAL, "Operational"),
    ]
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "name")

    def __str__(self):
        return f"{self.organization.name} - {self.name}"

class User(AbstractUser):
    ROLE_CHOICES = [
        ("Organization Admin", "Organization Admin"),
        ("Technical Admin", "Technical Admin"),
        ("Managerial Admin", "Managerial Admin"),
        ("Operational Admin", "Operational Admin"),
        ("Employee", "Employee"),
    ]
    phone = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True)
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="Employee")
    last_login_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.username

class Invitation(models.Model):
    STATUS = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Expired", "Expired"),
    ]
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="invitations"
    )
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitations",
    )
    invited_by = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="sent_invitations"
    )
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    role = models.CharField(max_length=50, default="Employee")
    status = models.CharField(max_length=20, choices=STATUS, default="Pending")
    accepted_user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accepted_invitation",
    )

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def accept(self, user):
        self.status = "Accepted"
        self.accepted_user = user
        self.accepted_at = timezone.now()
        self.save()

    def __str__(self):
        return self.email

class Goal(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="goal")
    daily_focus_hours = models.IntegerField(default=4)
    distraction_limit = models.IntegerField(default=10)
    goal_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

class ActivityLog(models.Model):
    EVENT_TYPES = [
        ("tab_opened", "Tab Opened"),
        ("tab_closed", "Tab Closed"),
        ("tab_active", "Tab Active"),
        ("tab_switched", "Tab Switched"),
        ("url_changed", "URL Changed"),
        ("heartbeat", "Heartbeat"),
    ]
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="activity_logs"
    )
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_logs",
    )

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    tab_id = models.IntegerField(db_index=True)
    url = models.URLField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    domain = models.CharField(max_length=255, blank=True, null=True)
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Total elapsed seconds")
    active_duration = models.IntegerField(default=0, help_text="Actual focused seconds")
    activity_date = models.DateField(default=timezone.now, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "activity_date"]),
            models.Index(fields=["organization", "activity_date"]),
            models.Index(fields=["tab_id", "activity_date"]),
        ]

    def save(self, *args, **kwargs):
        if self.opened_at:
            self.activity_date = self.opened_at.date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} | " f"{self.domain} | " f"{self.event_type}"

class Analytics(models.Model):
    CATEGORY = [
        ("Entertainment", "Entertainment"),
        ("Focused", "Focused"),
        ("Engaging", "Engaging"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="analytics")
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="analytics",
    )
    category = models.CharField(max_length=50, choices=CATEGORY)
    total_time = models.IntegerField(default=0)
    date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "category", "date")

    def __str__(self):
        return f"{self.user.username} - " f"{self.category}"
