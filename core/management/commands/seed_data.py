import random
from datetime import datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from crime_data.models import CrimeCategory, Location, CrimeRecord
from ontology.models import OntologyClass, OntologyProperty, OntologyFact
from notifications.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds initial demonstration data for the Crime Data Analysis Prediction System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting seed data generation..."))

        # 1. Create Users
        admin_user, created_admin = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@crimedb.org',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created_admin:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user (admin / admin123)"))
        else:
            self.stdout.write("Admin user already exists.")

        analyst_user, created_analyst = User.objects.get_or_create(
            username='analyst',
            defaults={
                'email': 'analyst@crimedb.org',
                'first_name': 'Senior',
                'last_name': 'Crime Analyst',
                'role': 'analyst',
                'is_staff': False,
                'is_superuser': False,
            }
        )
        if created_analyst:
            analyst_user.set_password('analyst123')
            analyst_user.save()
            self.stdout.write(self.style.SUCCESS("Created analyst user (analyst / analyst123)"))
        else:
            self.stdout.write("Analyst user already exists.")

        # 2. Create 5 Crime Categories
        categories_data = [
            {'name': 'Theft', 'color_code': '#FF6384', 'icon': 'bi-bag-x', 'description': 'Unlawful taking of property without force'},
            {'name': 'Assault', 'color_code': '#36A2EB', 'icon': 'bi-person-x', 'description': 'Intentional infliction of physical injury'},
            {'name': 'Burglary', 'color_code': '#FFCE56', 'icon': 'bi-house-slash', 'description': 'Unlawful entry into a building or structure'},
            {'name': 'Vandalism', 'color_code': '#4BC0C0', 'icon': 'bi-brush', 'description': 'Malicious destruction or defacement of property'},
            {'name': 'Fraud', 'color_code': '#9966FF', 'icon': 'bi-credit-card', 'description': 'Deceptive schemes, cyber fraud, and financial crimes'},
        ]

        created_categories = []
        for cat_data in categories_data:
            cat_obj, _ = CrimeCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'color_code': cat_data['color_code'],
                    'icon': cat_data['icon'],
                    'description': cat_data['description'],
                }
            )
            created_categories.append(cat_obj)
        self.stdout.write(self.style.SUCCESS(f"Initialized {len(created_categories)} crime categories."))

        # 3. Create 10 Indian Locations with realistic coordinates
        locations_data = [
            {'name': 'Connaught Place', 'city': 'New Delhi', 'state': 'Delhi', 'lat': 28.6315, 'lng': 77.2167, 'region': 'urban', 'pop': 150000},
            {'name': 'Bandra West', 'city': 'Mumbai', 'state': 'Maharashtra', 'lat': 19.0596, 'lng': 72.8295, 'region': 'urban', 'pop': 250000},
            {'name': 'Indiranagar', 'city': 'Bengaluru', 'state': 'Karnataka', 'lat': 12.9784, 'lng': 77.6408, 'region': 'urban', 'pop': 180000},
            {'name': 'T. Nagar', 'city': 'Chennai', 'state': 'Tamil Nadu', 'lat': 13.0418, 'lng': 80.2341, 'region': 'urban', 'pop': 200000},
            {'name': 'Park Street', 'city': 'Kolkata', 'state': 'West Bengal', 'lat': 22.5513, 'lng': 88.3524, 'region': 'urban', 'pop': 160000},
            {'name': 'Banjara Hills', 'city': 'Hyderabad', 'state': 'Telangana', 'lat': 17.4156, 'lng': 78.4350, 'region': 'urban', 'pop': 140000},
            {'name': 'Shivajinagar', 'city': 'Pune', 'state': 'Maharashtra', 'lat': 18.5314, 'lng': 73.8446, 'region': 'urban', 'pop': 175000},
            {'name': 'Navrangpura', 'city': 'Ahmedabad', 'state': 'Gujarat', 'lat': 23.0373, 'lng': 72.5613, 'region': 'urban', 'pop': 130000},
            {'name': 'Hazratganj', 'city': 'Lucknow', 'state': 'Uttar Pradesh', 'lat': 26.8467, 'lng': 80.9462, 'region': 'urban', 'pop': 120000},
            {'name': 'Sector 17', 'city': 'Chandigarh', 'state': 'Chandigarh', 'lat': 30.7398, 'lng': 76.7827, 'region': 'urban', 'pop': 95000},
        ]

        created_locations = []
        for loc_data in locations_data:
            loc_obj, _ = Location.objects.get_or_create(
                name=loc_data['name'],
                city=loc_data['city'],
                defaults={
                    'state': loc_data['state'],
                    'latitude': loc_data['lat'],
                    'longitude': loc_data['lng'],
                    'region_type': loc_data['region'],
                    'population': loc_data['pop'],
                }
            )
            created_locations.append(loc_obj)
        self.stdout.write(self.style.SUCCESS(f"Initialized {len(created_locations)} locations across India."))

        # 4. Create 200 Crime Records across the last 2 years
        if CrimeRecord.objects.count() < 200:
            severities = ['low', 'medium', 'high', 'critical']
            statuses = ['reported', 'under_investigation', 'solved', 'closed']
            today = timezone.now().date()
            start_date = today - timedelta(days=730)

            sample_descriptions = {
                'Theft': ['Stolen smartphone at public market', 'Pickpocketing during transit rush', 'Stolen bicycle outside retail complex', 'Luggage grabbed from depot'],
                'Assault': ['Physical confrontation following traffic dispute', 'Late night brawl outside recreational venue', 'Verbal altercation escalating to physical strike', 'Assault on store attendant'],
                'Burglary': ['Residential break-in during holiday absence', 'Commercial lock breached after closing hours', 'Apartment rear window forced open', 'Warehouse storage unit entered without authorization'],
                'Vandalism': ['Graffiti tags sprayed on municipal walls', 'Damaged street surveillance camera', 'Broken glass fixtures at public depot', 'Defaced government sign board'],
                'Fraud': ['Phishing scam targeting banking credentials', 'Unauthorized online financial transfer', 'Fake employment investment scheme', 'Credit card skimming incident'],
            }

            records = []
            for _ in range(200):
                cat = random.choice(created_categories)
                loc = random.choice(created_locations)
                random_days = random.randint(0, 729)
                inc_date = start_date + timedelta(days=random_days)
                inc_time = time(hour=random.randint(0, 23), minute=random.randint(0, 59))

                desc_choices = sample_descriptions.get(cat.name, ['Crime incident reported'])
                desc = f"{random.choice(desc_choices)} in {loc.name} area."

                records.append(CrimeRecord(
                    category=cat,
                    location=loc,
                    incident_date=inc_date,
                    incident_time=inc_time,
                    description=desc,
                    severity=random.choices(severities, weights=[0.3, 0.4, 0.2, 0.1])[0],
                    status=random.choices(statuses, weights=[0.25, 0.35, 0.25, 0.15])[0],
                    source='Police Precinct Log'
                ))

            CrimeRecord.objects.bulk_create(records)
            self.stdout.write(self.style.SUCCESS("Created 200 realistic CrimeRecord instances spanning the last 2 years."))
        else:
            self.stdout.write("Sufficient CrimeRecord records already exist in database.")

        # 5. Create Ontology Classes, Properties, and Facts
        root_crime, _ = OntologyClass.objects.get_or_create(
            name='Crime',
            defaults={'label': 'Crime (Root Class)', 'color_code': '#071B3A', 'description': 'Top level crime classification'}
        )
        violent_cls, _ = OntologyClass.objects.get_or_create(
            name='ViolentCrime',
            defaults={'label': 'Violent Crime', 'parent_class': root_crime, 'color_code': '#FF4560', 'description': 'Offenses involving physical bodily harm'}
        )
        property_cls, _ = OntologyClass.objects.get_or_create(
            name='PropertyCrime',
            defaults={'label': 'Property Crime', 'parent_class': root_crime, 'color_code': '#FEB019', 'description': 'Offenses involving property theft or destruction'}
        )
        financial_cls, _ = OntologyClass.objects.get_or_create(
            name='FinancialCrime',
            defaults={'label': 'Financial Crime', 'parent_class': root_crime, 'color_code': '#775DD0', 'description': 'Fraudulent and economic offenses'}
        )
        location_cls, _ = OntologyClass.objects.get_or_create(
            name='Location',
            defaults={'label': 'Geographic Location', 'color_code': '#00E396', 'description': 'Jurisdictional spatial points'}
        )
        suspect_cls, _ = OntologyClass.objects.get_or_create(
            name='Suspect',
            defaults={'label': 'Suspect Person', 'color_code': '#20D5F5', 'description': 'Persons of investigative interest'}
        )

        occurs_prop, _ = OntologyProperty.objects.get_or_create(
            name='occursAt',
            defaults={'label': 'Occurs At Location', 'domain_class': root_crime, 'range_class': location_cls, 'property_type': 'object'}
        )
        has_suspect_prop, _ = OntologyProperty.objects.get_or_create(
            name='hasSuspect',
            defaults={'label': 'Has Suspect', 'domain_class': root_crime, 'range_class': suspect_cls, 'property_type': 'object'}
        )

        # Facts
        OntologyFact.objects.get_or_create(
            subject_class=violent_cls,
            property=occurs_prop,
            object_class=location_cls
        )
        OntologyFact.objects.get_or_create(
            subject_class=property_cls,
            property=occurs_prop,
            object_class=location_cls
        )
        OntologyFact.objects.get_or_create(
            subject_class=financial_cls,
            property=has_suspect_prop,
            object_class=suspect_cls
        )
        self.stdout.write(self.style.SUCCESS("Initialized ontology knowledge graph classes, properties, and facts."))

        # 6. Create Initial Notifications
        Notification.objects.get_or_create(
            user=admin_user,
            title="System Ready",
            defaults={
                'message': "Welcome to the Crime Data Analysis & Prediction System. The initial seed datasets and ontology graphs are loaded.",
                'notification_type': 'success',
                'category': 'system',
                'action_url': '/dashboard/'
            }
        )
        Notification.objects.get_or_create(
            user=analyst_user,
            title="Analytics Workspace Initialized",
            defaults={
                'message': "Crime data records and predictive model pipelines are available for analysis and training.",
                'notification_type': 'info',
                'category': 'analysis',
                'action_url': '/analysis/'
            }
        )
        self.stdout.write(self.style.SUCCESS("Created initial administrative and analyst notifications."))

        self.stdout.write(self.style.SUCCESS("Successfully completed seed_data command! All demo data populated."))
