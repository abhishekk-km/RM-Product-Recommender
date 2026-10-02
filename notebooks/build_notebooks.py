import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

SETUP = """import sys
from pathlib import Path
ROOT = Path.cwd().resolve()
ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
pd.set_option('display.max_columns', 50)
from src.feature_engineering import load_raw, engineer_features
"""


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t.strip().splitlines(True)}


def code(t):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": t.strip().splitlines(True)}


def save(name, cells):
    nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 4,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                      "name": "python3"},
                       "language_info": {"name": "python"}}}
    (HERE / name).write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print("wrote", name)


save("01_eda.ipynb", [
    md("# 01 EDA: what does the customer base look like?"),
    code(SETUP + "\nraw = load_raw()\nprint(raw.shape)\nraw.head()"),
    code("print(raw['y'].value_counts(normalize=True).round(3))\nprint(raw['balance'].describe())"),
    code("raw['balance'].clip(-2000, 20000).plot.hist(bins=60, figsize=(8, 3),\n"
         "    title='Balance (EUR, clipped)')\nplt.show()"),
    code("def conv(col, data=raw):\n"
         "    return data.groupby(col, observed=True)['y'].apply(lambda s: (s == 'yes').mean() * 100).round(1)\n\n"
         "conv('job').sort_values().plot.barh(figsize=(7, 4), title='Term deposit conversion % by job')\n"
         "plt.show()"),
    code("print(conv(pd.cut(raw['age'], [0, 25, 35, 50, 60, 100])))\nprint(conv('poutcome'))"),
    md("**Takeaways to note for the interview:** class imbalance (about 12% subscribe), "
       "students and retirees convert best, and balance is heavily right-skewed."),
])

save("02_feature_engineering.ipynb", [
    md("# 02 Feature engineering: RM-relevant features"),
    code(SETUP + "\ndf = engineer_features(load_raw())\n"
         "for c in ['segment', 'life_stage', 'risk_profile']:\n"
         "    print(df[c].value_counts(), '\\n')"),
    code("def conv(col):\n"
         "    return df.groupby(col, observed=True)['y'].apply(lambda s: (s == 'yes').mean() * 100).round(1)\n\n"
         "print(conv('segment'))\nprint(conv('risk_profile'))\nprint(conv('life_stage'))"),
    code("df['score_band'] = pd.qcut(df['investment_score'], 5, duplicates='drop')\nprint(conv('score_band'))"),
    code("from src.recommender import recommend\n"
         "keys = ['age', 'job', 'marital', 'education', 'balance', 'housing', 'loan', 'default']\n"
         "sample = df.sample(300, random_state=1)\n"
         "prim = [recommend(r)['primary'].split(' — ')[0] for r in sample[keys].to_dict('records')]\n"
         "pd.Series(prim).value_counts()"),
    code("df.drop(columns=['score_band']).to_csv(ROOT / 'data' / 'processed' / 'customer_profiles.csv', index=False)\n"
         "print('saved')"),
])

save("03_model_training.ipynb", [
    md("# 03 Propensity model and persona tests"),
    code(SETUP + "\nfrom src.propensity import train, predict\nfrom src.recommender import recommend\n"
         "res = train()\nprint('Test ROC-AUC:', round(res['auc'], 3))"),
    code("t = pd.DataFrame({'y': res['y_test'].values, 'p': res['p_test']})\n"
         "t['decile'] = pd.qcut(t['p'].rank(method='first'), 10, labels=list(range(10, 0, -1)))\n"
         "lift = (t.groupby('decile', observed=True)['y'].mean() / t['y'].mean()).sort_index()\n"
         "print(lift.round(2))\n"
         "lift.plot.bar(figsize=(7, 3), title='Lift by propensity decile (1 = top)')\nplt.show()"),
    code("personas = {\n"
         "    'Young salaried, low balance': dict(age=24, job='services', balance=300, housing='no', loan='no', default='no'),\n"
         "    'Mid-career manager, mortgage': dict(age=42, job='management', balance=6000, housing='yes', loan='no', default='no'),\n"
         "    'Retired, high balance': dict(age=66, job='retired', balance=9000, housing='no', loan='no', default='no'),\n"
         "    'Defaulter': dict(age=38, job='blue-collar', balance=-200, housing='yes', loan='yes', default='yes'),\n"
         "}\n"
         "for name, p in personas.items():\n"
         "    o = recommend(p)\n"
         "    print(f\"{name}: {o['segment']} | {o['risk_profile']} | {o['primary'].split(' — ')[0]} | propensity {predict(p):.1%}\")"),
    md("**Honest note:** with call duration excluded, a customer-attribute-only model is a modest "
       "ranker (ROC-AUC well below 0.8), so use it to prioritise outreach, not to decide eligibility."),
])