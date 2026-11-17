from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone 


class Vendor(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    category = models.CharField(max_length=50, blank=True, null=True) 

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().upper()
        super().save(*args, **kwargs)


class Stall(models.Model):
    stall_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    vendor_name = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    rent_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    next_due_date = models.DateField(blank=True, null=True)
    date_paid = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.vendor_name:
            self.vendor_name = self.vendor_name.strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.next_due_date and self.next_due_date < timezone.now().date():
            return True
        return False

    @property
    def get_status(self):
        # Kon may date_paid na kag ang due date kay ara pa sa future ukon karon
        if self.date_paid and self.next_due_date and self.next_due_date >= timezone.now().date():
            return "Paid"
        elif self.next_due_date and self.next_due_date < timezone.now().date():
            return "Overdue"
        return "Pending"

    @property
    def payment_status(self):
        if self.date_paid:
            return "Paid"
        elif self.next_due_date and self.next_due_date < timezone.now().date():
            return "Overdue"
        return "Pending"

    @property
    def is_overdue(self):
        if self.next_due_date and self.next_due_date < timezone.now().date():
            return True
        return False
    
    


class PaymentRecord(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
        ('PayMaya', 'PayMaya'),
        ('Bank Transfer', 'Bank Transfer'),
    ]

    # I-retained angimo nga original fields kag foreign key relasyon
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField()
    
    # Gindugang para sa status kag payment tracking
    status = models.CharField(max_length=20, default='Paid')
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES, default='Cash')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_payments',
    )

    # I-retain angimo nga original _str_ method (o i-update kon may ginpuno ka)
    def __str__(self):
        return f"Payment for Stall {self.stall.pk} - ₱{self.amount_paid} ({self.payment_type})"



class DailyReportArchive(models.Model):
    report_date = models.DateField(unique=True)
    total_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    occupied_stalls = models.PositiveIntegerField(default=0)
    vacant_stalls = models.PositiveIntegerField(default=0)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_report_archives',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-report_date']

    def __str__(self):
        return f"Daily report for {self.report_date}"


class SystemSetting(models.Model):
    market_name = models.CharField(max_length=255, default="Salong Public Market")
    default_currency = models.CharField(max_length=10, default="PHP")
    market_address = models.CharField(max_length=255, blank=True, default="")
    email_notifications = models.BooleanField(default=True)
    payment_reminders = models.BooleanField(default=True)

    def __str__(self):
        return self.market_name


class UserProfile(models.Model):
    ROLE_SUPER_ADMIN = 'superadmin'
    ROLE_MANAGER = 'manager'
    ROLE_STAFF = 'staff'

    ROLE_CHOICES = [
        (ROLE_SUPER_ADMIN, 'Superuser'),
        (ROLE_MANAGER, 'Market Manager/Head'),
        (ROLE_STAFF, 'Staff / Collector'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @classmethod
    def role_for(cls, user):
        if user.is_superuser:
            return cls.ROLE_SUPER_ADMIN
        profile, _ = cls.objects.get_or_create(user=user)
        return profile.role

    @classmethod
    def label_for(cls, user):
        return dict(cls.ROLE_CHOICES).get(cls.role_for(user), 'Staff / Collector')


class ActivityLog(models.Model):
    ACTION_USER = 'user'
    ACTION_STALL = 'stall'
    ACTION_VENDOR = 'vendor'
    ACTION_PAYMENT = 'payment'
    ACTION_SETTINGS = 'settings'
    ACTION_AUTH = 'auth'

    ACTION_CHOICES = [
        (ACTION_USER, 'User Management'),
        (ACTION_STALL, 'Stall Update'),
        (ACTION_VENDOR, 'Vendor Update'),
        (ACTION_PAYMENT, 'Payment'),
        (ACTION_SETTINGS, 'Settings'),
        (ACTION_AUTH, 'Authentication'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_USER)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor = self.user.username if self.user else 'System'
        return f"{actor} - {self.get_action_display()} - {self.description}"



