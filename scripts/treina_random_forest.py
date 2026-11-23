import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = ROOT / "Dataset_resumido.csv"
MODEL_DIR = ROOT / "models"
METRICS_DIR = ROOT / "docs" / "metrics"

NUMERIC_FEATURES = [
    "dur",
    "sbytes",
    "dbytes",
    "Sload",
    "Dload",
    "Spkts",
    "Dpkts",
    "smeansz",
    "dmeansz",
]

CATEGORICAL_FEATURES = ["proto", "state"]
TARGET = "Label"

RANDOM_STATE = 42
TEST_SIZE = 0.20

CLASS_NAMES = {
    0: "benigno",
    1: "ataque",
}


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {DATASET_PATH}"
        )

    print("Carregando dataset...")
    df = pd.read_csv(DATASET_PATH, low_memory=False)

    required_columns = (
        NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET]
    )
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {missing_columns}"
        )

    # Recorte B: registros com duração preenchida.
    df = df.loc[df["dur"].notna()].copy()

    # Conversão explícita do alvo.
    df[TARGET] = pd.to_numeric(df[TARGET], errors="raise").astype(int)

    if set(df[TARGET].unique()) != {0, 1}:
        raise ValueError(
            "O alvo precisa conter exatamente as classes 0 e 1."
        )

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    print(f"Registros selecionados: {len(df)}")
    print("\nDistribuição das classes:")
    print(y.value_counts().sort_index())

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore"),
            ),
        ]
    )

    preprocessing = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    print("\nTreinando Random Forest...")
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)

    classifier = pipeline.named_steps["classifier"]
    classes = classifier.classes_

    precision, recall, f1, support = (
        precision_recall_fscore_support(
            y_test,
            predictions,
            labels=[0, 1],
            zero_division=0,
        )
    )

    class_metrics = {}

    for index, label in enumerate([0, 1]):
        probability_index = list(classes).index(label)

        pr_auc = average_precision_score(
            (y_test == label).astype(int),
            probabilities[:, probability_index],
        )

        class_metrics[str(label)] = {
            "nome": CLASS_NAMES[label],
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1_score": float(f1[index]),
            "pr_auc": float(pr_auc),
            "support": int(support[index]),
        }

    cm = confusion_matrix(y_test, predictions, labels=[0, 1])

    confusion = {
        "ordem_classes": ["benigno (0)", "ataque (1)"],
        "valores": cm.tolist(),
        "verdadeiros_negativos": int(cm[0, 0]),
        "falsos_positivos": int(cm[0, 1]),
        "falsos_negativos": int(cm[1, 0]),
        "verdadeiros_positivos": int(cm[1, 1]),
    }
    metrics = {
        "experimento": "baseline_random_forest",
        "dataset": DATASET_PATH.name,
        "recorte": "registros com dur preenchida",
        "total_registros": len(df),
        "registros_treino": len(X_train),
        "registros_teste": len(X_test),
        "proporcao_teste": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "modelo": "RandomForestClassifier",
        "parametros": {
            "n_estimators": 200,
            "class_weight": "balanced",
            "random_state": RANDOM_STATE,
            "n_jobs": -1,
        },
        "variaveis_numericas": NUMERIC_FEATURES,
        "variaveis_categoricas": CATEGORICAL_FEATURES,
        "variaveis_excluidas": {
            "service": (
                "Excluída do primeiro baseline devido à alta "
                "proporção de ausências e forte associação entre "
                "ausência e classe. Será candidata a comparação."
            ),
            "ct_state_ttl": "Pendente de decisão no contrato.",
            "trans_depth": "Totalmente ausente no recorte.",
            "res_bdy_len": "Totalmente ausente no recorte.",
            "is_sm_ips_ports": "Constante no recorte.",
        },
        "matriz_confusao": confusion,
        "accuracy": float(accuracy_score(y_test, predictions)),
        "metricas_por_classe": class_metrics,
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_DIR / "random_forest_baseline.joblib"
    metrics_path = (
        METRICS_DIR / "random_forest_baseline.json"
    )

    joblib.dump(pipeline, model_path)

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=4)

    print("\n===== RESULTADOS DO BASELINE =====")
    print(f"Acurácia: {metrics['accuracy']:.4f}")

    for label, values in class_metrics.items():
        print(f"\nClasse {label} - {values['nome']}")
        print(f"Precision: {values['precision']:.4f}")
        print(f"Recall:    {values['recall']:.4f}")
        print(f"F1-score:  {values['f1_score']:.4f}")
        print(f"PR-AUC:    {values['pr_auc']:.4f}")
        print(f"Support:   {values['support']}")

    print("\nArquivos salvos:")
    print(model_path)
    print(metrics_path)


if __name__ == "__main__":
    main()