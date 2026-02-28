import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
    classification_report, roc_curve
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
import seaborn as sns


def simulate_data(num_samples=500):
    """
    Generates a simulated dataset of accounts with graph-derived features.
    """
    np.random.seed(42)
    data = {
        'account_id': [f'acc_{i}' for i in range(num_samples)],
        'hop_distance': np.random.randint(1, 6, size=num_samples),
        'drift_score': np.random.uniform(0, 1, size=num_samples),
        'amount_mean': np.random.uniform(10, 1000, size=num_samples),
        'amount_std': np.random.uniform(5, 200, size=num_samples),
        'daily_velocity': np.random.randint(1, 20, size=num_samples),
        'counterparty_weekly': np.random.randint(1, 50, size=num_samples),
        'device_count': np.random.randint(1, 5, size=num_samples),
        'is_fraud': np.random.choice([True, False], size=num_samples, p=[0.1, 0.9])
    }

    df = pd.DataFrame(data)

    # Inject realistic correlation
    fraud_indices = df[df['is_fraud']].index
    df.loc[fraud_indices, 'hop_distance'] = np.random.randint(1, 3, size=len(fraud_indices))
    df.loc[fraud_indices, 'drift_score'] = np.random.uniform(0.6, 1, size=len(fraud_indices))

    contamination_map = {1: 1.0, 2: 0.6, 3: 0.3, 4: 0.1, 5: 0.1}
    df['contamination_score'] = df['hop_distance'].map(contamination_map)

    return df


def get_dfcrm_risk(row):
    return 0.6 * row['contamination_score'] + 0.4 * row['drift_score']


def get_dfcrm_zone(risk_score):
    if risk_score >= 0.75:
        return 1  # Fraud (Critical)
    else:
        return 0  # Non-Fraud


def evaluate_model(y_true, y_pred, y_proba, model_name):
    metrics = {
        'Accuracy': accuracy_score(y_true, y_pred),
        'Precision': precision_score(y_true, y_pred),
        'Recall': recall_score(y_true, y_pred),
        'F1-score': f1_score(y_true, y_pred),
        'ROC-AUC': roc_auc_score(y_true, y_proba)
    }
    return {model_name: metrics}


def plot_confusion_matrix(y_true, y_pred, title):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Non-Fraud', 'Fraud'],
                yticklabels=['Non-Fraud', 'Fraud'])
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title(title)
    plt.show()


def plot_roc_curve(y_true, y_proba_lr, y_proba_dfcrm):
    fpr_lr, tpr_lr, _ = roc_curve(y_true, y_proba_lr)
    fpr_df, tpr_df, _ = roc_curve(y_true, y_proba_dfcrm)

    plt.figure(figsize=(6, 5))
    plt.plot(fpr_lr, tpr_lr, label='Logistic Regression')
    plt.plot(fpr_df, tpr_df, label='DFCRM')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve Comparison')
    plt.legend()
    plt.show()


def main():
    # 1. Generate Data
    df = simulate_data()

    # 2. Feature Selection
    features = [
        'contamination_score',
        'drift_score',
        'amount_mean',
        'amount_std',
        'daily_velocity',
        'counterparty_weekly',
        'device_count'
    ]

    X = df[features]
    y = df['is_fraud'].astype(int)

    # 3. Train-Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # 4. Logistic Regression with Scaling + Class Balancing
    lr_model = Pipeline([
        ('scaler', StandardScaler()),
        ('lr', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))
    ])

    lr_model.fit(X_train, y_train)

    y_pred_lr = lr_model.predict(X_test)
    y_proba_lr = lr_model.predict_proba(X_test)[:, 1]

    # 5. DFCRM Predictions
    df_test = df.loc[X_test.index].copy()
    df_test['risk_score'] = df_test.apply(get_dfcrm_risk, axis=1)

    y_proba_dfcrm = df_test['risk_score']
    y_pred_dfcrm = df_test['risk_score'].apply(get_dfcrm_zone)

    # 6. Evaluate
    lr_metrics = evaluate_model(y_test, y_pred_lr, y_proba_lr, 'Logistic Regression')
    dfcrm_metrics = evaluate_model(y_test, y_pred_dfcrm, y_proba_dfcrm, 'DFCRM')

    comparison_df = pd.DataFrame({**lr_metrics, **dfcrm_metrics}).T

    print("\n--- Model Performance Comparison ---")
    print(comparison_df)

    print("\n--- Logistic Regression Classification Report ---")
    print(classification_report(y_test, y_pred_lr))

    print("\n--- DFCRM Classification Report ---")
    print(classification_report(y_test, y_pred_dfcrm))

    # 7. Visualizations
    plot_confusion_matrix(y_test, y_pred_lr, 'Logistic Regression Confusion Matrix')
    plot_confusion_matrix(y_test, y_pred_dfcrm, 'DFCRM Confusion Matrix')
    plot_roc_curve(y_test, y_proba_lr, y_proba_dfcrm)

    # 8. Logistic Coefficients
    lr_coefficients = lr_model.named_steps['lr'].coef_[0]
    coef_df = pd.DataFrame({
        'Feature': features,
        'Coefficient': lr_coefficients
    }).sort_values(by='Coefficient', ascending=False)

    print("\n--- Logistic Regression Feature Importance ---")
    print(coef_df)


if __name__ == "__main__":
    main()