import os
import json
import logging
from datetime import datetime
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from sklearn.model_selection import train_test_split

from accounts.decorators import analyst_required, admin_required
from crime_data.models import DatasetUpload, CrimeRecord
from notifications.models import Notification
from .models import MLModel, ModelEvaluation
from .utils import (
    prepare_features,
    train_model,
    evaluate_model,
    calculate_baseline,
    save_model,
    get_feature_importance,
    ALGORITHMS
)

logger = logging.getLogger(__name__)


@login_required
@analyst_required
def model_training_view(request):
    """
    Renders model training dashboard:
    - Training form with algorithm selection and feature checkboxes
    - History of previously trained models
    """
    datasets = DatasetUpload.objects.filter(status='completed').order_by('-uploaded_at')
    models_history = MLModel.objects.select_related('dataset', 'created_by').prefetch_related('evaluations').order_by('-created_at')[:10]

    context = {
        'datasets': datasets,
        'algorithms': MLModel.ALGORITHM_CHOICES,
        'models_history': models_history,
    }
    return render(request, 'model_training/training.html', context)


@analyst_required
@require_POST
def train_model_view(request):
    """
    POST endpoint to train a machine learning model on crime data.
    - Prepares dataset features
    - Trains sklearn model
    - Computes evaluation metrics (MAE, MSE, RMSE, R2)
    - Serializes model to disk (.pkl)
    - Saves MLModel & ModelEvaluation records
    - Sends user notification and returns JSON response
    """
    dataset_id = request.POST.get('dataset_id')
    algorithm = request.POST.get('algorithm', 'random_forest')
    model_name = request.POST.get('model_name', '').strip() or f"{algorithm.replace('_', ' ').title()} Model"
    version = request.POST.get('version', 'v1.0')

    # Selected feature columns
    features = request.POST.getlist('features')
    if not features:
        features = ['category_id', 'location_id', 'month', 'day_of_week']

    dataset = get_object_or_404(DatasetUpload, pk=dataset_id)
    records = CrimeRecord.objects.filter(dataset_upload=dataset).select_related('category', 'location')

    if not records.exists():
        # Fallback to all records if specific upload has none
        records = CrimeRecord.objects.select_related('category', 'location').all()

    if not records.exists():
        return JsonResponse({'status': 'error', 'message': 'No crime records available to train model.'}, status=400)

    # Build DataFrame
    data_rows = []
    for r in records:
        data_rows.append({
            'category_id': r.category_id,
            'location_id': r.location_id,
            'month': r.incident_date.month if r.incident_date else 1,
            'day_of_week': r.incident_date.weekday() if r.incident_date else 0,
            'year': r.incident_date.year if r.incident_date else 2024,
            'crime_count': 1.0,
        })
    df = pd.DataFrame(data_rows)

    # Aggregate by features to form true count target
    target_col = 'crime_count'
    groupby_cols = [f for f in features if f in df.columns]
    if groupby_cols:
        df_agg = df.groupby(groupby_cols).size().reset_index(name=target_col)
    else:
        df_agg = df

    # Prepare features
    X, y, encodings = prepare_features(df_agg, features, target_col)

    if len(X) < 5:
        return JsonResponse({'status': 'error', 'message': 'Insufficient data points for training (minimum 5 samples needed).'}, status=400)

    # Train / test split
    test_size = 0.2 if len(X) >= 10 else 0.1
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    # Train model
    hyperparams = {
        'n_estimators': request.POST.get('n_estimators', 100),
        'max_depth': request.POST.get('max_depth', None),
        'learning_rate': request.POST.get('learning_rate', 0.1),
    }

    try:
        model = train_model(X_train, y_train, algorithm, hyperparams)
        metrics = evaluate_model(model, X_test, y_test)
        baseline_mae = calculate_baseline(y_train, y_test)
        feature_importance = get_feature_importance(model, list(X.columns))

        # Save model to disk
        filename = f"{algorithm}_{dataset.id}_{int(timezone.now().timestamp())}.pkl"
        relative_path = os.path.join('trained_models', filename)
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        save_model(model, full_path)

        # Create MLModel instance
        ml_model = MLModel.objects.create(
            name=model_name,
            algorithm=algorithm,
            version=version,
            dataset=dataset,
            target_variable=target_col,
            features=list(X.columns),
            hyperparameters=hyperparams,
            model_file=relative_path,
            status='trained',
            created_by=request.user,
            trained_at=timezone.now()
        )

        # Create ModelEvaluation instance
        evaluation = ModelEvaluation.objects.create(
            model=ml_model,
            mae=metrics['mae'],
            mse=metrics['mse'],
            rmse=metrics['rmse'],
            r2_score=metrics['r2'],
            accuracy=metrics['accuracy'],
            training_samples=len(X_train),
            test_samples=len(X_test),
            baseline_mae=baseline_mae,
            evaluation_notes=f"Trained on {len(X_train)} samples, evaluated on {len(X_test)} samples."
        )

        # Create notification
        Notification.create_notification(
            user=request.user,
            title="Model Training Completed",
            message=f"Model '{ml_model.name}' trained successfully. R² Score: {metrics['r2']}, RMSE: {metrics['rmse']}.",
            notif_type="success",
            category="training",
            action_url=f"/model-training/models/{ml_model.id}/"
        )

        logger.info(f"Model {ml_model.id} ({ml_model.name}) trained successfully by {request.user.username}.")

        return JsonResponse({
            'status': 'success',
            'message': 'Model trained successfully.',
            'model_id': ml_model.id,
            'metrics': metrics,
            'baseline_mae': baseline_mae,
            'feature_importance': feature_importance,
        })

    except Exception as e:
        logger.error(f"Error training model: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def model_list_view(request):
    """Lists all trained ML models with evaluation summaries."""
    models_qs = MLModel.objects.select_related('dataset', 'created_by').prefetch_related('evaluations').order_by('-created_at')
    return render(request, 'model_training/model_list.html', {'models': models_qs})


@login_required
def model_detail_view(request, pk):
    """Shows in-depth details, hyperparameters, and evaluations for a single model."""
    model_obj = get_object_or_404(
        MLModel.objects.select_related('dataset', 'created_by').prefetch_related('evaluations'),
        pk=pk
    )
    latest_eval = model_obj.evaluations.first()
    return render(request, 'model_training/model_detail.html', {
        'model': model_obj,
        'evaluation': latest_eval,
    })


@admin_required
@require_POST
def delete_model_view(request, pk):
    """Deletes an MLModel and its underlying pickle file (Admin only)."""
    model_obj = get_object_or_404(MLModel, pk=pk)
    name = model_obj.name
    if model_obj.model_file and os.path.exists(model_obj.model_file.path):
        try:
            os.remove(model_obj.model_file.path)
        except OSError:
            pass
    model_obj.delete()
    messages.success(request, f"Model '{name}' deleted successfully.")
    return redirect('model_training:model_list')
