from django.contrib import admin

from apps.circulation.models import DueDateChange, LibraryPolicy, Loan, LoanRequest, MovementLog


@admin.register(LibraryPolicy)
class LibraryPolicyAdmin(admin.ModelAdmin):
    list_display = ("max_active_loans", "loan_days", "reminder_days")


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "book", "status", "requested_at")
    list_filter = ("status",)
    search_fields = ("student__enrollment", "book__title")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("student", "book", "status", "due_date", "confirmed_by")
    list_filter = ("status",)
    search_fields = ("student__enrollment", "book__title", "copy__inventory_code")


@admin.register(DueDateChange)
class DueDateChangeAdmin(admin.ModelAdmin):
    list_display = ("loan", "previous_due_date", "new_due_date", "changed_by", "changed_at")


@admin.register(MovementLog)
class MovementLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "description")
    search_fields = ("description",)
