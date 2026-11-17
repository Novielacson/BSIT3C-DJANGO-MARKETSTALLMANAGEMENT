from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views

app_name = 'stalls'

urlpatterns = [

    # Dashboard
    path('', RedirectView.as_view(pattern_name='stalls:dashboard', permanent=False), name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    

    # Stalls and Vendors
    path('stalls-vendors/', views.stalls_vendors, name='stalls_vendors'),
    path('stalls/add/', views.add_stall, name='add_stall'),
    path('stalls/edit/<int:pk>/', views.edit_stall, name='edit_stall'),
    path('delete-selected/', views.delete_selected_stalls, name='delete_selected_stalls'),
    path('stalls/delete/<int:stall_id>/', views.delete_stall, name='delete_stall'),
    path('stalls/delete-multiple/', views.delete_multiple_stalls, name='delete_multiple_stalls'),
    path('stall/<int:pk>/', views.stall_detail, name='stall_detail'),


    # Payments
    path('payments/', views.payments_view, name='payments'),
    path('payment/<int:stall_id>/', views.process_payment, name='payment_form'),
    path('pay/<int:stall_id>/', views.process_payment, name='process_payment'),
    path('payment/receipt/<int:payment_id>/', views.print_receipt, name='receipt'),
    path('pay/<int:pk>/', views.record_payment, name='record_payment'),

    # Reports
    path('reports/', views.reports_view, name='reports'),

    # Activity Records
    path('activity-records/', views.activity_records_view, name='activity_records'),
    
    # Market Map
    path('market-map/', views.market_map_view, name='market_map'),
    path('market-summary/', views.market_summary, name='market_summary'),
    path('vendor/<int:pk>/', views.vendor_detail, name='vendor_detail'),
    

    # Other pages
    path('help-support/', views.help_support_view, name='help_support'),
    path('settings/', views.settings_view, name='settings'),

    # Users
    path('users/', views.users_list_view, name='users'),
    path('users/add/', views.add_user_view, name='add_user'),
    path('users/<int:user_id>/change-password/', views.change_password_view, name='change_password'),
    path('admin-profile/', views.admin_profile_view, name='admin_profile'),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='stalls/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('signup/', views.signup_view, name='signup'),

]