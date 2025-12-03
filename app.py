import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

st.set_page_config(page_title="Canada Home Affordability", layout="wide")

st.title("🏠 Canada Home Affordability Calculator")
st.markdown("**Income distribution + mortgage calculator + regional regulations**")

# Regional data (Federal + Provincial regulations)
REGIONS = {
    "Ontario": {"down_payment": 0.05, "rate": 0.045, "first_time": 0.05, "pop": 15_000_000, "incentive": 0.95},
    "BC": {"down_payment": 0.05, "rate": 0.048, "first_time": 0.05, "pop": 5_300_000, "incentive": 0.90},
    "Alberta": {"down_payment": 0.05, "rate": 0.042, "first_time": 0.05, "pop": 4_500_000, "incentive": 1.00},
    "Quebec": {"down_payment": 0.05, "rate": 0.043, "first_time": 0.03, "pop": 9_000_000, "incentive": 1.00},
    "National": {"down_payment": 0.05, "rate": 0.045, "first_time": 0.05, "pop": 20_000_000, "incentive": 0.95}
}

# Log-normal functions
mu, sigma = 10.45, 0.95
scale = np.exp(mu)
income_range = np.linspace(1, 300_000, 1000)

def lognorm_pdf(x, s, scale):
    return (1 / (x * s * np.sqrt(2 * np.pi))) * np.exp(-((np.log(x) - np.log(scale))**2) / (2 * s**2))

def lognorm_cdf(x, s, scale):
    z = (np.log(x) - np.log(scale)) / s
    return 0.5 * (1 + np.tanh(np.sqrt(2) * z / 2) + np.sqrt(2/np.pi) * np.exp(-z**2/2))

pdf = lognorm_pdf(income_range, sigma, scale)
cdf = lognorm_cdf(income_range, sigma, scale)

# Mortgage calculator
def calculate_max_affordable(price, down_payment_pct, mortgage_rate, amortization=25):
    down_payment = price * down_payment_pct
    loan = price - down_payment
    monthly_rate = mortgage_rate / 12
    n_payments = amortization * 12
    
    # Monthly payment formula
    monthly_payment = loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    
    # Annual income needed (28% housing ratio)
    annual_income_needed = monthly_payment * 12 / 0.28
    return annual_income_needed

# Tabs
tab1, tab2 = st.tabs(["🏠 Home Affordability", "📊 Income Distribution"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Home Details")
        home_price = st.number_input("Purchase Price ($)", 100000, 2000000, 800000, 50000)
        region = st.selectbox("Region", list(REGIONS.keys()))
        first_time_buyer = st.checkbox("First Time Buyer")
        
        region_data = REGIONS[region]
        down_payment_pct = region_data["first_time"] if first_time_buyer else region_data["down_payment"]
        mortgage_rate = region_data["rate"]
        total_pop = region_data["pop"]
        
        st.info(f"**{region}**: {down_payment_pct*100}% down payment, {mortgage_rate*100:.1f}% rate")
    
    with col2:
        st.header("Results")
        max_income_needed = calculate_max_affordable(home_price, down_payment_pct, mortgage_rate)
        
        # People who can afford
        prob_affordable = 1 - lognorm_cdf(max_income_needed, sigma, scale)
        people_affordable = prob_affordable * total_pop
        percent_affordable = prob_affordable * 100
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Can Afford This Home", f"{people_affordable:,.0f}", f"{percent_affordable:.1f}%")
        with col_b:
            st.metric("Min Income Needed", f"${max_income_needed:,.0f}")
        with col_c:
            st.metric("Down Payment", f"${home_price*down_payment_pct:,.0f}")
        
        st.caption(f"**Assumptions**: 28% housing ratio, {25}yr amortization, stress test passed")

with tab2:
    # Original income distribution with affordability line
    st.sidebar.header("Income Range")
    min_income = st.sidebar.slider("Min ($)", 0, 150000, 25000, 5000)
    max_income = st.sidebar.slider("Max ($)", min_income, 300000, 100000, 5000)
    
    prob = lognorm_cdf(max_income, sigma, scale) - lognorm_cdf(min_income, sigma, scale)
    st.metric(f"People in ${min_income:,}-${max_income:,} range", f"{prob*total_pop:,.0f} ({prob*100:.1f}%)")
    
    # Chart with affordability threshold
    fig = make_subplots(rows=1, cols=2, subplot_titles=('📈 Income Distribution', '📊 Cumulative'))
    
    density_scaled = pdf / np.max(pdf) * 30
    fig.add_trace(go.Scatter(x=income_range, y=density_scaled, mode='lines',
                            line=dict(color='#1f77b4', width=4)), row=1, col=1)
    
    # Affordability threshold line
    fig.add_vline(x=max_income_needed if 'max_income_needed' in locals() else 80000, 
                  line_dash="dash", line_color="orange", 
                  annotation_text=f"Afford ${home_price:,}", row=1, col=1)
    
    fig.add_trace(go.Scatter(x=income_range, y=cdf*100, mode='lines',
                            line=dict(color='#2ca02c', width=3)), row=1, col=2)
    
    fig.update_layout(height=500, showlegend=False)
    fig.update_xaxes(title="Income ($)", tickformat="$,d")
    st.plotly_chart(fig, use_container_width=True)

# Regional comparison table
st.subheader("🏛️ Regional Comparison")
if st.button("Compare Regions"):
    comparison_data = []
    for region, data in REGIONS.items():
        income_needed = calculate_max_affordable(home_price, data["first_time"], data["rate"])
        prob = 1 - lognorm_cdf(income_needed, sigma, scale)
        comparison_data.append({
            "Region": region,
            "Min Income Needed": f"${income_needed:,.0f}",
            "Can Afford": f"{prob*data['pop']:,.0f}",
            "% Population": f"{prob*100:.1f}%"
        })
    
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True)

# Key assumptions
with st.expander("ℹ️ Assumptions & Regulations"):
    st.write("""
    **Federal Rules**: 
    - Stress test: Qualify at 5.25% or contract rate + 2%
    - Max amortization: 25 years (<$1M), 30 years (first-time <$800K)
    
    **Provincial Incentives**:
    - Ontario: Land Transfer Tax rebate first-time
    - BC: Property Transfer Tax exemption
    - Quebec: Lower down payment options
    
    **Calculator uses**: 28% TDS ratio, current posted rates
    """)
