import os
import re
import logging
from django.conf import settings
import rdflib
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef
from .models import OntologyClass, OntologyProperty, OntologyFact

logger = logging.getLogger(__name__)

CRIME_NAMESPACE = 'http://www.semanticweb.org/crime-ontology#'
ONTOLOGY_FILE_PATH = os.path.join(settings.BASE_DIR, 'ontology', 'crime_ontology.owl')


def create_initial_ontology_file():
    """Generates a default OWL ontology file if one does not exist."""
    g = Graph()
    CRM = Namespace(CRIME_NAMESPACE)
    g.bind('crm', CRM)
    g.bind('owl', OWL)
    g.bind('rdfs', RDFS)

    # Base classes
    classes = [
        ('Crime', 'Root Crime Class'),
        ('ViolentCrime', 'Crimes involving physical violence'),
        ('PropertyCrime', 'Crimes involving destruction or theft of property'),
        ('FinancialCrime', 'Crimes involving financial deception or fraud'),
        ('Location', 'Spatial coordinates and jurisdictional regions'),
        ('Suspect', 'Individuals or entities under investigation'),
        ('Victim', 'Impacted individuals or organizations'),
        ('Weapon', 'Instruments used during crime commission'),
    ]

    for cls_name, comment in classes:
        cls_uri = CRM[cls_name]
        g.add((cls_uri, RDF.type, OWL.Class))
        g.add((cls_uri, RDFS.label, Literal(cls_name)))
        g.add((cls_uri, RDFS.comment, Literal(comment)))

    # Subclass relationships
    g.add((CRM.ViolentCrime, RDFS.subClassOf, CRM.Crime))
    g.add((CRM.PropertyCrime, RDFS.subClassOf, CRM.Crime))
    g.add((CRM.FinancialCrime, RDFS.subClassOf, CRM.Crime))

    # Object properties
    props = [
        ('occursAt', CRM.Crime, CRM.Location, 'Relates crime to its location'),
        ('involvesWeapon', CRM.Crime, CRM.Weapon, 'Relates crime to weapon used'),
        ('hasSuspect', CRM.Crime, CRM.Suspect, 'Relates crime to suspects'),
        ('hasVictim', CRM.Crime, CRM.Victim, 'Relates crime to victims'),
    ]

    for p_name, domain, range_cls, comment in props:
        p_uri = CRM[p_name]
        g.add((p_uri, RDF.type, OWL.ObjectProperty))
        g.add((p_uri, RDFS.domain, domain))
        g.add((p_uri, RDFS.range, range_cls))
        g.add((p_uri, RDFS.comment, Literal(comment)))

    g.serialize(destination=ONTOLOGY_FILE_PATH, format='xml')
    logger.info(f"Created initial crime ontology file at {ONTOLOGY_FILE_PATH}")
    return g


def load_ontology():
    """
    Loads crime_ontology.owl into an RDFLib Graph.
    Creates default file if it doesn't already exist.
    """
    g = Graph()
    if not os.path.exists(ONTOLOGY_FILE_PATH):
        return create_initial_ontology_file()
    try:
        g.parse(ONTOLOGY_FILE_PATH, format='xml')
    except Exception as e:
        logger.warning(f"Failed parsing OWL as xml: {e}, attempting default creation.")
        return create_initial_ontology_file()
    return g


def validate_sparql_query(query):
    """
    Sanitizes and validates SPARQL query to prevent malicious operations.
    Returns (is_valid: bool, error: str).
    """
    if not query or not query.strip():
        return False, "Query cannot be empty."

    # Disallow destructive SPARQL update clauses (DROP, DELETE, CLEAR, INSERT)
    forbidden_keywords = [r'\bDROP\b', r'\bDELETE\b', r'\bCLEAR\b', r'\bINSERT\b', r'\bLOAD\b', r'\bCREATE\b']
    for kw in forbidden_keywords:
        if re.search(kw, query, re.IGNORECASE):
            return False, f"Unauthorized SPARQL operation detected: query contains {kw.replace(r'\b', '')}."

    if not re.search(r'\bSELECT\b|\bASK\b|\bDESCRIBE\b|\bCONSTRUCT\b', query, re.IGNORECASE):
        return False, "Query must be a read query starting with SELECT, ASK, CONSTRUCT, or DESCRIBE."

    return True, ""


