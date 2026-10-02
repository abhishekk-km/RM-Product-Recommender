# ICICI RM Product Recommendation Assistant

A decision-support tool that mimics how a Relationship Manager (RM) thinks: build a Customer 360 profile, segment the customer, apply eligibility rules, rank products with reasoning, and hand a structured brief to a Claude Project that explains the recommendation in plain RM language.

## Architecture

    bank-full.csv -> feature_engineering.py -> segment, life stage, risk, eligibility, investment score
                                              |
                      product_catalog.py + recommender.py -> ranked products + RM notes
                                              |
                      propensity.py -> term-deposit likelihood
                                              |
                      Streamlit app (app/main.py) -> customer brief -> Claude Project (RM assistant)

## Setup

```
pip install -r requirements.txt
python src/feature_engineering.py
python src/propensity.py
python notebooks/build_notebooks.py
streamlit run app/main.py
```

## Data

UCI Bank Marketing (`bank-full.csv`, 45,211 records, Portuguese bank). Balance is in euros and is converted to rupees at 90 purely as a proxy. Call `duration` is excluded from modelling because it is only known after the call (target leakage).

## Method

- Segments: Mass, Emerging Affluent, Affluent, HNI (balance thresholds)
- Life stage: five age bands
- Risk: rule-based from age, leverage and default history
- Eligibility: loans need positive balance, no default and employment
- Ranking: segment fit, life-stage fit, protection-first bonus for insurance
- Propensity: logistic regression on customer attributes

## Claude Project

`claude_project/system_prompt.md` goes in the project instructions. Upload `product_catalog.md`, `rm_rules.md` and `data/processed/customer_profiles_sample.csv` as knowledge.

## Limitations

- Thresholds and product rules are illustrative, not ICICI's official criteria
- Product names, fees and rates change: verify on icicibank.com
- Euro-to-rupee balances are a proxy for Indian customers
- Propensity model is a modest ranker, not an approval engine
- Decision support only: suitability, KYC and customer consent stay with the RM

## Next steps

Real income and spend features, calibration of the propensity model, A/B tests of product ranking, CRM integration.