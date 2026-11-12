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


def sync_dataset_to_ontology(crime_records=None, limit_records=100):
    """
    Synchronizes actual uploaded crime dataset entities and records with the ontology:
    - Root classes: CrimeIncident, Location, CrimeCategory, Severity, IncidentDate
    - Object/Data properties: occursAt, hasCategory, hasSeverity, incidentOnDate
    - Subclasses for all actual CrimeCategories and Locations
    - Subclasses for Severity levels
    - Incident entities and facts connecting each incident to its Location, Category, Severity, Date
    Prevents duplicate entities and facts via get_or_create.
    """
    from crime_data.models import CrimeRecord, CrimeCategory, Location

    # 1. Base Core Ontology Classes
    root_classes = [
        ('CrimeIncident', 'Crime Incident', 'Root entity representing a reported criminal occurrence', '#1769FF'),
        ('Location', 'Location Entity', 'Spatial coordinates and jurisdictional regions', '#10B981'),
        ('CrimeCategory', 'Crime Category', 'Taxonomy classification of criminal offenses', '#F59E0B'),
        ('Severity', 'Severity Level', 'Degree of harm or criticality of an incident', '#EF4444'),
        ('IncidentDate', 'Incident Date', 'Temporal occurrence date of an incident', '#8B5CF6'),
    ]

    class_objs = {}
    for name, label, desc, color in root_classes:
        obj, _ = OntologyClass.objects.get_or_create(
            name=name,
            defaults={'label': label, 'description': desc, 'color_code': color}
        )
        class_objs[name] = obj

    # 2. Base Core Properties
    prop_defs = [
        ('occursAt', 'occursAt', 'Relates crime incident to its physical location', class_objs['CrimeIncident'], class_objs['Location'], 'object'),
        ('hasCategory', 'hasCategory', 'Classifies crime incident under a category', class_objs['CrimeIncident'], class_objs['CrimeCategory'], 'object'),
        ('hasSeverity', 'hasSeverity', 'Specifies severity tier of crime incident', class_objs['CrimeIncident'], class_objs['Severity'], 'data'),
        ('incidentOnDate', 'incidentOnDate', 'Associates incident with calendar date', class_objs['CrimeIncident'], class_objs['IncidentDate'], 'data'),
    ]

    prop_objs = {}
    for name, label, desc, domain, range_cls, p_type in prop_defs:
        obj, _ = OntologyProperty.objects.get_or_create(
            name=name,
            defaults={
                'label': label,
                'description': desc,
                'domain_class': domain,
                'range_class': range_cls,
                'property_type': p_type
            }
        )
        prop_objs[name] = obj

    # 3. Subclasses for actual Crime Categories
    for cat in CrimeCategory.objects.all():
        safe_name = f"Category_{re.sub(r'[^a-zA-Z0-9_]', '', cat.name.replace(' ', '_'))}"
        c_obj, _ = OntologyClass.objects.get_or_create(
            name=safe_name,
            defaults={
                'label': cat.name,
                'description': cat.description or f"Category: {cat.name}",
                'parent_class': class_objs['CrimeCategory'],
                'color_code': cat.color_code or '#F59E0B'
            }
        )
        class_objs[f"cat_{cat.id}"] = c_obj

    # 4. Subclasses for actual Locations
    for loc in Location.objects.all():
        safe_name = f"Location_{loc.id}_{re.sub(r'[^a-zA-Z0-9_]', '', loc.name.replace(' ', '_'))}"
        l_obj, _ = OntologyClass.objects.get_or_create(
            name=safe_name,
            defaults={
                'label': f"{loc.name} ({loc.city})",
                'description': f"Jurisdiction: {loc.name}, City: {loc.city}, Region: {loc.region_type}",
                'parent_class': class_objs['Location'],
                'color_code': '#10B981'
            }
        )
        class_objs[f"loc_{loc.id}"] = l_obj

    # 5. Subclasses for Severity levels
    for sev in ['low', 'medium', 'high', 'critical']:
        s_name = f"Severity_{sev.capitalize()}"
        s_obj, _ = OntologyClass.objects.get_or_create(
            name=s_name,
            defaults={
                'label': sev.capitalize(),
                'description': f"{sev.capitalize()} severity tier",
                'parent_class': class_objs['Severity'],
                'color_code': '#EF4444' if sev == 'critical' else ('#F59E0B' if sev == 'high' else '#16A36A')
            }
        )
        class_objs[f"sev_{sev}"] = s_obj

    # 6. Populate Crime Records into Ontology
    if crime_records is None:
        qs = CrimeRecord.objects.select_related('category', 'location').order_by('-id')
    else:
        qs = crime_records

    records_to_sync = qs[:limit_records] if limit_records else qs

    for rec in records_to_sync:
        if not rec.category or not rec.location:
            continue

        inc_name = f"Incident_{rec.id}"
        inc_label = f"Case #{rec.id} ({rec.category.name})"
        inc_cls, _ = OntologyClass.objects.get_or_create(
            name=inc_name,
            defaults={
                'label': inc_label,
                'description': f"Incident on {rec.incident_date} at {rec.location.name}: {rec.description[:100]}",
                'parent_class': class_objs['CrimeIncident'],
                'color_code': rec.category.color_code or '#1769FF'
            }
        )

        # Fact: Incident -> occursAt -> Location
        loc_cls = class_objs.get(f"loc_{rec.location_id}")
        if loc_cls:
            OntologyFact.objects.get_or_create(
                subject_class=inc_cls,
                property=prop_objs['occursAt'],
                object_class=loc_cls,
                source_record_id=rec.id,
                defaults={'literal_value': f"{rec.location.name}, {rec.location.city}"}
            )

        # Fact: Incident -> hasCategory -> Category
        cat_cls = class_objs.get(f"cat_{rec.category_id}")
        if cat_cls:
            OntologyFact.objects.get_or_create(
                subject_class=inc_cls,
                property=prop_objs['hasCategory'],
                object_class=cat_cls,
                source_record_id=rec.id,
                defaults={'literal_value': rec.category.name}
            )

        # Fact: Incident -> hasSeverity -> Severity
        sev_cls = class_objs.get(f"sev_{rec.severity.lower()}")
        if sev_cls:
            OntologyFact.objects.get_or_create(
                subject_class=inc_cls,
                property=prop_objs['hasSeverity'],
                object_class=sev_cls,
                source_record_id=rec.id,
                defaults={'literal_value': rec.severity}
            )

        # Fact: Incident -> incidentOnDate -> Date
        if rec.incident_date:
            date_str = str(rec.incident_date)
            date_safe_name = f"Date_{date_str.replace('-', '_')}"
            date_cls, _ = OntologyClass.objects.get_or_create(
                name=date_safe_name,
                defaults={
                    'label': date_str,
                    'description': f"Calendar date {date_str}",
                    'parent_class': class_objs['IncidentDate'],
                    'color_code': '#8B5CF6'
                }
            )
            OntologyFact.objects.get_or_create(
                subject_class=inc_cls,
                property=prop_objs['incidentOnDate'],
                object_class=date_cls,
                source_record_id=rec.id,
                defaults={'literal_value': date_str}
            )

    # Sync RDFLib OWL file as well
    export_ontology_to_owl_file()
    logger.info("Successfully synchronized dataset records into ontology.")


