from .models import UserProfile


def user_role(request):
    if not request.user.is_authenticated:
        return {}
    role = UserProfile.role_for(request.user)
    return {
        'user_role': role,
        'user_role_label': dict(UserProfile.ROLE_CHOICES).get(role, 'Staff / Collector'),
    }
