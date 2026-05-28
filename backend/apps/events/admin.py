from django.contrib import admin

from .models import EventCoverImage, EventSeries, EXDate, Event, RecurrenceOverride

admin.site.register(Event)
admin.site.register(EventSeries)
admin.site.register(EXDate)
admin.site.register(RecurrenceOverride)
admin.site.register(EventCoverImage)
