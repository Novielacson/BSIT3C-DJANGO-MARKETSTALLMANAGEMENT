import re

from django import forms
from .models import Stall, Vendor, UserProfile
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm


def generate_next_stall_number():
    """Return max numeric stall number + 1 (e.g. existing 1, 2, 5 -> '6')."""
    highest = 0
    for value in Stall.objects.values_list('stall_number', flat=True):
        match = re.search(r'\d+', str(value or ''))
        if match:
            highest = max(highest, int(match.group()))
    return str(highest + 1)


class StallForm(forms.ModelForm):
    class Meta:
        model = Stall
        fields = [
            'stall_number', 
            'vendor_name',  # Palitan ang 'vendor' ng 'vendor_name'
            'contact_number', 
            'category', 
            'rent_rate', 
            'date_paid'
        ]
        widgets = {
            'stall_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor_name': forms.TextInput(attrs={'class': 'form-control'}), # Dito rin
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'rent_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_paid': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_paid'].required = False
        self.fields['stall_number'].required = False
        self.fields['stall_number'].widget = forms.HiddenInput()
        if not self.instance.pk:
            self.fields['stall_number'].initial = generate_next_stall_number()

    def clean_stall_number(self):
        if self.instance.pk:
            return self.instance.stall_number
        return generate_next_stall_number()

    def clean_vendor_name(self):
        value = self.cleaned_data.get('vendor_name')
        return value.strip().upper() if value else value


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['name', 'contact_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
        }




class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}))
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, initial=UserProfile.ROLE_STAFF, label='Account Role')

    field_order = ['username', 'email', 'role', 'password1', 'password2']

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.update({'class': css_class})

# Custom Login Form (Naga-allow sang Username ukon Email)
class EmailOrUsernameLoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username or email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}))
