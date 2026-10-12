from django.db import models
from django.conf import settings


class OntologyClass(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text='URI/Class name identifier e.g. ViolentCrime')
    label = models.CharField(max_length=150, help_text='Human-readable label')
    description = models.TextField(blank=True)
    parent_class = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subclasses'
    )
    color_code = models.CharField(max_length=7, default='#1769FF', help_text='Hex color for graph node visualization')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ontology Class'
        verbose_name_plural = 'Ontology Classes'
        ordering = ['name']

    def __str__(self):
        return f'{self.label} ({self.name})'


class OntologyProperty(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ('object', 'Object Property'),
        ('data', 'Datatype Property'),
        ('annotation', 'Annotation Property'),
    ]

    name = models.CharField(max_length=100, unique=True, help_text='Property name identifier e.g. occursAtLocation')
    label = models.CharField(max_length=150, help_text='Human-readable label')
    description = models.TextField(blank=True)
    domain_class = models.ForeignKey(
        OntologyClass,
        on_delete=models.CASCADE,
        related_name='properties_as_domain'
    )
    range_class = models.ForeignKey(
        OntologyClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='properties_as_range'
    )
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES, default='object')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ontology Property'
        verbose_name_plural = 'Ontology Properties'
        ordering = ['name']

    def __str__(self):
        return f'{self.label} [{self.get_property_type_display()}]'


class OntologyFact(models.Model):
    subject_class = models.ForeignKey(
        OntologyClass,
        on_delete=models.CASCADE,
        related_name='facts_as_subject'
    )
    property = models.ForeignKey(
        OntologyProperty,
        on_delete=models.CASCADE,
        related_name='facts'
    )
    object_class = models.ForeignKey(
        OntologyClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facts_as_object'
    )
    literal_value = models.CharField(max_length=500, null=True, blank=True)
    source_record_id = models.IntegerField(null=True, blank=True, help_text='Optional reference to CrimeRecord ID')
    is_inferred = models.BooleanField(default=False, help_text='True if derived by SWRL / semantic reasoner')
    inference_rule = models.CharField(max_length=150, null=True, blank=True, help_text='Name of SWRL rule that generated this fact')

    class Meta:
        verbose_name = 'Ontology Fact'
        verbose_name_plural = 'Ontology Facts'
        ordering = ['id']

    def __str__(self):
        obj = self.object_class.name if self.object_class else str(self.literal_value)
        return f'{self.subject_class.name} -> {self.property.name} -> {obj}'


class SPARQLQuery(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    query_text = models.TextField(help_text='SPARQL query string')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sparql_queries')
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'SPARQL Query'
        verbose_name_plural = 'SPARQL Queries'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class SPARQLResult(models.Model):
    query = models.ForeignKey(SPARQLQuery, on_delete=models.CASCADE, related_name='execution_results')
    result_data = models.JSONField(default=dict, blank=True, help_text='JSON result payload')
    execution_time = models.FloatField(help_text='Execution duration in seconds')
    row_count = models.IntegerField(default=0)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sparql_executions')
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SPARQL Result'
        verbose_name_plural = 'SPARQL Results'
        ordering = ['-executed_at']

    def __str__(self):
        return f'Result for "{self.query.name}" ({self.row_count} rows, {self.execution_time:.3f}s)'
