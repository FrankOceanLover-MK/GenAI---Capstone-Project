import streamlit as st


def render():
    st.subheader("Find recommendations")
    with st.expander("Filters", expanded=True):
        budget = st.number_input(
            "Maximum price in US dollars",
            min_value=0,
            value=25000,
            step=500,
        )
        max_distance = st.number_input(
            "Maximum distance in miles",
            min_value=0,
            value=50,
            step=5,
            help="Distance from your location if the backend provides it.",
        )
        body_style = st.selectbox(
            "Body style",
            ["Any", "SUV", "Sedan", "Truck", "Coupe", "Hatchback", "Minivan"],
            index=0,
        )
        fuel_type = st.selectbox(
            "Fuel type",
            ["Any", "Gasoline", "Diesel", "Hybrid", "Electric", "Plug in hybrid"],
            index=0,
        )
        top_k = st.slider("Number of results", 1, 10, 5)

    params = {
        "budget": int(budget) if budget else None,
        "max_distance": float(max_distance) if max_distance else None,
        "top_k": int(top_k),
    }
    if body_style != "Any":
        params["body_style"] = body_style.lower()
    if fuel_type != "Any":
        params["fuel_type"] = fuel_type.lower()

    run = st.button("Find recommendations", type="primary")
    return run, params
