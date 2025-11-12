import streamlit as st

def render():
    st.header("Recommendations")
    with st.expander("Filters", expanded=True):
        price_max = st.number_input("Max Price (USD)", min_value=0, value=25000, step=500)
        mpg_min = st.number_input("Min MPG/MPGe", min_value=0, value=30, step=1)
        fuel = st.selectbox("Fuel Type", ["Any","Gasoline","Diesel","Hybrid","Electric","Plug-in Hybrid"], index=0)
        top_k = st.slider("Top K", 1, 10, 5)
    params = {"price_max": price_max, "mpg_min": mpg_min, "top_k": top_k}
    if fuel != "Any":
        params["fuel"] = fuel
    run = st.button("Find Recommendations", type="primary")
    return run, params
