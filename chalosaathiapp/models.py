# models.py
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
    
class UserProfile(AbstractUser):
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    aadhaar = models.CharField(max_length=14, unique=True)
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")]
    )
    avatar = models.ImageField(upload_to="avatars/", default="default-avatar.png")
    email = models.EmailField(unique=True)
    
    # Override username to make it optional and non-unique
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "aadhaar"]

    def __str__(self):
        return self.full_name    

class Feedback(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

class Ride(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female"), ("any", "Any")]
    )
    pickup = models.CharField(max_length=255)
    pickup_coords = models.CharField(max_length=50, null=True, blank=True)
    destination = models.CharField(max_length=255)
    destination_coords = models.CharField(max_length=50, null=True, blank=True)  # Add this field
    vehicle_number = models.CharField(max_length=50)
    vehicle_model = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=20, choices=[("two-wheeler", "Two-Wheeler"), ("four-wheeler", "Four-Wheeler")])
    date = models.DateField()
    time = models.TimeField()
    distance_km = models.FloatField()
    cost = models.FloatField()
    status = models.CharField(max_length=20, choices=[("active", "Active"), ("canceled", "Canceled")], default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Add these fields for distance calculations
    pickup_distance = models.FloatField(null=True, blank=True)
    dest_distance = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.pickup} → {self.destination} by {self.user.email}"
    


class Booking(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='bookings')
    passenger = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    booking_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("canceled", "Canceled")
        ],
        default="pending"
    )
    pickup_location = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    subscription_type = models.CharField(
        max_length=20,
        choices=[
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
        ],
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Booking by {self.passenger.email} for {self.ride}"

from django.db import models

class AdminUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.username
