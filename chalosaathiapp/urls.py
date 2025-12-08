

from django.urls import path
from chalosaathiapp import admin
from . import views
from .views import feedback_view
from django.conf import settings
from django.conf.urls.static import static
from .views import send_email_view

urlpatterns = [
    path("index/", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("ride/<int:ride_id>/cancel/", views.cancel_ride, name="cancel_ride"),
    path("ride/<int:ride_id>/resume/", views.resume_ride, name="resume_ride"),
    path("ride/<int:ride_id>/delete/", views.delete_ride, name="delete_ride"),        
    path("signup/", views.signup, name="signup"), 
    path("login/", views.login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("aboutus/", views.aboutus, name="aboutus"),
    path('feedback/', views.feedback_view, name='feedback'),
    # path('feedback-data/', views.feedback_data, name='feedback-data'),
    path("forgot_password/", views.forgot_password, name="forgot_password"),  
    path("feedback-data/", views.feedback_data, name="feedback_data"),
    path('send-email/', send_email_view, name='send_email'),
    path('maptest/', views.maptest, name='maptest'),
    path("distance/", views.distance_view, name="distance"),
    path('offer-ride/', views.offer_ride, name='offer_ride'),
    path('find-ride/', views.find_ride, name='find_ride'),
    path('ride-results/', views.ride_results, name='ride_results'),
    path('book-ride/<int:ride_id>/', views.book_ride, name='book_ride'),
    path('booking-confirmation/<int:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('ride/<int:ride_id>/bookings/', views.ride_bookings, name='ride_bookings'),
    path('booking/confirm/<int:booking_id>/', views.confirm_booking, name='confirm_booking'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking_driver, name='cancel_booking_driver'),
    path('choose-subscription/<int:booking_id>/', views.choose_subscription, name='choose_subscription'),
    
    
    
    
]
    

   



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)