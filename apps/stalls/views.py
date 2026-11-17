from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from .models import Stall, PaymentRecord, Vendor, UserProfile, ActivityLog, DailyReportArchive
from django.views.decorators.csrf import csrf_protect
from datetime import timedelta, date
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import reverse
from .forms import StallForm, CustomUserCreationForm, generate_next_stall_number
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .models import SystemSetting
from django.http import HttpResponse
from functools import wraps
import csv
import json


ALL_ROLES = (UserProfile.ROLE_SUPER_ADMIN, UserProfile.ROLE_MANAGER, UserProfile.ROLE_STAFF)
MANAGEMENT_ROLES = (UserProfile.ROLE_SUPER_ADMIN, UserProfile.ROLE_MANAGER)


def role_required(*allowed_roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if UserProfile.role_for(request.user) not in allowed_roles:
                messages.error(request, 'You do not have permission to access that page.')
                return redirect('stalls:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def log_activity(request, action, description):
    user = request.user if request.user.is_authenticated else None
    ActivityLog.objects.create(
        user=user,
        action=action,
        description=str(description)[:255],
    )


def infer_days_paid(payment, rent_rate):
    if not payment or not rent_rate:
        return 1
    try:
        ratio = float(payment.amount_paid) / float(rent_rate)
    except (TypeError, ValueError, ZeroDivisionError):
        return 1
    days = int(round(ratio))
    if days >= 1 and abs(ratio - days) < 0.01:
        return days
    return 1


def get_next_unpaid_date(stall, today):
    due_date = stall.next_due_date
    if not due_date:
        return today
    if not stall.date_paid:
        return max(today, due_date)
    if due_date <= stall.date_paid:
        return max(today, due_date + timedelta(days=1))

    last_payment = stall.payments.order_by('-date_paid', '-id').first()
    days_paid = infer_days_paid(last_payment, stall.rent_rate)
    if due_date == stall.date_paid + timedelta(days=days_paid - 1):
        return max(today, due_date + timedelta(days=1))
    return max(today, due_date)


@role_required(*ALL_ROLES)
def dashboard_view(request):
    query = request.GET.get('q', '')
    stalls = Stall.objects.all()
    
    if query:
        stalls = stalls.filter(
            Q(stall_number__icontains=query) |
            Q(vendor_name__icontains=query) |
            Q(category__icontains=query)
        )
    
    total_stalls = 24  
    occupied_stalls = Stall.objects.exclude(vendor_name__isnull=True).exclude(vendor_name__exact='').count()
    vacant_stalls = total_stalls - occupied_stalls

    total_revenue = PaymentRecord.objects.aggregate(total=Sum('amount_paid'))['total'] or 0.00
    
    try:
        today = timezone.now().date()
        overdue_payments = Stall.objects.filter(next_due_date__lt=today).aggregate(total=Sum('rent_rate'))['total'] or 0.00
    except Exception:
        overdue_payments = 0.00

    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_collections = PaymentRecord.objects.filter(
        date_paid__month=current_month,
        date_paid__year=current_year
    ).aggregate(total=Sum('amount_paid'))['total'] or 0.00

    context = {
        'total_revenue': total_revenue,
        'total_stalls': total_stalls,
        'occupied_stalls': occupied_stalls,
        'vacant_stalls': vacant_stalls,
        'overdue_payments': overdue_payments,
        'monthly_collections': monthly_collections,
        'stalls': stalls,
        'query': query,
    }
    return render(request, 'stalls/dashboard.html', context)


@role_required(*ALL_ROLES)
def stalls_vendors(request):
    query = request.GET.get('q')
    if query:
        stalls = Stall.objects.filter(stall_number__icontains=query) | Stall.objects.filter(vendor_name__icontains=query)
    else:
        stalls = Stall.objects.all()

    categories = sorted({stall.category or 'General' for stall in stalls})

    context = {
        'stalls': stalls,
        'categories': categories,
    }
    return render(request, 'stalls/stalls_vendors.html', context)

@role_required(*MANAGEMENT_ROLES)
def add_stall(request):
    if request.method == 'POST':
        stall_number = generate_next_stall_number()
        vendor_name = (request.POST.get('vendor_name') or '').strip().upper()
        category = request.POST.get('category')
        rent_rate = request.POST.get('daily_rate') or request.POST.get('rent_rate') or 0.00
        phone_number = request.POST.get('phone_number')
        due_date = request.POST.get('due_date') or None
        date_paid = request.POST.get('date_paid') or None

        vendor = None
        if vendor_name:
            vendor, _ = Vendor.objects.get_or_create(
                name=vendor_name,
                defaults={'contact_number': phone_number or ''},
            )

        stall = Stall.objects.create(
            stall_number=stall_number,
            vendor=vendor,
            vendor_name=vendor_name,
            category=category,
            rent_rate=rent_rate,
            contact_number=phone_number,
            next_due_date=due_date,
            date_paid=date_paid
        )
        log_activity(
            request,
            ActivityLog.ACTION_STALL,
            f'Added stall #{stall.stall_number} for vendor "{vendor_name or "N/A"}".',
        )
        return redirect('stalls:stalls_vendors')
        
    context = {
        'next_stall_number': generate_next_stall_number(),
    }
    return render(request, 'stalls/register_vendor_stall.html', context)


@role_required(*MANAGEMENT_ROLES)
def delete_selected_stalls(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_stalls')
        if selected_ids:
            deleted_count = len(selected_ids)
            Stall.objects.filter(pk__in=selected_ids).delete()
            log_activity(
                request,
                ActivityLog.ACTION_STALL,
                f'Deleted {deleted_count} selected stall(s).',
            )
    return redirect('stalls:stalls_vendors')



    

@role_required(*MANAGEMENT_ROLES)
def register_vendor_stall(request):
    if request.method == 'POST':
        # Kunin ang mga binigay na datos mula sa form
        vendor_name = (request.POST.get('vendor_name') or '').strip().upper()
        contact_number = request.POST.get('phone_number') or request.POST.get('contact_number')
        stall_number = generate_next_stall_number()
        category = request.POST.get('category')
        rent_rate = request.POST.get('daily_rate') or request.POST.get('rent_rate') or 0.00
        due_date = request.POST.get('due_date') or None

        vendor, created = Vendor.objects.get_or_create(
            name=vendor_name,
            defaults={'contact_number': contact_number or ''}
        )

        Stall.objects.create(
            stall_number=stall_number,
            vendor=vendor,
            vendor_name=vendor_name,
            category=category,
            rent_rate=rent_rate,
            contact_number=contact_number,
            next_due_date=due_date,
        )

        log_activity(
            request,
            ActivityLog.ACTION_VENDOR,
            f'Registered vendor "{vendor_name}" for stall #{stall_number}.',
        )
        return redirect('stalls:payments')

    context = {}
    return render(request, 'stalls/register_vendor_stall.html', context)


@role_required(*MANAGEMENT_ROLES)
def edit_stall(request, pk):
    stall = get_object_or_404(Stall, pk=pk)
    
    if request.method == 'POST':
        form = StallForm(request.POST, instance=stall)
        if form.is_valid():

            form.save()

            vendor_name = form.cleaned_data.get('vendor_name')
            if vendor_name:
                vendor, _ = Vendor.objects.get_or_create(
                    name=vendor_name,
                    defaults={'contact_number': form.cleaned_data.get('contact_number') or ''},
                )
            else:
                vendor = None
            stall.vendor = vendor
            stall.save(update_fields=['vendor'])

            log_activity(
                request,
                ActivityLog.ACTION_STALL,
                f'Updated stall #{stall.stall_number}.',
            )
            messages.success(request, f"Stall #{stall.stall_number} updated successfully!")
            return redirect('stalls:stalls_vendors')
    else:
        form = StallForm(instance=stall)
        
    return render(request, 'stalls/edit_stall.html', {'form': form, 'stall': stall})

@role_required(*ALL_ROLES)
def payments_view(request):
    query = request.GET.get('q')

    if query:
        stalls = Stall.objects.filter(
            Q(stall_number__icontains=query) |
            Q(vendor_name__icontains=query) |
            Q(category__icontains=query)
        )
    else:
        stalls = Stall.objects.all()

    categories = sorted({stall.category or 'General' for stall in stalls})

    context = {
        'stalls': stalls,
        'categories': categories,
        'today': date.today(),
    }
    return render(request, 'stalls/payments.html', context)


@role_required(*ALL_ROLES)
def process_payment(request, stall_id):
    stall = get_object_or_404(Stall, id=stall_id)
    today = date.today()

    if request.method == 'POST':
        amount_paid = request.POST.get('amount_paid')
        advance_days = request.POST.get('advance_days')
        payment_date = get_next_unpaid_date(stall, today)

        if advance_days:
            try:
                days_paid = max(1, int(advance_days))
            except (TypeError, ValueError):
                days_paid = 1
            amount_paid = stall.rent_rate * days_paid
        else:
            days_paid = 1

        if amount_paid:
            payment = PaymentRecord(
                stall=stall,
                amount_paid=amount_paid,
                date_paid=payment_date,
                payment_type=request.POST.get('payment_type', 'Cash'),
                reference_number=request.POST.get('reference_number') or None,
            )
            payment.received_by = request.user
            payment.save()

            stall.date_paid = payment_date
            stall.next_due_date = payment_date + timedelta(days=days_paid)
            stall.save()
            log_activity(
                request,
                ActivityLog.ACTION_PAYMENT,
                f'Recorded payment of PHP {amount_paid} for stall #{stall.stall_number}.',
            )
            return redirect('stalls:receipt', payment_id=payment.id)

    context = {
        'stall': stall,
        'default_payment_date': get_next_unpaid_date(stall, today),
    }
    return render(request, 'stalls/payment_form.html', context)



@role_required(*ALL_ROLES)
def print_receipt(request, payment_id):
    payment = get_object_or_404(
        PaymentRecord.objects.select_related('stall', 'received_by'),
        id=payment_id,
    )
    context = {'payment': payment}
    return render(request, 'stalls/receipt.html', context)

def _daily_report_data(report_date, today):
    payments = list(
        PaymentRecord.objects.filter(date_paid=report_date)
        .select_related('stall', 'received_by')
        .order_by('stall__stall_number', 'id')
    )
    total_collected = sum((payment.amount_paid for payment in payments), 0)

    all_stalls = Stall.objects.all().order_by('stall_number')
    total_stalls = max(24, all_stalls.count())

    if report_date == today:
        occupied_stalls = all_stalls.exclude(vendor_name__isnull=True).exclude(vendor_name='').count()
    else:
        occupied_stalls = len({payment.stall_id for payment in payments})

    vacant_stalls = max(total_stalls - occupied_stalls, 0)

    return {
        'payments': payments,
        'all_stalls': all_stalls,
        'total_collected': total_collected,
        'occupied_stalls': occupied_stalls,
        'vacant_stalls': vacant_stalls,
        'total_stalls': total_stalls,
        'paid_stalls_count': len({payment.stall_id for payment in payments}),
    }


@role_required(*MANAGEMENT_ROLES)
def reports_view(request):
    today = timezone.localdate()

    if request.method == 'POST':
        selected_date = parse_date(request.POST.get('report_date', '')) or today
        live = _daily_report_data(selected_date, today)
        DailyReportArchive.objects.update_or_create(
            report_date=selected_date,
            defaults={
                'total_collected': live['total_collected'],
                'occupied_stalls': live['occupied_stalls'],
                'vacant_stalls': live['vacant_stalls'],
                'generated_by': request.user,
            },
        )
        return redirect(f"{reverse('stalls:reports')}?date={selected_date.isoformat()}&print=1")

    selected_date = parse_date(request.GET.get('date', '')) or today
    live = _daily_report_data(selected_date, today)
    archive = (
        DailyReportArchive.objects.filter(report_date=selected_date)
        .select_related('generated_by')
        .first()
    )

    if archive:
        total_collected = archive.total_collected
        occupied_stalls = archive.occupied_stalls
        vacant_stalls = archive.vacant_stalls
        total_stalls = occupied_stalls + vacant_stalls
    else:
        total_collected = live['total_collected']
        occupied_stalls = live['occupied_stalls']
        vacant_stalls = live['vacant_stalls']
        total_stalls = live['total_stalls']

    payment_by_stall = {payment.stall_id: payment for payment in live['payments']}
    stall_rows = [
        {'stall': stall, 'payment': payment_by_stall.get(stall.id)}
        for stall in live['all_stalls']
    ]

    context = {
        'selected_date': selected_date,
        'today': today,
        'is_today': selected_date == today,
        'total_collected': total_collected,
        'occupied_stalls': occupied_stalls,
        'vacant_stalls': vacant_stalls,
        'total_stalls': total_stalls,
        'paid_stalls_count': live['paid_stalls_count'],
        'payments': live['payments'],
        'stall_rows': stall_rows,
        'archive': archive,
        'archives': DailyReportArchive.objects.select_related('generated_by').order_by('-report_date'),
        'report_generated_by': archive.generated_by if archive and archive.generated_by else request.user,
        'auto_print': request.GET.get('print') == '1',
        'market_name': SystemSetting.objects.values_list('market_name', flat=True).first() or 'Barangay Salong Public Market',
    }
    return render(request, 'stalls/reports.html', context)


@role_required(*MANAGEMENT_ROLES)
def activity_records_view(request):
    query = request.GET.get('q', '').strip()
    action = request.GET.get('action', '').strip()

    logs = ActivityLog.objects.select_related('user').order_by('-timestamp')

    if query:
        logs = logs.filter(
            Q(description__icontains=query) |
            Q(user__username__icontains=query)
        )

    if action in dict(ActivityLog.ACTION_CHOICES):
        logs = logs.filter(action=action)

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'stalls/activity_records.html', {
        'page_obj': page_obj,
        'logs': page_obj,
        'query': query,
        'selected_action': action,
        'action_choices': ActivityLog.ACTION_CHOICES,
        'total_logs': paginator.count,
    })


@role_required(*ALL_ROLES)
def market_map_view(request):
    stalls = Stall.objects.all()
    stalls_dict = {}

    for stall in stalls:
        try:
            clean_num = int(str(stall.stall_number).replace('#', '').strip())
            stalls_dict[clean_num] = stall
        except ValueError:
            pass

    occupied_count = sum(1 for stall in stalls_dict.values() if stall.vendor_name)
    vacant_count = max(0, 24 - occupied_count)

    context = {
        'stalls_dict': stalls_dict,
        'occupied_count': occupied_count,
        'vacant_count': vacant_count,
    }
    return render(request, 'stalls/market_map.html', context)





@role_required(*MANAGEMENT_ROLES)
def delete_multiple_stalls(request):
    if request.method == 'POST':
        stall_ids = request.POST.getlist('selected_stalls')
        if stall_ids:
            deleted_count = len(stall_ids)
            Stall.objects.filter(id__in=stall_ids).delete()
            log_activity(
                request,
                ActivityLog.ACTION_STALL,
                f'Deleted {deleted_count} selected stall(s).',
            )
            messages.success(request, "Selected stalls deleted successfully.")
        else:
            messages.warning(request, "No stalls were selected for deletion.")
    return redirect('stalls:stalls_vendors')



@role_required(*ALL_ROLES)
def stall_detail(request, pk):
    stall = get_object_or_404(Stall, pk=pk)
    payments = (
        PaymentRecord.objects.filter(stall=stall)
        .select_related('stall')
        .order_by('-date_paid', '-id')
    )

    context = {
        'stall': stall,
        'payments': payments,
    }
    return render(request, 'stalls/stall_detail.html', context)

@role_required(*ALL_ROLES)
def record_payment(request, pk):
    if request.method == 'POST':
        stall = get_object_or_404(Stall, pk=pk)
        today = timezone.now().date()
        
        # Kuhaon ang payment type kag reference number gikan sa form
        payment_type = request.POST.get('payment_type', 'Cash')
        reference_number = request.POST.get('reference_number', '')

        # 1. MAGHIMO SANG BAG-O NGA PAYMENT RECORD (Dugang sa history table)
        payment = PaymentRecord(
            stall=stall,
            amount_paid=stall.rent_rate,
            date_paid=today,
            status='Paid',
            payment_type=payment_type,
            reference_number=reference_number,
        )
        payment.received_by = request.user
        payment.save()

        # 2. I-UPDATE ANG STALL DETAILS KAG DATES
        stall.status = 'Paid'
        stall.date_paid = today
        stall.next_due_date = today + timedelta(days=30) # 30 days bago ang masunod ngadue
        stall.save()

        log_activity(
            request,
            ActivityLog.ACTION_PAYMENT,
            f'Recorded {payment_type} payment of PHP {stall.rent_rate} for stall #{stall.stall_number}.',
        )

        # Balik sa stall detail page para makita ang bag-ong record
        return redirect('stalls:stall_detail', pk=stall.pk)
    
    return redirect('stalls:stall_detail', pk=pk)


@role_required(*MANAGEMENT_ROLES)
def settings_view(request):
    # Kuhaon ang pinakaunang setting o maghimo sang default kon wala pa
    setting, created = SystemSetting.objects.get_or_create(id=1, defaults={'market_name': 'Salong Public Market'})

    export = request.GET.get('export')
    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stalls_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Stall Number', 'Vendor Name', 'Category', 'Contact Number', 'Rent Rate', 'Date Paid', 'Next Due Date'])
        for stall in Stall.objects.all().order_by('stall_number'):
            writer.writerow([
                stall.stall_number,
                stall.vendor_name or '',
                stall.category or '',
                stall.contact_number or '',
                stall.rent_rate,
                stall.date_paid or '',
                stall.next_due_date or '',
            ])
        return response

    if export == 'backup':
        payload = {
            'settings': {
                'market_name': setting.market_name,
                'default_currency': setting.default_currency,
                'market_address': setting.market_address,
            },
            'stalls': list(Stall.objects.values(
                'stall_number', 'vendor_name', 'category', 'rent_rate',
                'contact_number', 'next_due_date', 'date_paid'
            )),
        }
        response = HttpResponse(json.dumps(payload, default=str, indent=2), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="market_backup.json"'
        return response

    if request.method == 'POST':
        market_name = request.POST.get('market_name')
        if market_name:
            setting.market_name = market_name
        setting.default_currency = request.POST.get('default_currency') or setting.default_currency
        setting.market_address = request.POST.get('market_address', '').strip()
        setting.email_notifications = request.POST.get('email_notifications') == 'on'
        setting.payment_reminders = request.POST.get('payment_reminders') == 'on'
        setting.save()
        log_activity(
            request,
            ActivityLog.ACTION_SETTINGS,
            f'Updated system settings for "{setting.market_name}".',
        )
        messages.success(request, 'System settings updated successfully.')
        return redirect('stalls:settings')

    context = {
        'setting': setting
    }
    return render(request, 'stalls/settings.html', context)





@role_required(*ALL_ROLES)
def market_summary(request):
    return render(request, 'stalls/market_summary.html')

@role_required(*ALL_ROLES)
def help_support_view(request):
    return render(request, 'stalls/help_support.html')



@role_required(UserProfile.ROLE_SUPER_ADMIN)
def users_list_view(request):
    users = User.objects.all().order_by('-date_joined')
    for account in users:
        account.role_value = UserProfile.role_for(account)
        account.role_label = UserProfile.label_for(account)

    return render(request, 'stalls/users.html', {
        'users': users,
        'role_choices': UserProfile.ROLE_CHOICES,
    })


@role_required(UserProfile.ROLE_SUPER_ADMIN)
def add_user_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', UserProfile.ROLE_STAFF)
        password = request.POST.get('password') or request.POST.get('password1')
        password_confirm = request.POST.get('password2')

        errors = []
        if not username:
            errors.append('Username is required.')
        if not password:
            errors.append('Password is required.')
        if password_confirm is not None and password != password_confirm:
            errors.append('Passwords do not match.')
        if role not in dict(UserProfile.ROLE_CHOICES):
            errors.append('Please select a valid role.')
        if username and User.objects.filter(username=username).exists():
            errors.append('That username is already taken.')
        if email and User.objects.filter(email=email).exists():
            errors.append('That email is already in use.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'stalls/add_user.html', {
                'role_choices': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        log_activity(
            request,
            ActivityLog.ACTION_USER,
            f'Created user "{user.username}" with role {UserProfile.label_for(user)}.',
        )
        messages.success(request, f'User "{user.username}" has been created successfully.')
        return redirect('stalls:users')

    return render(request, 'stalls/add_user.html', {
        'role_choices': UserProfile.ROLE_CHOICES,
    })


@role_required(UserProfile.ROLE_SUPER_ADMIN)
def change_password_view(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        new_password = request.POST.get('new_password') or request.POST.get('password')
        if not new_password:
            messages.error(request, 'Please enter a new password.')
        else:
            user.set_password(new_password)
            user.save()
            log_activity(
                request,
                ActivityLog.ACTION_USER,
                f'Reset password for user "{user.username}".',
            )
            messages.success(request, f'Password updated for "{user.username}".')

    return redirect('stalls:users')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('stalls:dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = form.cleaned_data['role']
            profile.save()
            login(request, user)
            log_activity(
                request,
                ActivityLog.ACTION_USER,
                f'New account registered as {UserProfile.label_for(user)}.',
            )
            messages.success(request, 'Your account has been created successfully.')
            return redirect('stalls:dashboard')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()

    return render(request, 'stalls/signup.html', {'form': form})

def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('stalls:dashboard')

@role_required(UserProfile.ROLE_SUPER_ADMIN)
def edit_user_view(request, user_id):
    return render(request, 'stalls/edit_user.html')

@role_required(*MANAGEMENT_ROLES)
def delete_stall(request, stall_id):
    stall = get_object_or_404(Stall, id=stall_id)
    stall_number = stall.stall_number

    stall.delete()

    log_activity(
        request,
        ActivityLog.ACTION_STALL,
        f'Deleted stall #{stall_number}.',
    )

    messages.success(request, f"Stall #{stall_number} deleted successfully!")
    
    return redirect('stalls:stalls_vendors')

def login_view(request):
    return render(request, 'stalls/login.html')

def password_reset_view(request):
    return render(request, 'stalls/password_reset.html')

@role_required(*ALL_ROLES)
def vendor_detail(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    return render(request, 'stalls/vendor_detail.html', {'vendor': vendor})

@login_required
def admin_profile_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if user.is_superuser and profile.role != UserProfile.ROLE_SUPER_ADMIN:
        profile.role = UserProfile.ROLE_SUPER_ADMIN
        profile.save(update_fields=['role'])
    can_manage_role = user.is_superuser or profile.role == UserProfile.ROLE_SUPER_ADMIN
    password_form = PasswordChangeForm(user=user)

    if request.method == 'POST':
        action = request.POST.get('action', 'profile')

        if action == 'profile':
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.save()
            if can_manage_role:
                new_role = request.POST.get('role')
                if new_role in dict(UserProfile.ROLE_CHOICES):
                    profile.role = new_role
                    profile.save()
            log_activity(
                request,
                ActivityLog.ACTION_USER,
                f'Updated profile for user "{user.username}" ({UserProfile.label_for(user)}).',
            )
            messages.success(request, 'Profile details updated successfully.')
            return redirect('stalls:admin_profile')

        if action == 'password':
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                log_activity(
                    request,
                    ActivityLog.ACTION_USER,
                    f'Changed own password for user "{user.username}".',
                )
                messages.success(request, 'Password changed successfully.')
                return redirect('stalls:admin_profile')
            messages.error(request, 'Please correct the errors below.')

    recent_payments = (
        PaymentRecord.objects.select_related('stall')
        .order_by('-date_paid', '-id')[:5]
    )

    context = {
        'password_form': password_form,
        'recent_payments': recent_payments,
        'profile': profile,
        'can_manage_role': can_manage_role,
        'user_role_label': UserProfile.label_for(user),
    }
    return render(request, 'stalls/admin_profile.html', context)