from django.contrib import admin
from .models import Ticket, TicketMessage, Notice

class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'student', 'cohort', 'status', 'created_at')
    list_filter = ('status', 'cohort', 'created_at')
    search_fields = ('subject', 'student__username', 'student__email')
    inlines = [TicketMessageInline]

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'cohort', 'author', 'is_active', 'created_at')
    list_filter = ('is_active', 'cohort', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Lecturers can only see and manage notices they created, or notices for their cohorts
        from courses.models import Cohort
        return qs.filter(models.Q(author=request.user) | models.Q(cohort__lecturers=request.user)).distinct()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "cohort" and not request.user.is_superuser:
            # Lecturers can only target cohorts they are assigned to
            from courses.models import Cohort
            kwargs["queryset"] = Cohort.objects.filter(lecturers=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change: # If creating new notice
            obj.author = request.user
        super().save_model(request, obj, form, change)
