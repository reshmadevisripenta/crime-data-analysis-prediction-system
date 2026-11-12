import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.test_settings')
import django
django.setup()

from django.core.management import call_command

print("Running test suite...")
try:
    call_command('test', '--settings=config.test_settings', '--verbosity=1')
    print("\n[OK] All Django tests passed!")
except Exception as e:
    print(f"\n[ERROR] Tests encountered an exception: {e}")
