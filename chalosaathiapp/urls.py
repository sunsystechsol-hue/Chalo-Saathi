from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime
import random
import logging

from .models import UserProfile, Ride, Booking, Feedback
from .forms import FeedbackForm, EmailForm
from .tasks import (
    send_booking_notification_email,
    send_booking_status_notification_email,
    send_booking_status_notificatio_email
)

logger = logging.getLogger(__name__)


# -------------------------------------------
# HOME PAGE
# -------------------------------------------

def index(request):
    user_name = request.session.get('full_name')
    avatar = request.user.avatar.url if hasattr(request.user, "avatar") and request.user.avatar else None
    return render(request, "index.html", {"user_name": user_name, "avatar": avatar})


# -------------------------------------------
# LOGIN (FIXED)
# -------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        next_url = request.GET.get("next", "/")
        return redirect(next_url)

    if request.method == "POST":
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = UserProfile.objects.filter(phone=phone, email=email).first()

        if user and user.check_password(password):
            auth_login(request, user)

            # Save session info
            request.session["user_id"] = user.id
            request.session["full_name"] = user.full_name
            request.session["email"] = user.email
            request.session["phone"] = user.phone
            request.session["aadhaar"] = user.aadhaar
            request.session["gender"] = user.gender
            request.session["avatar"] = user.avatar.url if user.avatar else None

            next_url = request.GET.get("next", "/")
            return redirect(next_url)

        messages.error(request, "Invalid email, phone, or password!")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


# -------------------------------------------
# SIGNUP
# -------------------------------------------

