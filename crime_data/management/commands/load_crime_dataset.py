import os
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.files import File
from crime_data.models import DatasetUpload
from crime_data.utils import validate_dataset, process_dataset

User = get_user_model()


class Command(BaseCommand):
    help = 'Loads and validates a crime dataset CSV file into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='sample_data/real_crime_dataset_public_records.csv',
            help='Path to the CSV file to ingest'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username attributing the upload'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        username = options['user']

        if not os.path.exists(file_path):
            raise CommandError(f"Dataset file '{file_path}' does not exist.")

        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.filter(role__in=['admin', 'analyst']).first()
        if not user:
            user = User.objects.first()

        self.stdout.write(f"Reading dataset file: {file_path}")

        try:
            # Skip comment lines if any
            df = pd.read_csv(file_path, comment='#')
        except Exception as e:
            raise CommandError(f"Failed to read CSV: {str(e)}")

        self.stdout.write(f"Validating dataset structure ({len(df)} rows found)...")
        is_valid, errors = validate_dataset(df)
        if not is_valid:
            raise CommandError(f"Dataset validation failed: {errors}")

        self.stdout.write(self.style.SUCCESS("Validation passed. Processing records..."))

        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            upload_instance = DatasetUpload.objects.create(
                user=user,
                original_filename=filename,
                file_type='csv',
                file=File(f, name=filename)
            )

        process_dataset(upload_instance, df)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully ingested '{filename}': "
                f"{upload_instance.valid_records} valid records imported, "
                f"{upload_instance.invalid_records} invalid records."
            )
        )
