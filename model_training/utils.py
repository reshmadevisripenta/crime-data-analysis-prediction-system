import os
import pickle
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.svm import SVR
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from django.conf import settings

logger = logging.getLogger(__name__)

ALGORITHMS = {
    'random_forest': RandomForestRegressor,
    'linear_regression': LinearRegression,
    'decision_tree': DecisionTreeRegressor,
    'gradient_boosting': GradientBoostingRegressor,
    'ridge': Ridge,
    'svr': SVR,
}


def prepare_features(df, feature_cols, target_col):
    """
    Preprocesses tabular DataFrame for machine learning:
    - Encodes categorical variables
    - Imputes missing numeric values
    - Returns X (DataFrame), y (Series), and encoding mapping dictionary
    """
    df_clean = df.copy()

    # Fill target if missing
    if target_col in df_clean.columns:
        df_clean[target_col] = pd.to_numeric(df_clean[target_col], errors='coerce').fillna(1.0)
    else:
        # Default target if column not present (count frequency = 1 per event)
        df_clean[target_col] = 1.0

    encodings = {}
    X_cols = []

    for col in feature_cols:
        if col not in df_clean.columns:
            continue
        X_cols.append(col)

        # Categorical encoding
        if df_clean[col].dtype == 'object' or df_clean[col].dtype.name == 'category':
            df_clean[col] = df_clean[col].astype(str).fillna('missing')
            unique_vals = list(df_clean[col].unique())
            mapping = {val: idx for idx, val in enumerate(unique_vals)}
            encodings[col] = mapping
            df_clean[col] = df_clean[col].map(mapping)
        else:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(df_clean[col].mean())

    X = df_clean[X_cols]
    y = df_clean[target_col]
    return X, y, encodings


def train_model(X_train, y_train, algorithm, hyperparams=None):
    """
    Instantiates and fits an sklearn regressor based on algorithm choice.
    Returns the fitted model.
    """
    hyperparams = hyperparams or {}
    model_class = ALGORITHMS.get(algorithm, RandomForestRegressor)

    if algorithm == 'random_forest':
        n_estimators = int(hyperparams.get('n_estimators', 100))
        max_depth = int(hyperparams.get('max_depth', 10)) if hyperparams.get('max_depth') else None
        model = model_class(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
    elif algorithm == 'gradient_boosting':
        n_estimators = int(hyperparams.get('n_estimators', 100))
        learning_rate = float(hyperparams.get('learning_rate', 0.1))
        model = model_class(n_estimators=n_estimators, learning_rate=learning_rate, random_state=42)
    elif algorithm == 'decision_tree':
        max_depth = int(hyperparams.get('max_depth', 10)) if hyperparams.get('max_depth') else None
        model = model_class(max_depth=max_depth, random_state=42)
    elif algorithm == 'linear_regression':
        model = model_class()
    elif algorithm == 'ridge':
        alpha = float(hyperparams.get('alpha', 1.0))
        model = model_class(alpha=alpha, random_state=42)
    elif algorithm == 'svr':
        C = float(hyperparams.get('C', 1.0))
        model = model_class(C=C)
    else:
        model = RandomForestRegressor(n_estimators=100, random_state=42)

    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test, y_test):
    """
    Evaluates model predictions against ground truth test set.
    Returns metrics dict: {mae, mse, rmse, r2, accuracy}
    """
    y_pred = model.predict(X_test)

    mae = float(mean_absolute_error(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    r2_val = r2_score(y_test, y_pred) if len(y_test) >= 2 else 0.0
    r2 = 0.0 if (r2_val is None or np.isnan(r2_val)) else float(r2_val)

    # Approximate accuracy percentage based on relative error bounded [0, 100]
    mean_actual = np.mean(y_test) if len(y_test) > 0 and np.mean(y_test) != 0 else 1.0
    relative_err = min(mae / abs(mean_actual), 1.0)
    accuracy = float(max(0.0, (1.0 - relative_err) * 100))

    actual_list = [round(float(v), 2) for v in (y_test.values if hasattr(y_test, 'values') else y_test)]
    pred_list = [round(float(v), 2) for v in y_pred]

    return {
        'mae': round(mae, 4),
        'mse': round(mse, 4),
        'rmse': round(rmse, 4),
        'r2': round(r2, 4),
        'accuracy': round(accuracy, 2),
        'actual': actual_list,
        'predicted': pred_list,
    }


def calculate_baseline(y_train, y_test):
    """
    Computes naive mean baseline MAE.
    """
    mean_val = np.mean(y_train) if len(y_train) > 0 else 0.0
    baseline_preds = np.full_like(y_test, fill_value=mean_val)
    baseline_mae = float(mean_absolute_error(y_test, baseline_preds))
    return round(baseline_mae, 4)


def save_model(model, file_path):
    """Serializes model to disk using pickle."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as f:
        pickle.dump(model, f)
    logger.info(f"Model saved to {file_path}")


def load_model(file_path):
    """Deserializes model from disk using pickle."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Model artifact not found at {file_path}")
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def get_feature_importance(model, feature_names):
    """
    Returns feature importance mapping if supported by the model.
    """
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        return {feat: round(float(imp), 4) for feat, imp in zip(feature_names, importances)}
    elif hasattr(model, 'coef_'):
        coefs = model.coef_
        return {feat: round(float(c), 4) for feat, c in zip(feature_names, coefs)}
    return {}
