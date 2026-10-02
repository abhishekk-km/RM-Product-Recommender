import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.feature_engineering import EUR_INR, NOT_EMPLOYED
from src.propensity import predict
from src.recommender import recommend

JOBS = ["admin.", "blue-collar", "entrepreneur", "housemaid", "management", "retired",
        "self-employed", "services", "student", "technician", "unemployed", "unknown"]
MARITAL = ["married", "single", "divorced"]
EDU = ["primary", "secondary", "tertiary", "unknown"]
ORDER = ["Mass", "Emerging Affluent", "Affluent", "HNI"]
LS_ORDER = ["Young Adult", "Early Career", "Mid Career", "Pre-Retirement", "Senior"]
KEYS = ["age", "job", "marital", "education", "balance", "housing", "loan", "default"]
ORANGE, MAROON = "#F37E20", "#AE282E"
CMAP = {"Mass": "#FBC490", "Emerging Affluent": ORANGE, "Affluent": "#C8502A", "HNI": MAROON}
PAL = [ORANGE, MAROON, "#F9C99B", "#7A7A7A", "#C8502A", "#FBC490"]
INV_STEPS = [{"range": [0, 40], "color": "#F7DCC4"},
             {"range": [40, 70], "color": "#F3B27A"},
             {"range": [70, 100], "color": "#E88A3A"}]
DATA = ROOT / "data" / "processed" / "customer_profiles.csv"

