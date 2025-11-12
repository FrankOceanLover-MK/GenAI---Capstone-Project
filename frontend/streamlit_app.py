import streamlit as st
from components.vin_input import render as render_vin
from components.filters import render as render_filters
from components.charts import table as render_table, mpg_chart
from components.utils import try_recommendations, openapi_has_recommendations, ApiError, DEFAULT_BASE, health

st.set_page_config(page_title="Carwise AI", layout="wide" )

st.sidebar.title("Backend")
st.sidebar.write(f"Base URL: **{DEFAULT_BASE}**")
try:
    h = health()
    st.sidebar.success("Backend: OK") 
    if isinstance(h, dict) and h.get("mode"):
        st.sidebar.write(f"Mode: {h['mode']}")
except Exception:
    st.sidebar.error("Backend not reachable.")

st.title("Carwise AI — Demo UI")

car = render_vin()

st.divider()

if openapi_has_recommendations():
    run, params = render_filters()
    if run:
        with st.spinner("Fetching recommendations..."):
            try:
                path, data = try_recommendations(params)
                if isinstance(data, list) and data:
                    df = render_table(data)
                    mpg_chart(df)
                else:
                    st.warning("No recommendations returned.")
            except ApiError as e:
                st.error(e.message)
            except Exception:
                st.error("Failed to contact recommendations endpoint.")
else:
    st.info("Recommendations endpoint not available on backend yet. This panel will enable automatically once implemented.")
