from django.shortcuts import render, redirect
from .models import Ride, UserProfile
from django.contrib import messages
from .forms import FeedbackForm
from django.http import JsonResponse
from .models import Feedback
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout
from django.core.mail import send_mail
from .forms import EmailForm
from django.contrib.auth.hashers import make_password
import random
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.gis.measure import D
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Ride, Booking
from django.db import transaction
from celery import shared_task
from django.utils.html import strip_tags
import logging
from .tasks import send_booking_status_notification_email, send_booking_notification_email,send_booking_status_notificatio_email
from django.core.mail import EmailMultiAlternatives
from chalosaathiapp.models import UserProfile
# Create your views here.
def index(request):
     user_name = request.session.get('full_name')  # None if not logged in
     return render(request, "index.html", {"user_name": user_name, 'avatar': request.user.avatar.url if hasattr(request.user, 'avatar') and request.user.avatar else None })

@login_required
def profile(request):
    # Fetch the user's rides
    rides = Ride.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, "profile.html", {
        "full_name": request.session.get("full_name", request.user.get_full_name()),
        "email": request.session.get("email", request.user.email),
        "phone": request.session.get("phone", ""),
        "aadhaar": request.session.get("aadhaar", ""),
        "gender": request.session.get("gender", ""),
        'avatar': request.user.avatar.url if hasattr(request.user, 'avatar') and request.user.avatar else None,
        "rides": rides,
    })

@login_required
def cancel_ride(request, ride_id):
    try:
        ride = Ride.objects.get(id=ride_id, user=request.user)
        ride.status = 'canceled'
        ride.save()
    except Ride.DoesNotExist:
        pass
    return redirect('profile')

@login_required
def resume_ride(request, ride_id):
    try:
        ride = Ride.objects.get(id=ride_id, user=request.user)
        ride.status = 'active'
        ride.save()
    except Ride.DoesNotExist:
        pass
    return redirect('profile')

@login_required
def delete_ride(request, ride_id):
    try:
        ride = Ride.objects.get(id=ride_id, user=request.user)
        ride.delete()
    except Ride.DoesNotExist:
        pass  # Optionally log or display an error
    return redirect("profile")



logger = logging.getLogger(__name__)

@login_required
def ride_results(request):
    logger.info(f"ride_results called with session={request.session.get('search_params', {})}")
    search_params = request.session.get('search_params', {})
    if not search_params:
        logger.warning("No search_params in session, redirecting to find_ride")
        return redirect('find_ride')

    user_gender = request.user.gender
    if not user_gender:
        logger.warning("No user gender, rendering with error")
        return render(request, 'ride_results.html', {'error': 'Please specify your gender in your profile.'})

    pickup_lat, pickup_lon = map(float, search_params['pickup_coords'].split(','))
    date = search_params['date']
    distance_filter = float(request.GET.get('distance', 2.0))  # Default to 2km

    rides = Ride.objects.filter(status='active', date=date)
    if user_gender == 'Male':
        rides = rides.filter(gender__in=['Male', 'any'])
    elif user_gender == 'Female':
        rides = rides.filter(gender__in=['Female', 'any'])
    else:
        rides = rides.filter(gender='any')

    filtered_rides = []
    for ride in rides:
        if not ride.pickup_coords:
            continue
        try:
            ride_lat, ride_lon = map(float, ride.pickup_coords.split(','))
            distance = geodesic((pickup_lat, pickup_lon), (ride_lat, ride_lon)).km
            if distance <= distance_filter:
                cost_per_ride = ride.distance_km * (4 if ride.vehicle_type == 'two-wheeler' else 6)
                filtered_rides.append({
                    'ride': ride,
                    'distance_from_search': round(distance, 2),
                    'cost_per_ride': round(cost_per_ride, 2),
                })
        except (ValueError, AttributeError):
            continue

    logger.info(f"Rendering ride_results with {len(filtered_rides)} rides")
    return render(request, 'ride_results.html', {
        'rides': filtered_rides,
        'search_params': search_params,  # Pass search_params to template
        'distance_filter': distance_filter,
        'error': None,
    })


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

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect("signup")

        
        if UserProfile.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered!")
            return redirect("signup")

        
        if UserProfile.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("signup")

        
        if UserProfile.objects.filter(aadhaar=aadhaar).exists():
            messages.error(request, "Aadhaar number already registered!")
            return redirect("signup")

        # Save user securely
        user = UserProfile(
            full_name=full_name,
            phone=phone,
            email=email,
            aadhaar=aadhaar,
            gender=gender,
            avatar=avatar
        )
        user.set_password(password)  # hashes the password
        user.save()

        messages.success(request, "Signup successful! Please login.")
        return redirect("login")

    return render(request, "signup.html")