st.set_page_config(page_title="ICICI RM Assistant", page_icon="🏦", layout="wide")
st.markdown("""
<style>
.hero{background:linear-gradient(90deg,#AE282E,#F37E20);padding:22px 28px;border-radius:14px;margin-bottom:18px}
.hero .t{color:#fff;font-size:2rem;font-weight:700}
.hero .s{color:#ffe9d6;margin-top:4px}
.kpi{background:#FFF3E8;border-left:5px solid #AE282E;border-radius:10px;padding:12px 14px;margin-bottom:12px}
.kpi .l{font-size:.75rem;color:#6b6b6b;text-transform:uppercase;letter-spacing:.04em}
.kpi .v{font-size:1.6rem;font-weight:700;color:#AE282E;line-height:1.25}
.kpi .s{font-size:.75rem;color:#8a8a8a}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    return pd.read_csv(DATA) if DATA.exists() else None


def baselines():
    df = load_data()
    if df is None:
        return None, {}
    return df["y"].eq("yes").mean(), df.groupby("segment")["investment_score"].mean().to_dict()


@st.cache_data(show_spinner="Scoring sample customers...")
def product_mix(seg_t, ls_t, n=400):
    df = load_data()
    d = df[df["segment"].isin(seg_t) & df["life_stage"].isin(ls_t)]
    rows = []
    for r in d.sample(min(n, len(d)), random_state=1)[KEYS].to_dict("records"):
        for _, name, cat in recommend(r)["ranked"][:3]:
            rows.append((name, cat))
    return (pd.DataFrame(rows, columns=["product", "category"])
            .value_counts().reset_index(name="customers"))


def plot(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def style(fig, h=330):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=50, b=10),
                      title_font_size=15, legend_title_text="")
    return fig


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="l">{label}</div><div class="v">{value}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)


def gauge(v, title, maxv, ref=None, steps=None, fmt=".0f"):
    mode = "gauge+number" + ("+delta" if ref is not None else "")
    fig = go.Figure(go.Indicator(
        mode=mode, value=float(v), title={"text": title},
        number={"valueformat": fmt},
        delta={"reference": float(ref), "valueformat": fmt} if ref is not None else None,
        gauge={"axis": {"range": [0, maxv]}, "bar": {"color": MAROON}, "steps": steps or []}))
    fig.update_layout(height=270, margin=dict(l=20, r=20, t=70, b=10))
    return fig


def radar(p):
    bal = p["balance"] * EUR_INR
    d = {"Balance strength": min(max(bal, 0) / 500000, 1) * 100,
         "Debt freedom": 100 - 50 * (p.get("housing") == "yes") - 50 * (p.get("loan") == "yes"),
         "Credit health": 0 if p.get("default") == "yes" else 100,
         "Income stability": 30 if p.get("job", "admin.") in NOT_EMPLOYED else 100,
         "Time horizon": max(0, min(100, (65 - p["age"]) / 40 * 100))}
    k = list(d.keys())
    fig = go.Figure(go.Scatterpolar(r=list(d.values()) + [d[k[0]]], theta=k + [k[0]],
                                    fill="toself", line_color=MAROON,
                                    fillcolor="rgba(174,40,46,0.25)"))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], visible=True)),
                      showlegend=False, height=270, margin=dict(l=40, r=40, t=70, b=10),
                      title=dict(text="Customer strength profile", x=0.5, font=dict(size=15)))
    return fig


def brief(o, prob):
    lines = [f"Customer Summary: {o['summary']}",
             f"Segment: {o['segment']} | Life Stage: {o['life_stage']} | Risk: {o['risk_profile']}",
             f"Investment score: {o['investment_score']}/100",
             f"Term-deposit propensity: {prob:.0%}" if prob is not None else "",
             f"Engine primary pick: {o['primary']}",
             "Engine secondary picks: " + "; ".join(o["secondary"]),
             "Flags: " + " | ".join(o["rm_note"]),
             "Please give the full RM recommendation in the standard format."]
    return "\n".join(x for x in lines if x)


def show(o, prob, p):
    base, seg_avg = baselines()
    c = st.columns(3)
    c[0].metric("Segment", o["segment"])
    c[1].metric("Life stage", o["life_stage"])
    c[2].metric("Risk profile", o["risk_profile"])
    st.caption(o["summary"])
    g1, g2, g3 = st.columns(3)
    with g1:
        plot(gauge(o["investment_score"], "Investment capacity (Δ vs segment avg)", 100,
                   ref=seg_avg.get(o["segment"]), steps=INV_STEPS))
    with g2:
        if prob is None:
            st.info("Run `python src/propensity.py` to enable the propensity gauge.")
        else:
            plot(gauge(prob * 100, "Term-deposit propensity % (Δ vs base)",
                       max(30, min(100, int(prob * 200) + 1)),
                       ref=None if base is None else base * 100, fmt=".1f"))
    with g3:
        plot(radar(p))
    st.success("**Primary recommendation:** " + o["primary"])
    left, right = st.columns(2)
    with left:
        st.markdown("**Secondary recommendations**")
        for s in o["secondary"] or ["None"]:
            st.write("- " + s)
        st.markdown("**Cross-sell opportunity (next quarter)**")
        st.write(o["cross_sell"])
        st.markdown("**RM notes**")
        for n in o["rm_note"]:
            st.warning(n)
    with right:
        rk = pd.DataFrame(o["ranked"][:8], columns=["fit score", "product", "category"])
        if rk.empty:
            st.info("No eligible products found.")
        else:
            fig = px.bar(rk, x="fit score", y="product", color="category", orientation="h",
                         color_discrete_sequence=PAL, title="Product fit ranking")
            fig.update_yaxes(autorange="reversed", title=None)
            plot(style(fig, 400))


def portfolio(d, seg_t, ls_t):
    n = len(d)
    conv = d["y"].eq("yes").mean() * 100
    rate = lambda s: (s == "yes").mean() * 100
    r1 = st.columns(5)
    kpi(r1[0], "Customers", f"{n:,}", "in current filter")
    kpi(r1[1], "Avg balance", f"₹{d['balance_inr'].mean():,.0f}",
        f"median ₹{d['balance_inr'].median():,.0f}")
    kpi(r1[2], "Affluent + HNI share", f"{d['segment'].isin(['Affluent', 'HNI']).mean() * 100:.1f}%",
        "wealth-tier customers")
    kpi(r1[3], "Term-deposit conversion", f"{conv:.1f}%", "campaign success rate")
    kpi(r1[4], "Loan-eligible", f"{d['loan_eligible'].mean() * 100:.1f}%", "balance > ₹10k, no default")
    hp = ((d["investment_score"] >= 60) & (d["default"] == "no")).mean() * 100
    r2 = st.columns(5)
    kpi(r2[0], "Avg investment score", f"{d['investment_score'].mean():.0f}/100", "capacity to invest")
    kpi(r2[1], "Housing-loan holders", f"{(d['housing'] == 'yes').mean() * 100:.1f}%", "existing mortgage")
    kpi(r2[2], "Credit defaults", f"{(d['default'] == 'yes').mean() * 100:.1f}%", "avoid credit products")
    kpi(r2[3], "Conservative risk", f"{(d['risk_profile'] == 'Conservative').mean() * 100:.1f}%",
        "FD / safe products")
    kpi(r2[4], "High-potential", f"{hp:.1f}%", "score ≥ 60 and no default")

    a, b = st.columns(2)
    cnt = d["segment"].value_counts().reindex(ORDER).dropna()
    fig = go.Figure(go.Pie(labels=list(cnt.index), values=list(cnt.values), hole=0.55,
                           sort=False, marker=dict(colors=[CMAP[s] for s in cnt.index])))
    fig.update_layout(title="Customer mix by segment")
    with a:
        plot(style(fig))
    cs = (d.groupby("segment")["y"].apply(rate).reindex(ORDER).dropna().round(1)
          .reset_index(name="rate"))
    fig = px.bar(cs, x="segment", y="rate", color="segment", color_discrete_map=CMAP,
                 text="rate", title="Term-deposit conversion % by segment")
    fig.update_traces(texttemplate="%{text}%")
    fig.add_hline(y=conv, line_dash="dot", annotation_text="overall")
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None)
    with b:
        plot(style(fig))

    a, b = st.columns(2)
    emp = d["employed"]
    elig = emp & d["loan_eligible"]
    cap = elig & (d["investment_score"] >= 60)
    fig = go.Figure(go.Funnel(
        y=["All customers", "Employed", "Employed & loan-eligible", "Cross-sell ready (score ≥ 60)"],
        x=[n, int(emp.sum()), int(elig.sum()), int(cap.sum())],
        textinfo="value+percent initial",
        marker=dict(color=["#FBC490", ORANGE, "#C8502A", MAROON])))
    fig.update_layout(title="Cross-sell funnel")
    with a:
        plot(style(fig))
    ct = (pd.crosstab(d["life_stage"], d["segment"])
          .reindex(index=LS_ORDER, columns=ORDER, fill_value=0))
    fig = px.imshow(ct, text_auto=True, aspect="auto", color_continuous_scale="Oranges",
                    title="Life stage × segment (customers)")
    fig.update_layout(coloraxis_showscale=False, xaxis_title=None, yaxis_title=None)
    with b:
        plot(style(fig))

    a, b = st.columns(2)
    rk = (pd.crosstab(d["segment"], d["risk_profile"], normalize="index") * 100) \
        .reindex(ORDER).dropna(how="all").round(1)
    fig = px.bar(rk, text_auto=True, title="Risk profile mix by segment (%)",
                 color_discrete_map={"Conservative": MAROON, "Moderate": ORANGE,
                                     "Aggressive": "#F9C99B"},
                 labels={"value": "% of segment", "variable": "Risk"})
    fig.update_layout(xaxis_title=None)
    with a:
        plot(style(fig))
    fig = px.histogram(d, x="investment_score", nbins=20, color_discrete_sequence=[ORANGE],
                       title="Investment score distribution")
    fig.add_vline(x=d["investment_score"].mean(), line_dash="dot", annotation_text="avg")
    with b:
        plot(style(fig))

    a, b = st.columns(2)
    cj = d.groupby("job")["y"].apply(rate).round(1).sort_values().reset_index(name="rate")
    fig = px.bar(cj, x="rate", y="job", orientation="h", color_discrete_sequence=[MAROON],
                 title="Conversion % by occupation")
    fig.update_layout(yaxis_title=None, xaxis_title=None)
    with a:
        plot(style(fig, 400))
    bands = pd.cut(d["age"], [0, 25, 35, 50, 60, 100],
                   labels=["≤25", "26-35", "36-50", "51-60", "60+"])
    ca = d.groupby(bands, observed=True)["y"].apply(rate).round(1).reset_index(name="rate")
    fig = px.bar(ca, x="age", y="rate", color_discrete_sequence=[ORANGE],
                 title="Conversion % by age band", text="rate")
    fig.update_traces(texttemplate="%{text}%")
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    with b:
        plot(style(fig, 400))

    a, b = st.columns(2)
    bl = (d.groupby("life_stage")["balance_inr"].mean().reindex(LS_ORDER).dropna().round(0)
          .reset_index())
    fig = px.bar(bl, x="life_stage", y="balance_inr", color_discrete_sequence=[MAROON],
                 title="Average balance (₹) by life stage")
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    with a:
        plot(style(fig, 400))
    pm = product_mix(tuple(seg_t), tuple(ls_t))
    fig = px.bar(pm.sort_values("customers"), x="customers", y="product", color="category",
                 orientation="h", color_discrete_sequence=PAL,
                 title="Product demand (top-3 picks, 400 sampled customers)")
    fig.update_layout(yaxis_title=None)
    with b:
        plot(style(fig, 400))


st.markdown('<div class="hero"><div class="t">🏦 ICICI RM Product Recommender</div>'
            '<div class="s">Customer 360 profile → segment, life stage, risk → ranked products '
            'with reasoning</div></div>', unsafe_allow_html=True)
t1, t2, t3, t4 = st.tabs(["RM Recommender", "Portfolio Insights", "Customer Lookup", "How it works"])

with t1:
    a, b = st.columns(2)
    age = a.number_input("Age", 18, 100, 35)
    job = a.selectbox("Job", JOBS)
    marital = a.selectbox("Marital status", MARITAL)
    edu = a.selectbox("Education", EDU, index=1)
    bal = b.number_input("Avg yearly balance (EUR, converted to INR at 90)", value=1000)
    housing = b.selectbox("Housing loan", ["no", "yes"])
    loan = b.selectbox("Personal loan", ["no", "yes"])
    default = b.selectbox("Credit default", ["no", "yes"])
    car = b.checkbox("Owns a vehicle")
    if st.button("Recommend", type="primary"):
        p = dict(age=int(age), job=job, marital=marital, education=edu, balance=int(bal),
                 housing=housing, loan=loan, default=default, has_vehicle=car)
        show(recommend(p), predict(p), p)

with t2:
    df = load_data()
    if df is None:
        st.warning("Run `python src/feature_engineering.py` first.")
    else:
        f1, f2 = st.columns(2)
        seg_f = f1.multiselect("Segments", ORDER, default=ORDER)
        ls_f = f2.multiselect("Life stages", LS_ORDER, default=LS_ORDER)
        d = df[df["segment"].isin(seg_f) & df["life_stage"].isin(ls_f)]
        if d.empty:
            st.warning("No customers match the selected filters.")
        else:
            portfolio(d, seg_f, ls_f)

with t3:
    df = load_data()
    if df is None:
        st.warning("Run `python src/feature_engineering.py` first.")
    else:
        idx = int(st.number_input("Customer row number", 0, len(df) - 1, 0))
        row = df.iloc[idx]
        with st.expander("Raw customer record"):
            st.dataframe(row.astype(str).to_frame("value"))
        p = dict(age=int(row["age"]), job=row["job"], marital=row["marital"],
                 education=row["education"], balance=int(row["balance"]),
                 housing=row["housing"], loan=row["loan"], default=row["default"])
        show(recommend(p), predict(p), p)

with t4:
    st.markdown("""
**Pipeline:** segment (balance in ₹) → life stage (age) → risk profile → eligibility rules →
ranked products → propensity model → Claude Project turns the brief into an RM-style explanation.

**KPI definitions**

| KPI | Definition |
|---|---|
| Affluent + HNI share | Customers with ₹2 lakh+ balance |
| Term-deposit conversion | Share of customers who subscribed in the campaign |
| Loan-eligible | Balance above ₹10,000 and no credit default |
| Avg investment score | 0-100 from balance, housing loan, personal loan, default |
| High-potential | Investment score 60+ and no default |
| Cross-sell ready | Employed, loan-eligible and score 60+ |
| Propensity | Model probability of subscribing, shown against the overall base rate |

**Limitations:** Portuguese-bank dataset, balances converted from euros as a proxy;
segment thresholds and product rules are illustrative, not ICICI's official criteria.
""")