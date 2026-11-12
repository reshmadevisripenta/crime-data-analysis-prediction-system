import time
import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from accounts.decorators import analyst_required
from .models import OntologyClass, OntologyProperty, OntologyFact, SPARQLQuery, SPARQLResult
from .utils import load_ontology, execute_sparql, get_graph_data, validate_sparql_query

logger = logging.getLogger(__name__)


@login_required
def ontology_explorer_view(request):
    """
    Renders ontology visual explorer page containing D3.js knowledge graph,
    class hierarchy, object properties, and saved SPARQL queries.
    """
    classes = OntologyClass.objects.prefetch_related('subclasses').all()
    properties = OntologyProperty.objects.select_related('domain_class', 'range_class').all()
    facts = OntologyFact.objects.select_related('subject_class', 'property', 'object_class')[:50]
    saved_queries = SPARQLQuery.objects.all().order_by('-created_at')[:10]

    graph_data = get_graph_data()

    context = {
        'classes': classes,
        'properties': properties,
        'facts': facts,
        'saved_queries': saved_queries,
        'graph_data_json': json.dumps(graph_data),
    }
    return render(request, 'ontology/explorer.html', context)


@login_required
def get_graph_data_view(request):
    """AJAX endpoint that returns nodes and edges JSON for D3.js visualization."""
    data = get_graph_data()
    return JsonResponse(data)


@analyst_required
@require_POST
def sparql_query_view(request):
    """
    Executes a user-submitted SPARQL query against the ontology.
    Saves the query execution history in SPARQLResult and returns JSON.
    """
    query_text = (request.POST.get('query') or request.POST.get('sparql_query') or '').strip()
    query_name = request.POST.get('name', 'Ad-hoc Query').strip()

    is_valid, err_msg = validate_sparql_query(query_text)
    if not is_valid:
        return JsonResponse({'status': 'error', 'message': err_msg}, status=400)

    start_time = time.time()
    try:
        results = execute_sparql(query_text)
        elapsed = time.time() - start_time

        # Save query and execution result
        query_obj, _ = SPARQLQuery.objects.get_or_create(
            name=query_name,
            defaults={'query_text': query_text, 'created_by': request.user}
        )

        SPARQLResult.objects.create(
            query=query_obj,
            result_data={'results': results},
            execution_time=elapsed,
            row_count=len(results),
            executed_by=request.user
        )

        return JsonResponse({
            'status': 'success',
            'results': results,
            'row_count': len(results),
            'execution_time': f"{elapsed:.3f}s"
        })
    except Exception as e:
        logger.error(f"Error executing SPARQL query: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def class_detail_view(request, class_name):
    """
    Displays ontology class details including subclasses, domain properties,
    and linked facts.
    """
    ont_class = get_object_or_404(OntologyClass, name=class_name)
    subclasses = ont_class.subclasses.all()
    domain_props = ont_class.properties_as_domain.all()
    range_props = ont_class.properties_as_range.all()
    facts = OntologyFact.objects.filter(subject_class=ont_class).select_related('property', 'object_class')

    context = {
        'class_obj': ont_class,
        'subclasses': subclasses,
        'domain_props': domain_props,
        'range_props': range_props,
        'facts': facts,
    }
    return render(request, 'ontology/class_detail.html', context)
