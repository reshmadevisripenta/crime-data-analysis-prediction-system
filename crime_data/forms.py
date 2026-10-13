import os
from django import forms
from django.core.exceptions import ValidationError
from .models import DatasetUpload, CrimeRecord, CrimeCategory, Location


class DatasetUploadForm(forms.ModelForm):
    """Form for uploading CSV/Excel crime datasets with file extension and size validation."""
    ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls']
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    file_type = forms.ChoiceField(
        choices=DatasetUpload.FILE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = DatasetUpload
        fields = ['file', 'file_type']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.csv,.xlsx,.xls'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        if file and not cleaned_data.get('file_type'):
            ext = os.path.splitext(file.name)[1].lower()
            if ext in ['.xlsx', '.xls']:
                cleaned_data['file_type'] = 'excel'
            else:
                cleaned_data['file_type'] = 'csv'
        return cleaned_data

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if not uploaded_file:
            raise ValidationError("Please select a file to upload.")

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file format '{ext}'. Only CSV (.csv) and Excel (.xlsx, .xls) files are supported."
            )

        if uploaded_file.size > self.MAX_FILE_SIZE:
            raise ValidationError("File size exceeds 50 MB limit. Please upload a smaller file.")

        return uploaded_file


class CrimeRecordForm(forms.ModelForm):
    """Form for creating and editing individual CrimeRecord instances."""
    class Meta:
        model = CrimeRecord
        fields = [
            'category',
            'location',
            'incident_date',
            'incident_time',
            'description',
            'severity',
            'status',
            'source',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'incident_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'incident_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed crime description'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Police Log, Citizen Report, FIR'}),
        }