def export_ontology_to_owl_file():
    """Serializes the current database ontology classes, properties, and facts to crime_ontology.owl."""
    g = Graph()
    CRM = Namespace(CRIME_NAMESPACE)
    CRIME = Namespace('http://crimedb.org/ontology#')
    g.bind('crm', CRM)
    g.bind('crime', CRIME)
    g.bind('owl', OWL)
    g.bind('rdfs', RDFS)

    classes = OntologyClass.objects.all()
    for cls in classes:
        uri = CRM[cls.name]
        g.add((uri, RDF.type, OWL.Class))
        g.add((uri, RDFS.label, Literal(cls.label or cls.name)))
        if cls.description:
            g.add((uri, RDFS.comment, Literal(cls.description)))
        if cls.parent_class:
            g.add((uri, RDFS.subClassOf, CRM[cls.parent_class.name]))
        # Also bind under CRIME namespace for compatibility
        crime_uri = CRIME[cls.name]
        g.add((crime_uri, RDF.type, OWL.Class))
        if cls.parent_class:
            g.add((crime_uri, RDFS.subClassOf, CRIME[cls.parent_class.name]))

    properties = OntologyProperty.objects.select_related('domain_class', 'range_class').all()
    for prop in properties:
        uri = CRM[prop.name]
        prop_type = OWL.ObjectProperty if prop.property_type == 'object' else OWL.DatatypeProperty
        g.add((uri, RDF.type, prop_type))
        g.add((uri, RDFS.label, Literal(prop.label or prop.name)))
        if prop.domain_class:
            g.add((uri, RDFS.domain, CRM[prop.domain_class.name]))
            g.add((CRIME[prop.name], RDFS.domain, CRIME[prop.domain_class.name]))
        if prop.range_class:
            g.add((uri, RDFS.range, CRM[prop.range_class.name]))
            g.add((CRIME[prop.name], RDFS.range, CRIME[prop.range_class.name]))

    facts = OntologyFact.objects.select_related('subject_class', 'property', 'object_class').all()[:200]
    for fact in facts:
        sub_uri = CRM[fact.subject_class.name]
        prop_uri = CRM[fact.property.name]
        if fact.object_class:
            g.add((sub_uri, prop_uri, CRM[fact.object_class.name]))
            g.add((CRIME[fact.subject_class.name], CRIME[fact.property.name], CRIME[fact.object_class.name]))
        elif fact.literal_value:
            g.add((sub_uri, prop_uri, Literal(fact.literal_value)))
            g.add((CRIME[fact.subject_class.name], CRIME[fact.property.name], Literal(fact.literal_value)))

    try:
        os.makedirs(os.path.dirname(ONTOLOGY_FILE_PATH), exist_ok=True)
        g.serialize(destination=ONTOLOGY_FILE_PATH, format='xml')
        logger.info(f"Updated crime_ontology.owl at {ONTOLOGY_FILE_PATH}")
    except Exception as e:
        logger.warning(f"Could not serialize OWL file: {e}")

    return g