def signup(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        aadhaar = request.POST.get("aadhaar")
        gender = request.POST.get("gender")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        avatar = request.FILES.get("avatar")

        # VALIDATIONS
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect("signup")

        if UserProfile.objects.filter(phone=phone).exists():
            messages.error(request, "Phone already registered!")
            return redirect("signup")

        if UserProfile.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("signup")

        if UserProfile.objects.filter(aadhaar=aadhaar).exists():
            messages.error(request, "Aadhaar already registered!")
            return redirect("signup")

        user = UserProfile(
            full_name=full_name,
            phone=phone,
            email=email,
            aadhaar=aadhaar,
            gender=gender,
            avatar=avatar
        )
        user.set_password(password)
        user.save()

        messages.success(request, "Signup successful! Please login.")
        return redirect("login")

    return render(request, "signup.html")


# -------------------------------------------
# PROFILE
# -------------------------------------------

@login_required
def profile(request):
    rides = Ride.objects.filter(user=request.user).order_by("-created_at")
    avatar = request.user.avatar.url if hasattr(request.user, "avatar") and request.user.avatar else None

    return render(request, "profile.html", {
        "full_name": request.session.get("full_name", request.user.full_name),
        "email": request.session.get("email", request.user.email),
        "phone": request.session.get("phone", ""),
        "aadhaar": request.session.get("aadhaar", ""),
        "gender": request.session.get("gender", ""),
        "avatar": avatar,
        "rides": rides
    })


# -------------------------------------------
# RIDE ACTIONS
# -------------------------------------------

@login_required
def cancel_ride(request, ride_id):
    Ride.objects.filter(id=ride_id, user=request.user).update(status="canceled")
    return redirect("profile")


@login_required
def resume_ride(request, ride_id):
    Ride.objects.filter(id=ride_id, user=request.user).update(status="active")
    return redirect("profile")


@login_required
def delete_ride(request, ride_id):
    Ride.objects.filter(id=ride_id, user=request.user).delete()
    return redirect("profile")


# -------------------------------------------
# FORGOT PASSWORD
# -------------------------------------------

def forgot_password(request):
    step = "email"
    success = False

    if request.method == "POST":
        # STEP 1: SEND OTP
        if "femail" in request.POST:
            femail = request.POST.get("femail")

            if UserProfile.objects.filter(email=femail).exists():
                otp = random.randint(100000, 999999)
                request.session["reset_email"] = femail
                request.session["reset_otp"] = str(otp)

                send_mail(
                    "PASSWORD RESET OTP",
                    f"Your OTP is: {otp}",
                    settings.DEFAULT_FROM_EMAIL,
                    [femail],
                    fail_silently=False
                )

                step = "otp"
                success = True
            else:
                messages.error(request, "Email not found!")

        # STEP 2: VERIFY OTP
        elif "otp" in request.POST:
            if request.POST.get("otp") == request.session.get("reset_otp"):
                step = "reset"
            else:
                messages.error(request, "Invalid OTP!")

        # STEP 3: RESET PASSWORD
        elif "new_password" in request.POST:
            new_password = request.POST.get("new_password")
            femail = request.session.get("reset_email")

            user = UserProfile.objects.get(email=femail)
            user.password = make_password(new_password)
            user.save()

            messages.success(request, "Password reset successful!")
            return redirect("login")

    return render(request, "forgot_password.html", {"step": step, "success": success})


# -------------------------------------------
# FEEDBACK
# -------------------------------------------

def feedback_view(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success"})
        return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    return render(request, "feedback.html", {"form": FeedbackForm()})


def feedback_data(request):
    feedbacks = Feedback.objects.all().order_by("-created_at")
    data = [{"name": fb.name, "message": fb.message, "created_at": fb.created_at.strftime("%Y-%m-%d %H:%M")} for fb in feedbacks]
    return JsonResponse({"feedbacks": data})


# -------------------------------------------
# OFFER RIDE
# -------------------------------------------

def offer_ride(request):
    if request.method == "POST":
        try:
            pickup_lat, pickup_lon = map(float, request.POST.get("pickup_coords").split(","))
            dest_lat, dest_lon = map(float, request.POST.get("destination_coords").split(","))
        except:
            return render(request, "success.html", {"error": "Invalid coordinates"})

        distance_km = geodesic((pickup_lat, pickup_lon), (dest_lat, dest_lon)).km
        cost = distance_km * 4

        Ride.objects.create(
            user=request.user,
            gender=request.POST.get("gender"),
            pickup=request.POST.get("pickup_address"),
            pickup_coords=request.POST.get("pickup_coords"),
            destination=request.POST.get("destination_address"),
            destination_coords=request.POST.get("destination_coords"),
            vehicle_number=request.POST.get("vehino"),
            vehicle_model=request.POST.get("vehiname"),
            vehicle_type=request.POST.get("vehicletype"),
            date=request.POST.get("date"),
            time=request.POST.get("time"),
            distance_km=round(distance_km, 2),
            cost=round(cost, 2),
        )

        return render(request, "success.html", {
            "pickup": request.POST.get("pickup_address"),
            "destination": request.POST.get("destination_address"),
            "distance": round(distance_km, 2),
            "cost": round(cost, 2),
        })

    return render(request, "index.html")


# -------------------------------------------
# FIND RIDE
# -------------------------------------------

@login_required
def find_ride(request):
    if request.method == "POST":
        pickup_coords = request.POST.get("pickup_coords1")
        destination_coords = request.POST.get("destination_coords1")

        try:
            pickup_lat, pickup_lon = map(float, pickup_coords.split(","))
            dest_lat, dest_lon = map(float, destination_coords.split(","))
        except:
            return render(request, "index.html", {"error": "Invalid coordinates"})

        search_params = {
            "pickup": request.POST.get("from"),
            "destination": request.POST.get("to"),
            "date": request.POST.get("date"),
            "time": request.POST.get("time"),
            "gender": request.POST.get("gender"),
            "pickup_coords": pickup_coords,
            "destination_coords": destination_coords,
        }

        request.session["search_params"] = search_params

        rides = Ride.objects.filter(status="active")

        matching = []
        for ride in rides:
            try:
                rlat, rlon = map(float, ride.pickup_coords.split(","))
                ploc = (pickup_lat, pickup_lon)
                rloc = (rlat, rlon)
                distance = geodesic(ploc, rloc).km

                if distance <= 5:
                    matching.append(ride)
            except:
                continue

        return render(request, "ride_results.html", {"rides": matching, "search_params": search_params})

    return render(request, "index.html")


# -------------------------------------------
# BOOK RIDE
# -------------------------------------------

@login_required
def book_ride(request, ride_id):
    if request.method != "POST":
        messages.error(request, "Invalid request!")
        return redirect("ride_results")

    ride = get_object_or_404(Ride, id=ride_id, status="active")

    if ride.user == request.user:
        messages.error(request, "You cannot book your own ride!")
        return redirect("ride_results")

    if Booking.objects.filter(ride=ride, passenger=request.user).exists():
        messages.error(request, "Already booked!")
        return redirect("ride_results")

    booking = Booking.objects.create(
        ride=ride,
        passenger=request.user,
        pickup_location=ride.pickup,
        status="pending",
        contact_number=request.user.phone,
        message=request.POST.get("message", "")
    )

    send_booking_notification_email.delay(booking.id)

    return redirect("choose_subscription", booking_id=booking.id)


# -------------------------------------------
# SUBSCRIPTION
# -------------------------------------------

@login_required
def choose_subscription(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, passenger=request.user, status="pending")
    ride = booking.ride
    base = ride.cost

    weekly = base * 1.5
    monthly = base * 5
    quarterly = base * 14

    if request.method == "POST":
        sub = request.POST.get("subscription_type")

        if sub in ["weekly", "monthly", "quarterly"]:
            booking.subscription_type = sub
            booking.save()

            return redirect("booking_confirmation", booking_id=booking_id)

        messages.error(request, "Invalid subscription!")

    return render(request, "subscription_options.html", {
        "booking": booking,
        "ride": ride,
        "weekly_cost": round(weekly, 2),
        "monthly_cost": round(monthly, 2),
        "quarterly_cost": round(quarterly, 2)
    })


# -------------------------------------------
# MY BOOKINGS
# -------------------------------------------

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(passenger=request.user).order_by("-booking_time")
    return render(request, "my_booking.html", {"bookings": bookings})


# -------------------------------------------
# RIDE BOOKINGS FOR DRIVER
# -------------------------------------------

@login_required
def ride_bookings(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)
    bookings = Booking.objects.filter(ride=ride).order_by("-booking_time")

    for b in bookings:
        if b.subscription_type == "weekly":
            b.total_cost = ride.cost * 1.5
            b.plan_name = "Weekly"
        elif b.subscription_type == "monthly":
            b.total_cost = ride.cost * 5
            b.plan_name = "Monthly"
        elif b.subscription_type == "quarterly":
            b.total_cost = ride.cost * 14
            b.plan_name = "Quarterly"
        else:
            b.total_cost = ride.cost
            b.plan_name = "One-Time"

        b.passenger_name = b.passenger.full_name or b.passenger.email

    return render(request, "ride_bookings.html", {"ride": ride, "bookings": bookings})


# -------------------------------------------
# BOOKING CONFIRMATION
# -------------------------------------------

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, passenger=request.user)
    return render(request, "booking_confirmation.html", {"booking": booking})
