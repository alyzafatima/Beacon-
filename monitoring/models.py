from django.db import models
from django.contrib.auth.models import User
import secrets

class Monitor(models.Model):

    MONITOR_TYPES = [
        ('http', 'HTTP'),
        ('heartbeat', 'Heartbeat'),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=200)

    monitor_type = models.CharField(
        max_length=20,
        choices=MONITOR_TYPES
    )

    url = models.URLField(blank=True)

    expected_status = models.IntegerField(default=200)

    interval_seconds = models.IntegerField(default=60)

    grace_period_seconds = models.IntegerField(default=300)

    heartbeat_token = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):

        if self.monitor_type == "heartbeat" and not self.heartbeat_token:
            self.heartbeat_token = secrets.token_urlsafe(16)

        super().save(*args, **kwargs)

class Check(models.Model):

    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    success = models.BooleanField(default=False)

    status_code = models.IntegerField(
        null=True,
        blank=True
    )

    response_time_ms = models.IntegerField(
        null=True,
        blank=True
    )


class Incident(models.Model):

    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE
    )

    started_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    cause = models.TextField(blank=True)


class AlertChannel(models.Model):

    CHANNEL_TYPES = [
        ('slack', 'Slack'),
        ('email', 'Email'),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    channel_type = models.CharField(
        max_length=20,
        choices=CHANNEL_TYPES
    )

    webhook_url = models.URLField(blank=True)

    email_address = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)


class StatusPage(models.Model):

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    slug = models.SlugField(
        unique=True
    )

    title = models.CharField(
        max_length=200
    )

    monitors = models.ManyToManyField(
        Monitor,
        blank=True
    )

    def __str__(self):

        return self.title


class Profile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    timezone = models.CharField(
        max_length=100,
        default="Asia/Karachi"
    )

    def __str__(self):
        return self.user.username


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):

    if created:
        Profile.objects.create(
            user=instance
        )