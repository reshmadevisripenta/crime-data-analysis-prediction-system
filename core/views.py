import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from crime_data.models import CrimeRecord, CrimeCategory, Location
from prediction.models import PredictionResult
from .forms import ContactForm

logger = logging.getLogger(__name__)


def home_view(request):
    """
    Public landing page presenting platform statistics, features overview,
    and calls-to-action.
    """
    total_records = CrimeRecord.objects.count()
    total_categories = CrimeCategory.objects.count()
    total_locations = Location.objects.count()
    total_predictions = PredictionResult.objects.count()

    context = {
        'total_records': total_records,
        'total_categories': total_categories,
        'total_locations': total_locations,
        'total_predictions': total_predictions,
    }
    return render(request, 'core/home.html', context)


def about_view(request):
    """
    Information page describing system architecture, ontology graph,
    and machine learning forecasting methodology.
    """
    return render(request, 'core/about.html')


def contact_view(request):
    """
    Public contact form page. Validates input and saves ContactMessage instance.
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save()
            logger.info(f"Received contact message from {contact_msg.email}: {contact_msg.subject}")
            messages.success(request, "Thank you! Your message has been received. Our team will get back to you shortly.")
            return redirect('core:contact')
        else:
            messages.error(request, "Please verify all fields in the contact form.")
    else:
        form = ContactForm()

    return render(request, 'core/contact.html', {'form': form})
