from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password
from .models import AdminUser

@receiver(post_migrate)
def create_default_admin(sender, **kwargs):
    if not AdminUser.objects.filter(username="admin").exists():
        AdminUser.objects.create(
            username="admin",
            password=make_password("admin123")
        )
        print("✅ Default Admin Created")
    else:
        print("⚠️ Admin already exists. Skipping...")
