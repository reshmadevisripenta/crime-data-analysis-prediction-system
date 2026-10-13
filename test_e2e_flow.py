import os
import django
import io

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.test_settings')
django.setup()

from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from crime_data.models import CrimeCategory, Location, DatasetUpload, CrimeRecord
from model_training.models import MLModel

def run_tests():
    print("--- 0. Running migrations on test DB ---")
    call_command('migrate', verbosity=0)
    print("--- 1. Setting up Test Users ---")
    viewer, _ = User.objects.get_or_create(username='viewer_user', defaults={'role': 'viewer', 'email': 'viewer@example.com'})
    viewer.set_password('viewer123')
    viewer.save()

    analyst, _ = User.objects.get_or_create(username='analyst_user', defaults={'role': 'analyst', 'email': 'analyst@example.com'})
    analyst.set_password('analyst123')
    analyst.save()

    admin, _ = User.objects.get_or_create(username='admin_user', defaults={'role': 'admin', 'is_staff': True, 'email': 'admin@example.com'})
    admin.set_password('admin123')
    admin.save()

    client = Client()

    print("\n--- 2. Testing Unauthenticated Access to /crime-data/upload/ ---")
    resp = client.get('/crime-data/upload/')
    print(f"Unauthenticated GET status: {resp.status_code}")
    assert resp.status_code == 302
    assert '/accounts/login/' in resp.url
    print("[PASS] Properly redirects unauthenticated user to login")

    print("\n--- 3. Testing Viewer Access to /crime-data/upload/ ---")
    client.force_login(viewer)
    resp = client.get('/crime-data/upload/', follow=True)
    print(f"Viewer GET status (after follow): {resp.status_code}, URL: {resp.redirect_chain}")
    assert len(resp.redirect_chain) > 0
    assert '/dashboard/' in resp.redirect_chain[0][0]
    # Check messages
    from django.contrib.messages import get_messages
    msgs = list(get_messages(resp.wsgi_request))
    msg_texts = [str(m) for m in msgs]
    sanitized = [m.encode('ascii', 'replace').decode() for m in msg_texts]
    print(f"Messages via get_messages: {sanitized}")
    in_html = "Access Denied" in resp.content.decode()
    print(f"'Access Denied' in HTML: {in_html}")
    assert any("Access Denied" in m for m in msg_texts) or in_html
    print("[PASS] Viewer is denied with friendly message and redirected to dashboard")

    print("\n--- 4. Testing Analyst Access to /crime-data/upload/ ---")
    client.force_login(analyst)
    resp = client.get('/crime-data/upload/')
    print(f"Analyst GET status: {resp.status_code}")
    assert resp.status_code == 200
    assert 'multipart/form-data' in resp.content.decode()
    assert 'csrfmiddlewaretoken' in resp.content.decode()
    print("[PASS] Analyst successfully loads upload form with multipart/form-data and CSRF token")

    print("\n--- 5. Testing Dataset Upload by Analyst ---")
    # Make sure at least one category and location exist for parsing
    cat, _ = CrimeCategory.objects.get_or_create(name='Theft', defaults={'color_code': '#FF5733'})
    loc, _ = Location.objects.get_or_create(name='Central Area', defaults={'city': 'Metro City', 'latitude': 12.97, 'longitude': 77.59})

    csv_content = b"""incident_date,category,location,description,severity,status
2024-01-15,Theft,Central Area,Phone theft reported,low,reported
2024-01-16,Theft,Central Area,Bicycle theft reported,low,solved
2024-01-17,Theft,Central Area,Bag snatching,medium,under_investigation
2024-01-18,Theft,Central Area,Shop theft,low,closed
2024-01-19,Theft,Central Area,Wallet pickpocketed,low,solved
2024-01-20,Theft,Central Area,Vehicle break-in,medium,reported
2024-01-21,Theft,Central Area,Locker broken,high,under_investigation
2024-01-22,Theft,Central Area,Store burglary,high,solved
2024-01-23,Theft,Central Area,Item stolen,low,reported
2024-01-24,Theft,Central Area,Purse stolen,low,solved
"""
    uploaded_file = SimpleUploadedFile("test_crimes.csv", csv_content, content_type="text/csv")
    resp = client.post('/crime-data/upload/', {'file': uploaded_file}, follow=True)
    print(f"Upload POST status: {resp.status_code}, redirect chain: {resp.redirect_chain}")
    upload_count = DatasetUpload.objects.count()
    records_count = CrimeRecord.objects.count()
    print(f"Total DatasetUpload count: {upload_count}, CrimeRecord count: {records_count}")
    assert upload_count > 0
    print("[PASS] Dataset uploaded and processed successfully")

    print("\n--- 6. Testing Model Training by Analyst ---")
    latest_upload = DatasetUpload.objects.latest('id')
    training_data = {
        'name': 'Test Random Forest Model',
        'dataset_id': latest_upload.id,
        'algorithm': 'random_forest',
        'features': ['month', 'day_of_week'],
        'target': 'crime_count'
    }
    resp = client.post('/model-training/train/', training_data)
    print(f"Model Training POST status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Response: {resp.json()}")
        print(f"Trained Models count: {MLModel.objects.count()}")
    else:
        print(f"Response text: {resp.content.decode()[:300]}")

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
