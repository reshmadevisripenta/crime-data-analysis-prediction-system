import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

import json
from django.test import Client
from accounts.models import User
from crime_data.models import CrimeRecord, Location, CrimeCategory, DatasetUpload
from ontology.utils import get_graph_data, execute_sparql, sync_dataset_to_ontology

print("=== 1. CHECK DATABASE RECORDS ===")
user = User.objects.filter(role='admin').first() or User.objects.first()
total_records = CrimeRecord.objects.count()
total_locations = Location.objects.count()
total_categories = CrimeCategory.objects.count()
print(f"Logged in user: {user.username} ({user.role})")
print(f"Total CrimeRecords: {total_records}")
print(f"Total Locations: {total_locations}")
print(f"Total CrimeCategories: {total_categories}")

client = Client()
client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

print("\n=== 2. TEST LOCATION ANALYSIS ===")
response = client.get('/location/?city=Rajahmundry')
print(f"Location map_view status: {response.status_code}")
assert response.status_code == 200, f"Location map_view returned {response.status_code}"
assert b"Rajahmundry" in response.content, "Rajahmundry should be rendered in location HTML"
assert b"Cases" in response.content
print(f"Location page successfully rendered with Rajahmundry records. HTML size: {len(response.content)} bytes.")

# Unfiltered map page
resp_all = client.get('/location/')
assert resp_all.status_code == 200
assert b"Interactive Spatial Distribution Map" in resp_all.content
print(f"Unfiltered location map page successfully rendered ({len(resp_all.content)} bytes).")

ajax_resp = client.get('/location/api/markers/?severity=critical')
ajax_data = json.loads(ajax_resp.content)
print(f"Location AJAX endpoint (critical severity): count={ajax_data['count']}")

print("\n=== 3. TEST BUILD ONTOLOGY ===")
sync_dataset_to_ontology()
graph_data = get_graph_data()
print(f"Ontology Graph Nodes: {len(graph_data['nodes'])}")
print(f"Ontology Graph Edges: {len(graph_data['edges'])}")
assert len(graph_data['nodes']) > 0, "Graph nodes should not be empty"

onto_resp = client.get('/ontology/')
assert onto_resp.status_code == 200, f"Ontology view returned {onto_resp.status_code}"
assert b"Ontology Hierarchy" in onto_resp.content
assert b"OWL Classes" in onto_resp.content
print(f"Ontology page loaded: {onto_resp.status_code} ({len(onto_resp.content)} bytes)")

# Test SPARQL query execution
test_query = """
SELECT ?incident ?location ?category
WHERE {
    ?incident crm:occursAt ?location .
    ?incident crm:hasCategory ?category .
}
LIMIT 5
"""
sparql_results = execute_sparql(test_query)
print(f"SPARQL execution returned {len(sparql_results)} rows:")
for r in sparql_results[:3]:
    print(f"  {r}")
assert len(sparql_results) > 0, "SPARQL query should return matching triples"

# Test SPARQL POST endpoint
sparql_post_resp = client.post('/ontology/sparql/', {'query': test_query})
sparql_post_data = json.loads(sparql_post_resp.content)
print(f"SPARQL POST endpoint returned: status={sparql_post_data.get('status')}, rows={sparql_post_data.get('row_count')}")
assert sparql_post_data.get('status') == 'success'

print("\n=== 4. TEST ANALYZE PATTERNS ===")
ana_resp = client.get('/analysis/')
assert ana_resp.status_code == 200, f"Analysis view returned {ana_resp.status_code}"
assert b"Exploratory Crime Analytics" in ana_resp.content
assert b"Update Analytical Metrics" in ana_resp.content
assert b"Location-Wise Crime Distribution" in ana_resp.content
print(f"Analysis view loaded successfully ({len(ana_resp.content)} bytes)")

ana_ajax_resp = client.get(f"/analysis/api/data/?category={total_categories}")
ana_ajax_data = json.loads(ana_ajax_resp.content)
print(f"Analysis AJAX API returned: status={ana_ajax_data['status']}, total={ana_ajax_data['total_records']}")
assert ana_ajax_data['status'] == 'success'
assert 'location_counts' in ana_ajax_data
assert 'severity_stats' in ana_ajax_data

pat_resp = client.get('/patterns/')
assert pat_resp.status_code == 200, f"Patterns view returned {pat_resp.status_code}"
assert b"Pattern Recognition" in pat_resp.content
assert b"Statistical Hypotheses" in pat_resp.content
print(f"Patterns view loaded successfully ({len(pat_resp.content)} bytes)")

print("\n[OK] ALL MODULE INTEGRATION AND DATA TESTS PASSED SUCCESSFULLY!")
