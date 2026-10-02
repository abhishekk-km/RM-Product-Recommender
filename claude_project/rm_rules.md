# RM Rules (mirrors src/feature_engineering.py and src/recommender.py)

## Currency
Balance in the dataset is in euros; converted to rupees at 90 for segmentation. This is a proxy, not real Indian balances.

## Segments (rupee balance)
- Mass: up to 50,000 (including negative balances)
- Emerging Affluent: 50,001 to 2,00,000
- Affluent: 2,00,001 to 5,00,000
- HNI: above 5,00,000

## Life stage (age)
Young Adult 25 and under; Early Career 26-35; Mid Career 36-50; Pre-Retirement 51-60; Senior 61+.

## Risk profile
- Conservative if age 55+, or credit default, or both housing loan and personal loan.
- Aggressive if age under 35 and balance above Rs 50,000 (and not Conservative).
- Otherwise Moderate.

## Employment
Not employed: retired, student, unemployed, unknown. Everything else counts as employed.

## Loan eligibility
Eligible only if rupee balance is above 10,000 and there is no credit default.

## Investment capacity score (0-100)
40 x min(balance / 5,00,000, 1) + 30 if no housing loan + 20 if no personal loan + 10 if no default.

## Ranking
Base 1 point. +2 if the product targets the customer's segment. +2 if it targets the life stage. +1 for insurance. Highest first: top is primary, next three are secondary, fifth is the cross-sell.

## Mandatory RM notes
- Always: KYC and risk-suitability before investments; disclose charges.
- Default on record: avoid credit products, focus on regularising.
- Not loan eligible: say so explicitly.
- Housing plus personal loan: watch over-leverage.

## Escalate to a senior RM / credit team
Defaults, very high leverage, HNI portfolio requests, anything outside the catalog.