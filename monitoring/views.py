from django.shortcuts import render , redirect

# Create your views here.
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .serializers import MonitorSerializer

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import *
from .tasks import send_alert

from django.db.models import Avg
from django.shortcuts import render, get_object_or_404
from datetime import timedelta
from django.utils import timezone

from .forms import *

@login_required
def account_billing(request):

    if request.method == "POST":

        form = AccountForm(
            request.POST,
            instance=request.user,
            user=request.user
        )

        if form.is_valid():

            form.save()

            return redirect("account-billing")

    else:

        form = AccountForm(
            instance=request.user,
            user=request.user
        )

    return render(
        request,
        "monitoring/account_billing.html",
        {
            "form": form
        }
    )

from django import forms
from django.contrib.auth.models import User
from .models import Profile


class AccountForm(forms.ModelForm):

    timezone = forms.CharField(
        max_length=100
    )

    class Meta:

        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
            "timezone",
        ]

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user")

        super().__init__(*args, **kwargs)

        self.user = user

        self.fields["timezone"].initial = (
            user.profile.timezone
        )

    def save(self, commit=True):

        user = super().save(commit=commit)

        user.profile.timezone = self.cleaned_data["timezone"]
        user.profile.save()
        return user

    
def landing(request):
    return render(
        request,
        "monitoring/landing.html"
    )

def public_status_page(request, slug):

    status_page = get_object_or_404(
        StatusPage,
        slug=slug
    )

    monitors = status_page.monitors.filter(
        owner=status_page.owner
    )

    monitor_data = []

    has_down = False

    for monitor in monitors:

        latest_check = Check.objects.filter(
            monitor=monitor
        ).order_by("-timestamp").first()

        is_down = Incident.objects.filter(
            monitor=monitor,
            resolved_at=None
        ).exists()

        if is_down:
            has_down = True

        recent_checks = Check.objects.filter(
            monitor=monitor
        ).order_by("-timestamp")[:30]

        monitor_data.append({
            "monitor": monitor,
            "latest_check": latest_check,
            "is_down": is_down,
            "recent_checks": recent_checks,
        })

    return render(
        request,
        "monitoring/status_page.html",
        {
            "status_page": status_page,
            "monitor_data": monitor_data,
            "has_down": has_down,
        }
    )

@login_required
def status_pages(request):

    if request.method == "POST":

        form = StatusPageForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            status_page = form.save(commit=False)

            status_page.owner = request.user

            status_page.save()

            form.save_m2m()

            return redirect("status-pages")

    else:

        form = StatusPageForm(
            user=request.user
        )

    status_pages = StatusPage.objects.filter(
        owner=request.user
    )

    return render(
        request,
        "monitoring/status_pages.html",
        {
            "form": form,
            "status_pages": status_pages,
        }
    )

@login_required
def alerts_settings(request):

    channels = AlertChannel.objects.filter(
        owner=request.user
    ).order_by("-id")

    if request.method == "POST":

        action = request.POST.get("action")

        if action == "add":

            channel_type = request.POST.get(
                "channel_type"
            )

            webhook_url = request.POST.get(
                "webhook_url",
                ""
            )

            email_address = request.POST.get(
                "email_address",
                ""
            )

            AlertChannel.objects.create(
                owner=request.user,
                channel_type=channel_type,
                webhook_url=webhook_url,
                email_address=email_address,
                is_active=True
            )

            return redirect("alerts-settings")


        if action == "toggle":

            channel_id = request.POST.get(
                "channel_id"
            )

            channel = AlertChannel.objects.filter(
                id=channel_id,
                owner=request.user
            ).first()

            if channel:

                channel.is_active = (
                    not channel.is_active
                )

                channel.save()

            return redirect("alerts-settings")


        if action == "delete":

            channel_id = request.POST.get(
                "channel_id"
            )

            AlertChannel.objects.filter(
                id=channel_id,
                owner=request.user
            ).delete()

            return redirect("alerts-settings")


    return render(
        request,
        "monitoring/alerts_settings.html",
        {
            "channels": channels
        }
    )

