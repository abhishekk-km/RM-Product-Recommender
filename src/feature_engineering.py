import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EUR_INR = 90
NOT_EMPLOYED = {"retired", "student", "unemployed", "unknown"}


def load_raw():
    files = list((ROOT / "data").rglob("bank-full.csv"))
    if not files:
        raise FileNotFoundError("bank-full.csv not found under data/")
    return pd.read_csv(files[0], sep=";")


def engineer_features(df):
    df = df.copy()
    df["balance_inr"] = df["balance"] * EUR_INR
    df["segment"] = pd.cut(df["balance_inr"], [-np.inf, 50000, 200000, 500000, np.inf],
                           labels=["Mass", "Emerging Affluent", "Affluent", "HNI"]).astype(str)
    df["life_stage"] = pd.cut(df["age"], [0, 25, 35, 50, 60, np.inf],
                              labels=["Young Adult", "Early Career", "Mid Career",
                                      "Pre-Retirement", "Senior"]).astype(str)
    conservative = (df["age"] >= 55) | (df["default"] == "yes") | \
                   ((df["housing"] == "yes") & (df["loan"] == "yes"))
    aggressive = (df["age"] < 35) & (df["balance_inr"] > 50000)
    df["risk_profile"] = np.select([conservative, aggressive],
                                   ["Conservative", "Aggressive"], "Moderate")
    df["employed"] = ~df["job"].isin(NOT_EMPLOYED)
    df["loan_eligible"] = (df["balance_inr"] > 10000) & (df["default"] == "no")
    score = (40 * np.clip(df["balance_inr"] / 500000, 0, 1)
             + 30 * (df["housing"] == "no") + 20 * (df["loan"] == "no")
             + 10 * (df["default"] == "no"))
    df["investment_score"] = score.clip(0, 100).round().astype(int)
    return df


if __name__ == "__main__":
    out = engineer_features(load_raw())
    out_dir = ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_dir / "customer_profiles.csv", index=False)
    out.sample(500, random_state=1).to_csv(out_dir / "customer_profiles_sample.csv", index=False)
    print(out[["segment", "life_stage", "risk_profile"]].describe())
    print("Saved", len(out), "rows")