from django.contrib import admin
from .models import Monitor, Check, Incident, AlertChannel, StatusPage


admin.site.register(Monitor)
admin.site.register(Check)
admin.site.register(Incident)
admin.site.register(AlertChannel)
admin.site.register(StatusPage)