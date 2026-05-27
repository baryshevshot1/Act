from django.contrib import admin

from .models import EventParticipant, GuestRSVP, WaitlistEntry

admin.site.register(EventParticipant)
admin.site.register(GuestRSVP)
admin.site.register(WaitlistEntry)