@login_required
def dashboard(request):

    user = request.user

    thirty_days_ago = timezone.now() - timedelta(days=30)
    ninety_days_ago = timezone.now() - timedelta(days=90)

    # --------------------------------
    # USER'S MONITORS
    # --------------------------------

    monitors = Monitor.objects.filter(
        owner=user
    )

    # --------------------------------
    # LAST 30 DAYS CHECKS
    # --------------------------------

    checks = Check.objects.filter(
        monitor__owner=user,
        timestamp__gte=thirty_days_ago
    )

    total_checks = checks.count()

    successful_checks = checks.filter(
        success=True
    ).count()

    if total_checks > 0:
        uptime = (
            successful_checks / total_checks
        ) * 100
    else:
        uptime = 0

    # --------------------------------
    # CURRENTLY DOWN MONITORS
    # --------------------------------

    down_monitors = Incident.objects.filter(
        monitor__owner=user,
        resolved_at=None
    ).values(
        "monitor"
    ).distinct().count()

    # --------------------------------
    # OPEN INCIDENTS
    # --------------------------------

    open_incidents = Incident.objects.filter(
        monitor__owner=user,
        resolved_at=None
    ).count()

    # --------------------------------
    # AVERAGE RESPONSE TIME
    # --------------------------------

    avg_response = checks.filter(
        response_time_ms__isnull=False
    ).aggregate(
        Avg("response_time_ms")
    )["response_time_ms__avg"]

    if avg_response is None:
        avg_response = 0

    # --------------------------------
    # MONITOR TABLE
    # --------------------------------

    monitor_data = []

    for monitor in monitors:

        latest_check = Check.objects.filter(
            monitor=monitor
        ).order_by(
            "-timestamp"
        ).first()

        open_incident = Incident.objects.filter(
            monitor=monitor,
            resolved_at=None
        ).exists()

        monitor_checks = Check.objects.filter(
            monitor=monitor,
            timestamp__gte=ninety_days_ago
        )

        monitor_total = monitor_checks.count()

        monitor_success = monitor_checks.filter(
            success=True
        ).count()

        if monitor_total > 0:
            monitor_uptime = (
                monitor_success / monitor_total
            ) * 100
        else:
            monitor_uptime = 0

        monitor_data.append({
            "monitor": monitor,
            "latest_check": latest_check,
            "is_down": open_incident,
            "uptime": round(monitor_uptime, 2),
        })

    context = {
        "uptime": round(uptime, 2),
        "monitor_count": monitors.count(),
        "down_monitors": down_monitors,
        "open_incidents": open_incidents,
        "avg_response": round(avg_response, 2),
        "monitor_data": monitor_data,
    }

    return render(
        request,
        "monitoring/dashboard.html",
        context
    )


@login_required
def monitor_detail(request, monitor_id):

    monitor = get_object_or_404(
        Monitor,
        id=monitor_id,
        owner=request.user
    )

    checks = Check.objects.filter(
        monitor=monitor
    ).order_by("-timestamp")[:50]

    incidents = Incident.objects.filter(
        monitor=monitor
    ).order_by("-started_at")

    open_incident = incidents.filter(
        resolved_at=None
    ).first()

    latest_check = checks.first()

    total_checks = Check.objects.filter(
        monitor=monitor
    ).count()

    successful_checks = Check.objects.filter(
        monitor=monitor,
        success=True
    ).count()

    if total_checks > 0:

        monitor_uptime = round(
            (successful_checks / total_checks) * 100,
            2
        )

    else:

        monitor_uptime = 0


    context = {

        "monitor": monitor,

        "checks": checks,

        "incidents": incidents,

        "open_incident": open_incident,

        "latest_check": latest_check,

        "monitor_uptime": monitor_uptime,

    }


    return render(
        request,
        "monitoring/monitor_detail.html",
        context
    )

def signup(request):

    if request.method == "POST":

        form = UserCreationForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect("login")

    else:

        form = UserCreationForm()

    return render(
        request,
        "registration/signup.html",
        {"form": form}
    )


class MonitorViewSet(viewsets.ModelViewSet):

    serializer_class = MonitorSerializer

    permission_classes = [
        IsAuthenticated
    ]

    def get_queryset(self):

        return Monitor.objects.filter(
            owner=self.request.user
        )

    def perform_create(self, serializer):

        serializer.save(
            owner=self.request.user
        )


def heartbeat_ping(request, token):
    try:
        monitor = Monitor.objects.get(
            heartbeat_token=token,
            monitor_type="heartbeat"
        )
    except Monitor.DoesNotExist:
        return JsonResponse({"status": "not found"}, status=404)

    Check.objects.create(
        monitor=monitor,
        success=True
    )

    open_incident = Incident.objects.filter(
        monitor=monitor,
        resolved_at=None
    ).first()

    if open_incident:
        open_incident.resolved_at = timezone.now()
        open_incident.save()

        send_alert.delay(
            open_incident.id,
            "resolved"
        )

    return JsonResponse({"status": "ok"})



@login_required
def add_monitor(request):

    if request.method == "POST":

        name = request.POST.get("name")
        monitor_type = request.POST.get("monitor_type")
        url = request.POST.get("url")
        expected_status = request.POST.get("expected_status")
        interval_seconds = request.POST.get("interval_seconds")
        grace_period_seconds = request.POST.get(
            "grace_period_seconds"
        )

        Monitor.objects.create(
            owner=request.user,
            name=name,
            monitor_type=monitor_type,
            url=url,
            expected_status=expected_status,
            interval_seconds=interval_seconds,
            grace_period_seconds=grace_period_seconds,
        )

        return redirect("dashboard")


    return render(
        request,
        "monitoring/add_monitor.html"
    )