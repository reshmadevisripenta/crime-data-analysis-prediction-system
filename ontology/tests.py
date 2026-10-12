from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from ontology.models import OntologyClass, OntologyProperty, OntologyFact, SPARQLQuery, SPARQLResult


class TestOntologyModels(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ontoanalyst',
            email='onto@example.com',
            password='Password123!',
            role='analyst'
        )

    def test_ontology_class_creation_and_str(self):
        parent = OntologyClass.objects.create(
            name='Crime',
            label='Crime Incident',
            description='Root class for crime types'
        )
        child = OntologyClass.objects.create(
            name='ViolentCrime',
            label='Violent Crime',
            parent_class=parent
        )
        self.assertEqual(str(parent), 'Crime Incident (Crime)')
        self.assertEqual(str(child), 'Violent Crime (ViolentCrime)')
        self.assertEqual(child.parent_class, parent)

    def test_ontology_property_creation_and_str(self):
        domain = OntologyClass.objects.create(name='CrimeEvent', label='Crime Event')
        range_cls = OntologyClass.objects.create(name='LocationEntity', label='Location Entity')
        prop = OntologyProperty.objects.create(
            name='occursAt',
            label='Occurs At',
            domain_class=domain,
            range_class=range_cls,
            property_type='object'
        )
        self.assertEqual(str(prop), 'Occurs At [Object Property]')
        self.assertEqual(prop.domain_class, domain)
        self.assertEqual(prop.range_class, range_cls)

    def test_ontology_fact_creation_and_str(self):
        c1 = OntologyClass.objects.create(name='AssaultCase', label='Assault Case')
        c2 = OntologyClass.objects.create(name='CityZone', label='City Zone')
        prop = OntologyProperty.objects.create(
            name='locatedIn',
            label='Located In',
            domain_class=c1,
            range_class=c2
        )
        fact = OntologyFact.objects.create(
            subject_class=c1,
            property=prop,
            object_class=c2
        )
        self.assertEqual(str(fact), 'AssaultCase -> locatedIn -> CityZone')

    def test_sparql_query_and_result(self):
        query = SPARQLQuery.objects.create(
            name='FindAllCrimes',
            description='Select all crime instances',
            query_text='SELECT ?s ?p ?o WHERE { ?s ?p ?o }',
            created_by=self.user,
            is_public=True
        )
        self.assertEqual(str(query), 'FindAllCrimes')

        result = SPARQLResult.objects.create(
            query=query,
            result_data={'results': {'bindings': []}},
            execution_time=0.045,
            row_count=10,
            executed_by=self.user
        )
        self.assertIn('FindAllCrimes', str(result))
        self.assertEqual(result.row_count, 10)


class TestOntologyView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='vieweronto',
            email='vieweronto@example.com',
            password='Password123!',
            role='viewer'
        )

    def test_page_loads_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('ontology:explorer'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('classes', response.context)
        self.assertIn('properties', response.context)
        self.assertIn('facts', response.context)
        self.assertIn('saved_queries', response.context)