def create_initial_ontology_file():
    """Generates a default OWL ontology file if one does not exist."""
    return export_ontology_to_owl_file()


def load_ontology():
    """
    Loads crime_ontology.owl into an RDFLib Graph.
    Generates/syncs it if it doesn't exist.
    """
    g = Graph()
    if not os.path.exists(ONTOLOGY_FILE_PATH):
        return export_ontology_to_owl_file()
    try:
        g.parse(ONTOLOGY_FILE_PATH, format='xml')
    except Exception as e:
        logger.warning(f"Failed parsing OWL as xml: {e}, recreating from DB.")
        return export_ontology_to_owl_file()
    return g


def validate_sparql_query(query):
    """
    Sanitizes and validates SPARQL query to prevent malicious operations.
    Returns (is_valid: bool, error: str).
    """
    if not query or not query.strip():
        return False, "Query cannot be empty."

    forbidden_keywords = [r'\bDROP\b', r'\bDELETE\b', r'\bCLEAR\b', r'\bINSERT\b', r'\bLOAD\b', r'\bCREATE\b']
    for kw in forbidden_keywords:
        if re.search(kw, query, re.IGNORECASE):
            return False, f"Unauthorized SPARQL operation detected: query contains {kw.replace(r'\\b', '')}."

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
    prefixes = (
        f"PREFIX crm: <{CRIME_NAMESPACE}>\n"
        f"PREFIX crime: <http://crimedb.org/ontology#>\n"
        f"PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        f"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        f"PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
    )
    full_query = prefixes + query_string

    results = []
    try:
        qres = g.query(full_query)
        for row in qres:
            row_dict = {}
            if hasattr(row, 'asdict'):
                for k, v in row.asdict().items():
                    val = str(v)
                    # Clean URI prefixes for clean display in table
                    val = val.replace(CRIME_NAMESPACE, 'crm:').replace('http://crimedb.org/ontology#', 'crime:')
                    row_dict[str(k)] = val
            else:
                for idx, v in enumerate(row):
                    val = str(v).replace(CRIME_NAMESPACE, 'crm:').replace('http://crimedb.org/ontology#', 'crime:')
                    row_dict[f"col_{idx}"] = val
            results.append(row_dict)
    except Exception as e:
        logger.error(f"SPARQL execution error: {e}")
        raise e

    return results


def get_graph_data(max_incidents=35):
    """
    Generates nodes and edges JSON structure for D3.js force-directed graph.
    Sources nodes from OntologyClass and edges from OntologyProperty & OntologyFact.
    Limits individual incident nodes to max_incidents for optimal browser rendering performance.
    """
    # Ensure base classes and dataset sync exist
    if not OntologyClass.objects.filter(name='CrimeIncident').exists():
        sync_dataset_to_ontology()

    nodes = []
    edges = []
    node_id_set = set()

    # Core classes and category/location/severity classes
    core_classes = OntologyClass.objects.exclude(name__startswith='Incident_')
    for cls in core_classes:
        is_root = cls.parent_class is None
        radius = 24 if is_root else 16
        group = 1 if is_root else (2 if 'Category' in cls.name else (3 if 'Location' in cls.name else 4))
        
        nodes.append({
            'id': str(cls.name),
            'label': cls.label or cls.name,
            'color': cls.color_code or '#1769FF',
            'type': 'class',
            'group': group,
            'radius': radius,
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

    # Individual incident nodes (up to max_incidents)
    incident_classes = OntologyClass.objects.filter(name__startswith='Incident_')[:max_incidents]
    incident_ids = set()
    for inc in incident_classes:
        incident_ids.add(inc.id)
        nodes.append({
            'id': str(inc.name),
            'label': inc.label or inc.name,
            'color': inc.color_code or '#1769FF',
            'type': 'incident',
            'group': 5,
            'radius': 11,
            'description': inc.description or '',
        })
        node_id_set.add(str(inc.name))

        if inc.parent_class:
            edges.append({
                'source': str(inc.name),
                'target': str(inc.parent_class.name),
                'label': 'instanceOf',
                'type': 'inheritance'
            })

    # Facts between included nodes
    facts = OntologyFact.objects.select_related('subject_class', 'property', 'object_class').all()
    for fact in facts:
        sub_name = str(fact.subject_class.name)
        obj_name = str(fact.object_class.name) if fact.object_class else None

        if sub_name in node_id_set and obj_name and obj_name in node_id_set:
            edges.append({
                'source': sub_name,
                'target': obj_name,
                'label': fact.property.label if fact.property else 'relatesTo',
                'type': 'fact'
            })

    return {
        'nodes': nodes,
        'edges': edges,
        'links': edges  # Alias for D3 simulation
    }
