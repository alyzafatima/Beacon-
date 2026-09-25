import time
import requests

from django.utils import timezone
from celery import shared_task
from django.core.mail import send_mail

from .models import Monitor, Check, Incident, AlertChannel


@shared_task
def check_http_monitor(monitor_id):

    monitor = Monitor.objects.get(id=monitor_id)

    start_time = time.perf_counter()

    try:
        response = requests.get(
            monitor.url,
            timeout=10
        )

        status_code = response.status_code

    except requests.RequestException:

        status_code = None

    end_time = time.perf_counter()

    response_time_ms = int(
        (end_time - start_time) * 1000
    )

    success = (
        status_code == monitor.expected_status
    )

    Check.objects.create(
        monitor=monitor,
        success=success,
        status_code=status_code,
        response_time_ms=response_time_ms
    )

    recent_checks = Check.objects.filter(
        monitor=monitor
    ).order_by("-timestamp")[:3]

    open_incident = Incident.objects.filter(
        monitor=monitor,
        resolved_at=None
    ).first()

    # Open a new incident after 3 consecutive failures
    if len(recent_checks) == 3 and all(
        not check.success for check in recent_checks
    ):
        if not open_incident:

            incident = Incident.objects.create(
                monitor=monitor
            )

            # Send immediate DOWN alert
            send_alert.delay(
                incident.id,
                "opened"
            )

            # Schedule escalation after 5 minutes
            send_alert.apply_async(
                args=[incident.id, "escalation"],
                countdown=300
            )

    # Resolve existing incident when monitor becomes healthy
    if success and open_incident:

        open_incident.resolved_at = timezone.now()
        open_incident.save()

        # Send recovery alert
        send_alert.delay(
            open_incident.id,
            "resolved"
        )


@shared_task
def dispatch_http_checks():

    monitors = Monitor.objects.filter(
        monitor_type="http",
        is_active=True
    )

    for monitor in monitors:
        check_http_monitor.delay(monitor.id)


@shared_task
def sweep_heartbeat_monitors():

    monitors = Monitor.objects.filter(
        monitor_type="heartbeat",
        is_active=True
    )

    for monitor in monitors:

        latest_check = Check.objects.filter(
            monitor=monitor
        ).order_by("-timestamp").first()

        if latest_check:
            last_check_time = latest_check.timestamp
        else:
            last_check_time = monitor.created_at

        elapsed_seconds = (
            timezone.now() - last_check_time
        ).total_seconds()

        allowed_seconds = (
            monitor.interval_seconds +
            monitor.grace_period_seconds
        )

        open_incident = Incident.objects.filter(
            monitor=monitor,
            resolved_at=None
        ).first()

        if elapsed_seconds > allowed_seconds:

            if not open_incident:

                incident = Incident.objects.create(
                    monitor=monitor,
                    cause="Heartbeat missed"
                )

                # Send immediate DOWN alert
                send_alert.delay(
                    incident.id,
                    "opened"
                )

                # Schedule escalation after 5 minutes
                send_alert.apply_async(
                    args=[incident.id, "escalation"],
                    countdown=300
                )


@shared_task
def send_alert(incident_id, event):

    incident = Incident.objects.get(id=incident_id)

    monitor = incident.monitor

    channels = AlertChannel.objects.filter(
        owner=monitor.owner,
        is_active=True
    )

    if event == "opened":

        status = "DOWN"

    elif event == "resolved":

        status = "back UP"

    elif event == "escalation":

        # If incident has already been resolved,
        # do not send the escalation alert.
        if incident.resolved_at is not None:
            return

        status = "STILL DOWN"

    message = f"[Beacon] {monitor.name} is {status}"

    for channel in channels:

        if channel.channel_type == "slack":

            requests.post(
                channel.webhook_url,
                json={"text": message}
            )

        elif channel.channel_type == "email":

            send_mail(
                subject=f"[Beacon] {monitor.name} alert",
                message=message,
                from_email=None,
                recipient_list=[channel.email_address]
            )