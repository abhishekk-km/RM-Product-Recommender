import pandas as pd
from src.feature_engineering import engineer_features
from src.product_catalog import PRODUCTS

DEFAULTS = dict(job="admin.", default="no", housing="no", loan="no", has_vehicle=False)


def recommend(p):
    r = engineer_features(pd.DataFrame([{**DEFAULTS, **p}])).iloc[0].to_dict()
    hits = []
    for x in PRODUCTS:
        if x["seg"] and r["segment"] not in x["seg"]:
            continue
        if x["stage"] and r["life_stage"] not in x["stage"]:
            continue
        if not x["cond"](r):
            continue
        score = 1 + 2 * bool(x["seg"]) + 2 * bool(x["stage"]) + (x["cat"] == "insurance")
        hits.append((score, x))
    hits.sort(key=lambda t: -t[0])
    top = [f"{x['name']} — {x['why']}" for _, x in hits]

    notes = ["Complete KYC and risk-suitability check before selling investments; disclose charges."]
    if r["default"] == "yes":
        notes.append("Credit default on record: avoid credit products, focus on regularising.")
    if not r["loan_eligible"]:
        notes.append("Not loan-eligible right now (low balance or default).")
    if r["housing"] == "yes" and r["loan"] == "yes":
        notes.append("Already carries housing + personal loan: watch over-leverage.")

    return dict(
        summary=f"{int(r['age'])}-year-old {r['job']}, balance ≈ ₹{int(r['balance_inr']):,}",
        segment=r["segment"], life_stage=r["life_stage"], risk_profile=r["risk_profile"],
        investment_score=int(r["investment_score"]),
        primary=top[0] if top else "No match",
        secondary=top[1:4],
        cross_sell=top[4] if len(top) > 4 else "None for now",
        rm_note=notes,
        ranked=[(s, x["name"], x["cat"]) for s, x in hits],
    )