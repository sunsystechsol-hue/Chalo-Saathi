from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.index, name="index"),

    # Auth
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Profile
    path("profile/", views.profile, name="profile"),

    # Ride actions
    path("ride/<int:ride_id>/cancel/", views.cancel_ride, name="cancel_ride"),
    path("ride/<int:ride_id>/resume/", views.resume_ride, name="resume_ride"),
    path("ride/<int:ride_id>/delete/", views.delete_ride, name="delete_ride"),

    # Pages
    path("aboutus/", views.aboutus, name="aboutus"),
    path("forgot_password/", views.forgot_password, name="forgot_password"),

    # Feedback
    path("feedback/", views.feedback_view, name="feedback"),
    path("feedback-data/", views.feedback_data, name="feedback_data"),

    # Email
    path("send-email/", views.send_email_view, name="send_email"),

    # Maps & Distance
    path("maptest/", views.maptest, name="maptest"),
    path("distance/", views.distance_view, name="distance"),

    # Ride flow
    path("offer-ride/", views.offer_ride, name="offer_ride"),
    path("find-ride/", views.find_ride, name="find_ride"),
    path("ride-results/", views.ride_results, name="ride_results"),

    # Booking
    path("book-ride/<int:ride_id>/", views.book_ride, name="book_ride"),
    path("booking-confirmation/<int:booking_id>/", views.booking_confirmation, name="booking_confirmation"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path("ride/<int:ride_id>/bookings/", views.ride_bookings, name="ride_bookings"),
    path("booking/confirm/<int:booking_id>/", views.confirm_booking, name="confirm_booking"),
    path("booking/cancel/<int:booking_id>/", views.cancel_booking_driver, name="cancel_booking_driver"),
    path("choose-subscription/<int:booking_id>/", views.choose_subscription, name="choose_subscription"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