def execute_sparql(query_string):
    """
    Executes a validated SPARQL query against the RDFLib ontology graph.
    Returns list of dictionaries representing result rows.
    """
    g = load_ontology()

    # Prepend default prefixes if missing
    prefixes = f"PREFIX crm: <{CRIME_NAMESPACE}>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
    if "crm:" not in query_string and "crime-ontology" not in query_string:
        full_query = prefixes + query_string
    else:
        full_query = prefixes + query_string

    results = []
    try:
        qres = g.query(full_query)
        for row in qres:
            row_dict = {}
            if hasattr(row, 'asdict'):
                for k, v in row.asdict().items():
                    row_dict[str(k)] = str(v)
            else:
                for idx, v in enumerate(row):
                    row_dict[f"col_{idx}"] = str(v)
            results.append(row_dict)
    except Exception as e:
        logger.error(f"SPARQL execution error: {e}")
        raise e

    return results


def get_graph_data():
    """
    Generates nodes and edges JSON structure for D3.js force-directed graph.
    Sources nodes from OntologyClass and edges from OntologyProperty & OntologyFact.
    """
    nodes = []
    edges = []
    node_id_set = set()

    # Classes
    classes = OntologyClass.objects.all()
    for cls in classes:
        nodes.append({
            'id': str(cls.name),
            'label': cls.label or cls.name,
            'color': cls.color_code or '#1769FF',
            'type': 'class',
            'description': cls.description or '',
        })
        node_id_set.add(str(cls.name))

        if cls.parent_class:
            edges.append({
                'source': str(cls.name),
                'target': str(cls.parent_class.name),
                'label': 'subClassOf',
                'type': 'inheritance'
            })

    # Properties
    properties = OntologyProperty.objects.select_related('domain_class', 'range_class').all()
    for prop in properties:
        if prop.range_class and prop.domain_class:
            edges.append({
                'source': str(prop.domain_class.name),
                'target': str(prop.range_class.name),
                'label': prop.label or prop.name,
                'type': prop.property_type
            })

    # Facts
    facts = OntologyFact.objects.select_related('subject_class', 'property', 'object_class').all()
    for fact in facts:
        if fact.object_class:
            edges.append({
                'source': str(fact.subject_class.name),
                'target': str(fact.object_class.name),
                'label': fact.property.label if fact.property else 'relatesTo',
                'type': 'fact'
            })

    # Fallback default nodes if database has no ontology objects yet
    if not nodes:
        default_nodes = [
            {'id': 'Crime', 'label': 'Crime (Root)', 'color': '#071B3A', 'type': 'class'},
            {'id': 'ViolentCrime', 'label': 'Violent Crime', 'color': '#FF4560', 'type': 'class'},
            {'id': 'PropertyCrime', 'label': 'Property Crime', 'color': '#FEB019', 'type': 'class'},
            {'id': 'Location', 'label': 'Location', 'color': '#00E396', 'type': 'class'},
            {'id': 'Suspect', 'label': 'Suspect', 'color': '#775DD0', 'type': 'class'},
            {'id': 'Weapon', 'label': 'Weapon', 'color': '#FF4560', 'type': 'class'},
        ]
        default_edges = [
            {'source': 'ViolentCrime', 'target': 'Crime', 'label': 'subClassOf'},
            {'source': 'PropertyCrime', 'target': 'Crime', 'label': 'subClassOf'},
            {'source': 'Crime', 'target': 'Location', 'label': 'occursAt'},
            {'source': 'ViolentCrime', 'target': 'Weapon', 'label': 'involvesWeapon'},
            {'source': 'Crime', 'target': 'Suspect', 'label': 'hasSuspect'},
        ]
        return {'nodes': default_nodes, 'edges': default_edges}

    return {'nodes': nodes, 'edges': edges}
