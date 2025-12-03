import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

st.set_page_config(page_title="Canada Home Affordability", layout="wide", page_icon="🏠")

st.title("🏠 Canada Home Affordability Calculator")
st.markdown("**Regional mortgage rules + income distribution + buyer incentives**")

# ===========================================
# REGIONAL MORTGAGE RULES (Update rates here)
# ===========================================
REGIONS = {
    "🇨🇦 National": {"down_payment": 0.05, "rate": 0.045, "first_time": 0.05, "pop": 20_000_000, "incentive": 0.95},
    "🇴🇳 Ontario": {"down_payment": 0.05, "rate": 0.047, "first_time": 0.05, "pop": 15_000_000, "incentive": 0.93},
    "🇧🇨 BC": {"down_payment": 0.05, "rate": 0.049, "first_time": 0.05, "pop": 5_300_000, "incentive": 0.90},
    "🇦🇧 Alberta": {"down_payment": 0.05, "rate": 0.043, "first_time": 0.05, "pop": 4_500_000, "incentive": 1.00},
    "🇶🇨 Quebec": {"down_payment": 0.05, "rate": 0.044, "first_time": 0.03, "pop": 9_000_000, "incentive": 1.00},
    "🇲🇦 Manitoba": {"down_payment": 0.05, "rate": 0.042, "first_time": 0.05, "pop": 1_400_000, "incentive": 1.00}
}

# Income distribution (Canadian log-normal)
mu, sigma = 10.45, 0.95
scale = np.exp(mu)
income_range = np.linspace(1, 400_000, 1000)

def lognorm_pdf(x, s, scale):
    return (1 / (x * s * np.sqrt(2 * np.pi))) * np.exp(-((np.log(x) - np.log(scale))**2) / (2 * s**2))

def lognorm_cdf(x, s, scale):
    z = (np.log(x) - np.log(scale)) / s
    return 0.5 * (1 + np.tanh(np.sqrt(2) * z / 2) + np.sqrt(2/np.pi) * np.exp(-z**2/2))

pdf = lognorm_pdf(income_range, sigma, scale)
cdf = lognorm_cdf(income_range, sigma, scale)

# Mortgage calculator
@st.cache_data
def calculate_max_affordable(price, down_payment_pct, mortgage_rate, amortization=25):
    down_payment = price * down_payment_pct
    loan = price - down_payment
    monthly_rate = mortgage_rate / 12
    n_payments = amortization * 12
    monthly_payment = loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    annual_income_needed = monthly_payment * 12 / 0.28  # 28% TDS ratio
    return annual_income_needed, down_payment

# Main calculator
col1, col2 = st.columns([1, 2])

with col1:
    st.header("🏠 Home Details")
    home_price = st.number_input("**Purchase Price**", 100000, 3000000, 800000, 25000)
    region = st.selectbox("**Region**", list(REGIONS.keys()))
    first_time_buyer = st.checkbox("**First Time Buyer**", True)
    
    region_data = REGIONS[region]
    down_payment_pct = region_data["first_time"] if first_time_buyer else region_data["down_payment"]
    mortgage_rate = region_data["rate"]
    total_pop = region_data["pop"]
    
    max_income, down_payment = calculate_max_affordable(home_price, down_payment_pct, mortgage_rate)
    prob_affordable = 1 - lognorm_cdf(max_income, sigma, scale)
    people_affordable = prob_affordable * total_pop
    percent_affordable = prob_affordable * 100

with col2:
    st.header("✅ Results")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("**Can Afford Home**", f"{people_affordable:,.0f}", f"{percent_affordable:.1f}%")
    with col_b:
        st.metric("**Min Income Needed**", f"${max_income:,.0f}")
    
    st.metric("**Down Payment Required**", f"${down_payment:,.0f}")
    st.caption(f"*{region}: {down_payment_pct*100:.0f}% down, {mortgage_rate*100:.1f}% rate")

# Regional comparison
st.subheader("📊 All Regions Comparison")
if st.button("🔄 Update Comparison", use_container_width=True):
    comparison = []
    for region_name, data in REGIONS.items():
        income_needed, _ = calculate_max_affordable(home_price, data["first_time"], data["rate"])
        prob = 1 - lognorm_cdf(income_needed, sigma, scale)
        comparison.append({
            "Region": region_name,
            "Min Income": f"${income_needed:,.0f}",
            "Can Afford": f"{prob*data['pop']:,.0f}",
            "% of Pop": f"{prob*100:.1f}%"
        })
    
    df = pd.DataFrame(comparison)
    st.dataframe(df, use_container_width=True, hide_index=True)

# Chart
st.subheader("📈 Income Distribution")
fig = go.Figure()
density_scaled = pdf / np.max(pdf) * 40
fig.add_trace(go.Scatter(x=income_range, y=density_scaled, mode='lines',
                        line=dict(color='#1f77b4', width=4), name='Population'))
fig.add_vline(x=max_income, line_dash="dash", line_color="red", 
              annotation_text=f"Need ${max_income:,.0f}+", name="Threshold")
fig.update_layout(height=500, hovermode='x unified', showlegend=True)
fig.update_xaxes(title="Annual Income ($)", tickformat="$,d")
fig.update_yaxes(title="Population Density")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
with st.expander("ℹ️ **Assumptions**"):
    st.write("""
    - **28% TDS ratio** (standard bank qualification)
    - **25-year amortization** (<$1M homes)  
    - **Current posted rates** (update REGIONS dict)
    - **20M working population** (15+ years)
    - **Federal stress test** passed
    """)
