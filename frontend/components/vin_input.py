import streamlit as st
from .utils import get_car, get_summary, ApiError

def render():
    st.header("VIN Lookup")
    vin = st.text_input("Enter VIN", placeholder="e.g., WP0AF2A99KS165242")
    lookup = st.button("Search VIN", type="primary")
    if lookup and not vin.strip():
        st.warning("Please enter a VIN.")
        return None

    car = None
    if lookup and vin.strip():
        with st.spinner("Fetching car profile..."):
            try:
                car = get_car(vin.strip())
            except ApiError as e:
                if e.status == 401:
                    st.error("Unauthorized: check Auto.dev API key in backend `.env`.")
                elif e.status == 429:
                    st.error("Rate limit exceeded. Please try again later.")
                elif e.status == 404:
                    st.error("VIN not found.")
                else:
                    st.error(e.message)
                return None
            except Exception:
                st.error("Could not contact backend. Is it running?")
                return None

        if isinstance(car, dict):
            with st.container(border=True):
                st.subheader(f"{car.get('year','?')} {car.get('make','?')} {car.get('model','?')}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write("**Trim**", car.get("trim") or "–")
                    st.write("**Body**", car.get("body_type") or "–")
                    st.write("**Origin**", car.get("origin") or "–")
                with col2:
                    eng = car.get("engine") or {}
                    st.write("**Engine**", f"{eng.get('displacement_l','–')}L / {eng.get('cylinders','–')} cyl")
                    st.write("**HP**", eng.get("hp") or "–")
                    st.write("**Fuel**", eng.get("fuel_type") or "–")
                with col3:
                    eco = car.get("economy") or {}
                    if eco.get("mpge"):
                        st.write("**MPGe**", eco.get("mpge"))
                    else:
                        st.write("**MPG City/Hwy**", f"{eco.get('city_mpg','–')}/{eco.get('hwy_mpg','–')}")
                    st.write("**Drivetrain**", car.get("drivetrain") or "–")
                    safety = car.get("safety") or {}
                    st.write("**Safety**", safety.get("nhtsa_stars") or "–")

            if st.button("Explain this car", help="Calls /cars/{vin}/summary"):
                with st.spinner("Generating summary..."):
                    try:
                        summary = get_summary(vin.strip())
                        st.info(summary)
                    except ApiError as e:
                        st.error(e.message)
                    except Exception:
                        st.error("Backend not reachable for summary.")
    return car