def login(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Find user with phone + email
        user = UserProfile.objects.filter(phone=phone, email=email).first()

        if user and user.check_password(password):
            auth_login(request, user)  
            request.session['user_id'] = user.id
            request.session['full_name'] = user.full_name
            request.session['email'] = user.email
            request.session['phone'] = user.phone
            request.session['aadhaar'] = user.aadhaar
            request.session['gender'] = user.gender
            request.session['avatar'] = user.avatar.url if user.avatar else None
            messages.success(request, "Login successful!")
            return redirect("index")  
        else:
            messages.error(request, "Invalid phone, email, or password!")


    return render(request, "login.html")

def logout_view(request):
        logout(request)
        request.session.flush()  # clear custom session values
        return redirect("login")

def aboutus(request):
    return render(request, "aboutus.html")

def forgot_password(request):
    step = "email"  # default step
    success = False

    if request.method == "POST":
        if "femail" in request.POST:  # Step 1: Email check
            femail = request.POST.get("femail")
            if UserProfile.objects.filter(email=femail).exists():
                otp = random.randint(100000, 999999)
                request.session['reset_email'] = femail
                request.session['reset_otp'] = str(otp)

                send_mail(
                    "PASSWORD RESET OTP",
                    f"Your OTP is: {otp}",
                    "your_email@gmail.com",
                    [femail],
                    fail_silently=False,
                )
                success = True
                step = "otp"
            else:
                messages.error(request, "Email not found!")

        elif "otp" in request.POST:  # Step 2: OTP verification
            entered_otp = request.POST.get("otp")
            saved_otp = request.session.get("reset_otp")
            if entered_otp == saved_otp:
                step = "reset"
            else:
                messages.error(request, "Invalid OTP!")

        elif "new_password" in request.POST:  # Step 3: Reset password
            new_password = request.POST.get("new_password")
            femail = request.session.get("reset_email")
            user = UserProfile.objects.get(email=femail)
            user.password = make_password(new_password)  # encrypt password
            user.save()

            messages.success(request, "Password reset successful!")
            return redirect("login")

    return render(request, "forgot_password.html", {"step": step, "success": success})

def feedback_view(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success", "message": "Feedback submitted successfully"})
        else:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
    else:
        form = FeedbackForm()
    return render(request, 'feedback.html', {'form': form})

def feedback_data(request):
    feedbacks = Feedback.objects.all().order_by('-created_at')
    data = [
        {
            "name": fb.name,
            "message": fb.message,
            "created_at": fb.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for fb in feedbacks
    ]
    return JsonResponse({"feedbacks": data})

def send_email_view(request):
    success = False
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            send_mail(
                subject,
                message,
                'your_email@gmail.com',   # From email
                [recipient],
                fail_silently=False,
            )
            success = True
    else:
        form = EmailForm()
    
    return render(request, 'send_email.html', {'form': form, 'success': success})

def maptest(request):
    return render(request, "maptest.html")

def distance_view(request):
    distance = None
    error = None
    origin = destination = ""
    origin_lat = origin_lng = dest_lat = dest_lng = None

    if request.method == "POST":
        origin = request.POST.get("origin")
        destination = request.POST.get("destination")

        geolocator = Nominatim(user_agent="myapp")
        loc1 = geolocator.geocode(origin)
        loc2 = geolocator.geocode(destination)

        if loc1 and loc2:
            origin_lat, origin_lng = loc1.latitude, loc1.longitude
            dest_lat, dest_lng = loc2.latitude, loc2.longitude

            distance = round(geodesic((origin_lat, origin_lng), (dest_lat, dest_lng)).km, 2)
        else:
            error = "One or both locations not found."

    return render(request, "distance.html", {
        "origin": origin,
        "destination": destination,
        "distance": distance,
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "destination_lat": dest_lat,
        "destination_lng": dest_lng,
        "error": error
    })

def clean_address(address: str) -> str:
    """
    Clean up long addresses before geocoding.
    Keeps only the first 3 comma-separated parts if it's too detailed.
    """
    if not address:
        return ""
    parts = [p.strip() for p in address.split(",")]
    if len(parts) > 3:
        return ", ".join(parts[:3])  # keep first 3 chunks (more reliable for Nominatim)
    return address


def offer_ride(request):
    if request.method == "POST":
        gender = request.POST.get("gender")
        pickup_address = request.POST.get("pickup_address")
        destination_address = request.POST.get("destination_address")
        pickup_coords = request.POST.get("pickup_coords")
        destination_coords = request.POST.get("destination_coords")
        vehino = request.POST.get("vehino")
        vehiname = request.POST.get("vehiname")
        vehicle_type = request.POST.get("vehicletype")
        date = request.POST.get("date")
        time = request.POST.get("time")

        # Validate coordinates
        try:
            pickup_lat, pickup_lon = map(float, pickup_coords.split(','))
            destination_lat, destination_lon = map(float, destination_coords.split(','))
            pickup = (pickup_lat, pickup_lon)
            destination = (destination_lat, destination_lon)
        except (ValueError, AttributeError):
            return render(request, "success.html", {
                "error": "❌ Invalid location coordinates."
            })

        # Calculate distance and cost
        distance_km = geodesic(pickup, destination).km
        cost = distance_km * 4  # ₹4 per km

        # Save ride to database
        Ride.objects.create(
            user=request.user,
            gender=gender,
            pickup=pickup_address,
            pickup_coords=pickup_coords,  # Save pickup coordinates
            destination=destination_address,
            destination_coords=destination_coords,  # Save destination coordinates
            vehicle_number=vehino,
            vehicle_model=vehiname,
            vehicle_type=vehicle_type,
            date=date,
            time=time,
            distance_km=round(distance_km, 2),
            cost=round(cost, 2)
        )

        return render(request, "success.html", {
            "pickup": pickup_address,
            "destination": destination_address,
            "distance": round(distance_km, 2),
            "cost": round(cost, 2)
        })

    return render(request, "index.html")

@login_required
def find_ride(request):
    if request.method == "POST":
        gender = request.POST.get("gender")
        pickup_address = request.POST.get("from")
        destination_address = request.POST.get("to")
        pickup_coords = request.POST.get("pickup_coords1")
        destination_coords = request.POST.get("destination_coords1")
        date = request.POST.get("date")
        time = request.POST.get("time")
        
        # Validate coordinates
        try:
            pickup_lat, pickup_lon = map(float, pickup_coords.split(','))
            destination_lat, destination_lon = map(float, destination_coords.split(','))
            pickup = (pickup_lat, pickup_lon)
            destination = (destination_lat, destination_lon)
        except (ValueError, AttributeError):
            return render(request, "index.html", {
                "error": "❌ Invalid location coordinates."
            })
        
        # Store search_params in session
        search_params = {
            'pickup': pickup_address,
            'destination': destination_address,
            'date': date,
            'time': time,
            'gender': gender,
            'pickup_coords': pickup_coords,
            'destination_coords': destination_coords,
        }
        request.session['search_params'] = search_params
        
        # Get all active rides
        all_rides = Ride.objects.filter(status="active")
        
        # Filter by gender preference
        if gender != "any":
            all_rides = all_rides.filter(gender=gender)
        
        # Filter by date (ensure future rides)
        if date:
            try:
                search_date = datetime.strptime(date, "%Y-%m-%d").date()
                today = datetime.now().date()
                if search_date < today:
                    return render(request, "index.html", {
                        "error": "❌ Please select a future date."
                    })
                all_rides = all_rides.filter(date__gte=search_date)
            except ValueError:
                return render(request, "index.html", {
                    "error": "❌ Invalid date format."
                })
        
        # Calculate distances and filter by route similarity
        matching_rides = []
        for ride in all_rides:
            try:
                if ride.pickup_coords:
                    ride_pickup_lat, ride_pickup_lon = map(float, ride.pickup_coords.split(','))
                    ride_pickup = (ride_pickup_lat, ride_pickup_lon)
                    
                    pickup_distance = geodesic(pickup, ride_pickup).km
                    
                    if ride.destination_coords:
                        ride_dest_lat, ride_dest_lon = map(float, ride.destination_coords.split(','))
                        ride_destination = (ride_dest_lat, ride_dest_lon)
                        dest_distance = geodesic(destination, ride_destination).km
                        
                        if pickup_distance <= 5 and dest_distance <= 10:
                            ride.pickup_distance = round(pickup_distance, 2)
                            ride.dest_distance = round(dest_distance, 2)
                            matching_rides.append(ride)
            except (ValueError, AttributeError):
                continue
        
        matching_rides.sort(key=lambda r: r.pickup_distance)
        
        return render(request, "ride_results.html", {
            "rides": matching_rides,
            "search_params": search_params,
        })
    
    return render(request, "index.html")



@login_required
def book_ride(request, ride_id):
    logger.info(f"book_ride called with ride_id={ride_id}, method={request.method}, POST={request.POST}")

    if request.method != 'POST':
        messages.error(request, 'Invalid request method. Please use the booking form.')
        logger.warning("Redirecting to ride_results due to GET request")
        return redirect('ride_results')

    with transaction.atomic():
        ride = get_object_or_404(
            Ride.objects.select_for_update(),
            id=ride_id,
            status='active'
        )

        logger.info(f"Ride datetime check: Date={ride.date}, Time={ride.time}")
        ride_datetime = datetime.combine(ride.date, ride.time)
        if timezone.is_naive(ride_datetime):
            ride_datetime = timezone.make_aware(ride_datetime)
        logger.info(f"Computed ride_datetime: {ride_datetime}, Now: {timezone.now()}")
        if ride_datetime < timezone.now():
            messages.error(request, 'This ride has already occurred.')
            logger.warning("Redirecting to ride_results due to past ride")
            return redirect('ride_results')

        if ride.user == request.user:
            messages.error(request, 'You cannot book your own ride.')
            logger.warning("Redirecting to ride_results due to self-booking")
            return redirect('ride_results')

        gender = request.POST.get('gender') or getattr(request.user, 'gender', None)
        if not gender:
            messages.error(request, 'Your profile must include gender information to book rides.')
            logger.warning("Redirecting to ride_results due to missing gender")
            return redirect('ride_results')

        # logger.info(f"Gender check: user={gender}, ride={ride.gender}")
        # if ride.gender != 'any' and ride.gender != gender:
        #     messages.error(request, 'You do not meet the gender preference for this ride.')
        #     logger.warning("Redirecting to ride_results due to gender mismatch")
        #     return redirect('ride_results')

        if Booking.objects.filter(ride=ride, passenger=request.user).exists():
            messages.error(request, 'You have already booked this ride.')
            logger.warning("Redirecting to ride_results due to duplicate booking")
            return redirect('ride_results')

        current_bookings = Booking.objects.filter(ride=ride).count()
        if hasattr(ride, 'available_seats') and current_bookings >= ride.available_seats:
            messages.error(request, 'This ride is fully booked.')
            logger.warning("Redirecting to ride_results due to no available seats")
            return redirect('ride_results')

        contact_number = getattr(request.user, 'phone', '')
        if not contact_number:
            messages.error(request, 'You must add a phone number to your profile before booking a ride.')
            logger.warning("Redirecting to profile page due to missing phone")
            return redirect('profile')

        booking = Booking.objects.create(
            ride=ride,
            passenger=request.user,
            pickup_location=ride.pickup,
            status='pending',
            contact_number=contact_number,
            message=request.POST.get('message', '')
        )

        send_booking_notification_email.delay(booking.id)
        logger.info(f"Booking created, redirecting to choose_subscription with booking_id={booking.id}")

    return redirect('choose_subscription', booking_id=booking.id)

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, passenger=request.user)
    return render(request, 'booking_confirmation.html', {'booking': booking})


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(passenger=request.user).order_by('-booking_time')
    return render(request, 'my_booking.html', {'bookings': bookings})

@login_required
def ride_bookings(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)
    bookings = Booking.objects.filter(ride=ride).select_related('passenger').order_by('-booking_time')

    # Calculate plan name, total cost, and passenger name for each booking
    for booking in bookings:
        base_cost = ride.cost
        if booking.subscription_type == 'weekly':
            booking.total_cost = base_cost * 1.5
            booking.plan_name = "Weekly Plan (7 Rides)"
        elif booking.subscription_type == 'monthly':
            booking.total_cost = base_cost * 5
            booking.plan_name = "Monthly Plan (30 Rides)"
        elif booking.subscription_type == 'quarterly':
            booking.total_cost = base_cost * 14
            booking.plan_name = "Quarterly Plan (90 Rides)"
        else:
            booking.total_cost = base_cost
            booking.plan_name = "One-Time Ride"
        
        # Compute passenger name with fallback to email
        booking.passenger_name = booking.passenger.full_name if booking.passenger.full_name else booking.passenger.email

    return render(request, 'ride_bookings.html', {
        'ride': ride,
        'bookings': bookings,
    })
@login_required
def confirm_booking(request, booking_id):
    with transaction.atomic():
        booking = get_object_or_404(Booking, id=booking_id, ride__user=request.user)
        if booking.status == 'pending':
            booking.status = 'confirmed'
            booking.save()
            # Call synchronously for development (no .delay())
            send_booking_status_notificatio_email(booking.id, 'confirmed')
            messages.success(request, 'Booking confirmed successfully.')
        else:
            messages.error(request, 'Booking cannot be confirmed.')
    return redirect('ride_bookings', ride_id=booking.ride.id)

@login_required
def cancel_booking_driver(request, booking_id):
    with transaction.atomic():
        booking = get_object_or_404(Booking, id=booking_id, ride__user=request.user)
        if booking.status != 'canceled':
            booking.status = 'canceled'
            booking.save()
            # Call synchronously for development (no .delay())
            send_booking_status_notification_email(booking.id, 'canceled')
            messages.success(request, 'Booking canceled successfully.')
        else:
            messages.error(request, 'Booking is already canceled.')
    return redirect('ride_bookings', ride_id=booking.ride.id)

@login_required
def choose_subscription(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, passenger=request.user, status='pending')
    ride = booking.ride
    base_cost = ride.cost

    # Subscription costs
    weekly_cost = base_cost * 1.5
    monthly_cost = base_cost * 5
    quarterly_cost = base_cost * 14

    if request.method == 'POST':
        subscription_type = request.POST.get('subscription_type')
        if subscription_type in ['weekly', 'monthly', 'quarterly']:
            booking.subscription_type = subscription_type
            booking.save()

            driver = ride.user
            if driver and driver.email:
                # Calculate cost for selected plan
                total_cost = {
                    'weekly': weekly_cost,
                    'monthly': monthly_cost,
                    'quarterly': quarterly_cost
                }[subscription_type]

                # Use full_name directly with fallback to email
                driver_name = driver.full_name if driver.full_name else driver.email
                passenger_name = request.user.full_name if request.user.full_name else request.user.email

                # Render HTML content
                html_content = render_to_string('booking_email.html', {
                    'driver_name': driver_name,
                    'passenger_name': passenger_name,
                    'ride': ride,
                    'subscription_type': subscription_type.title(),
                    'total_cost': round(total_cost, 2),
                })

                subject = 'New Booking Confirmation - Subscription Selected'
                from_email = settings.DEFAULT_FROM_EMAIL
                to_email = [driver.email]

                try:
                    msg = EmailMultiAlternatives(subject, '', from_email, to_email)
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                    messages.success(request, f'Booking confirmed with {subscription_type} subscription! Driver notified via email.')
                except Exception as e:
                    print(f"Failed to send email: {e}")
                    messages.warning(request, f'Booking confirmed, but email could not be sent.')

            return redirect('booking_confirmation', booking_id=booking.id)
        messages.error(request, 'Invalid subscription option.')

    return render(request, 'subscription_options.html', {
        'booking': booking,
        'ride': ride,
        'weekly_cost': round(weekly_cost, 2),
        'monthly_cost': round(monthly_cost, 2),
        'quarterly_cost': round(quarterly_cost, 2),
    })



# admin



from django.db.models import Q


#--------------------------------
def admin_login(request):
    return render(request,'admin-login.html')


def admin_panel(request):
    """
    Fetches summary statistics and recent users for the admin dashboard.
    """
    # --- Calculate Summary Stats (from previous step) ---
    total_users = UserProfile.objects.count()
    total_bookings = Booking.objects.count()
    total_rides = Ride.objects.count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    
    # --- NEW: Fetch Recent Users ---
    # Get the 5 most recently joined users
    recent_users = UserProfile.objects.order_by('-date_joined')[:5]
    
    # --- Prepare the context dictionary ---
    # Add the recent_users to the context
    context = {
        'total_users': total_users,
        'total_bookings': total_bookings,
        'total_rides': total_rides,
        'pending_bookings': pending_bookings,
        'recent_users': recent_users, # Pass the new data to the template
    }

    # --- Render the template with the context ---
    return render(request, 'admin-panel.html', context)


# views.py
from django.shortcuts import render, get_object_or_404, redirect
from .models import UserProfile
from django.db.models import Q

def admin_user_list(request):
    search = request.GET.get("search")
    gender = request.GET.get("gender")

    users = UserProfile.objects.all()

    if search:
        users = users.filter(
            Q(full_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    if gender and gender != "All":
        users = users.filter(gender=gender)

    context = {
        "users": users,
        "search": search,
        "gender": gender,
    }
    return render(request, "users_list.html", context)


def admin_user_detail(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)
    return render(request, "user_detail.html", {"user": user})


def admin_user_edit(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)

    if request.method == "POST":
        user.full_name = request.POST.get("full_name")
        user.phone = request.POST.get("phone")
        user.aadhaar = request.POST.get("aadhaar")
        user.gender = request.POST.get("gender")

        if request.FILES.get("avatar"):
            user.avatar = request.FILES["avatar"]

        user.save()
        return redirect("admin_user_detail", user_id=user.id)

    return render(request, "user_edit.html", {"user": user})


def admin_user_delete(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)
    user.delete()
    return redirect("admin_user_list")


from django.shortcuts import render
from .models import Booking

def search_users_by_city(request):
    city = request.GET.get("city", "")
    bookings = []
    summary = {}

    if city:
        bookings = Booking.objects.select_related("passenger", "ride").filter(
            pickup_location__icontains=city
        )

        # 🔹 Visual Summary (Status Count)
        summary = {
            "total": bookings.count(),
            "pending": bookings.filter(status="pending").count(),
            "confirmed": bookings.filter(status="confirmed").count(),
            "canceled": bookings.filter(status="canceled").count(),
        }

    context = {
        "bookings": bookings,
        "city": city,
        "summary": summary,
    }

    return render(request, "search_users_by_city.html", context)

from .models import AdminUser
from django.contrib.auth.hashers import check_password
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            admin = AdminUser.objects.get(username=username)

            # ✅ SECURE PASSWORD CHECK
            if check_password(password, admin.password):
                request.session['admin_id'] = admin.id
                return redirect('admin_panel')
            else:
                messages.error(request, "Invalid username or password")

        except AdminUser.DoesNotExist:
            messages.error(request, "Invalid username or password")

    return render(request, "admin-login.html")

def admin_logout(request):
    request.session.flush()
    return redirect('admin_login')

def add_admin(request):
    # ✅ Only logged-in admin can access
    if not request.session.get('admin_id'):
        return redirect('admin_login')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('add_admin')

        if AdminUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('add_admin')

        AdminUser.objects.create(
            username=username,
            password=make_password(password)
        )

        messages.success(request, "New admin added successfully ✅")
        return redirect('add_admin')

    return render(request, "add-admin.html")

def admin_view_bookings(request):
    # ✅ Only logged-in admin can access
    if not request.session.get('admin_id'):
        return redirect('admin_login')

    status_filter = request.GET.get('status')

    if status_filter:
        bookings = Booking.objects.filter(status=status_filter).order_by('-booking_time')
    else:
        bookings = Booking.objects.all().order_by('-booking_time')

    return render(request, "admin-bookings.html", {
        "bookings": bookings,
        "status_filter": status_filter
    })

def admin_view_feedback(request):
    # ✅ Only logged-in admin can access
    if not request.session.get('admin_id'):
        return redirect('admin_login')

    feedbacks = Feedback.objects.all().order_by('-created_at')

    return render(request, "admin-feedback.html", {
        "feedbacks": feedbacks
    })


def delete_feedback(request, id):
    # ✅ Only logged-in admin can delete
    if not request.session.get('admin_id'):
        return redirect('admin_login')

    feedback = get_object_or_404(Feedback, id=id)
    feedback.delete()

    return redirect('admin_view_feedback')