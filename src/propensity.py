import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.feature_engineering import engineer_features, load_raw

MODEL_PATH = ROOT / "models" / "propensity.joblib"
CAT = ["job", "marital", "education", "default", "housing", "loan", "segment", "life_stage"]
NUM = ["age", "balance_inr", "investment_score"]
BASE = dict(job="admin.", marital="married", education="secondary",
            default="no", housing="no", loan="no")
_MODEL = None


def train():
    df = engineer_features(load_raw())
    X, y = df[CAT + NUM], (df["y"] == "yes").astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pre = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), CAT),
                             ("n", StandardScaler(), NUM)])
    model = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000))])
    model.fit(Xtr, ytr)
    p = model.predict_proba(Xte)[:, 1]
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return dict(model=model, auc=roc_auc_score(yte, p), y_test=yte, p_test=p)


def _load():
    global _MODEL
    if _MODEL is None:
        try:
            _MODEL = joblib.load(MODEL_PATH)
        except Exception:
            _MODEL = train()["model"]
    return _MODEL


def predict(p):
    try:
        df = engineer_features(pd.DataFrame([{**BASE, **p}]))
        return float(_load().predict_proba(df[CAT + NUM])[0, 1])
    except Exception:
        return None


if __name__ == "__main__":
    res = train()
    print("Test ROC-AUC:", round(res["auc"], 3), "| saved to", MODEL_PATH)
