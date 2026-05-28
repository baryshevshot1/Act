from django.contrib import admin

from .models import Event, EventCoverImage, EventSeries, EXDate, RecurrenceOverride

admin.site.register(Event)
admin.site.register(EventSeries)
admin.site.register(EXDate)
admin.site.register(RecurrenceOverride)
admin.site.register(EventCoverImage)
