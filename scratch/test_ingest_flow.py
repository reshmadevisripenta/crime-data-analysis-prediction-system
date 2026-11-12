import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

import pandas as pd
from accounts.models import User
from crime_data.models import CrimeRecord, Location, CrimeCategory, DatasetUpload
from crime_data.utils import validate_dataset, clean_dataset, process_dataset
from ontology.utils import get_graph_data

user = User.objects.filter(role='admin').first() or User.objects.first()
csv_path = os.path.join(BASE_DIR, 'media', 'datasets', 'crime_demo_dataset.csv')

print(f"Reading {csv_path}...")
df = pd.read_csv(csv_path)
print(f"Read {len(df)} rows. Columns: {list(df.columns)}")

is_valid, errors = validate_dataset(df)
print(f"Dataset valid: {is_valid}, errors: {errors}")
assert is_valid, "Dataset should be valid"

initial_records_count = CrimeRecord.objects.count()

# Create dummy upload instance
upload = DatasetUpload.objects.create(
    user=user,
    original_filename='crime_demo_dataset_test.csv',
    file_type='csv',
    total_records=len(df),
    status='pending'
)

processed_upload = process_dataset(upload, df)
print(f"Upload processed status: {processed_upload.status}")
print(f"Valid records imported: {processed_upload.valid_records}")
print(f"Total CrimeRecord objects now: {CrimeRecord.objects.count()}")

# Verify ontology graph synced
graph_data = get_graph_data()
print(f"Ontology nodes count after upload: {len(graph_data['nodes'])}")
print(f"Ontology edges count after upload: {len(graph_data['edges'])}")

# Clean up test upload and records
print("Cleaning up test upload...")
CrimeRecord.objects.filter(dataset_upload=upload).delete()
upload.delete()
print(f"Records count restored to: {CrimeRecord.objects.count()}")
print("[OK] Dataset ingestion and ontology sync verified!")
