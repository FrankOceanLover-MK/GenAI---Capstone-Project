import streamlit as st
from .utils import get_car, get_summary, ApiError


def render():
    st.subheader("VIN lookup")
    vin = st.text_input("Enter VIN", placeholder="For example WP0AF2A99KS165242")
    lookup = st.button("Search VIN", type="primary")

    if lookup and not vin.strip():
        st.warning("Please enter a VIN.")
        return None, None

    car = None
    last_vin = None

    if lookup and vin.strip():
        with st.spinner("Fetching car profile..."):
            try:
                car = get_car(vin.strip())
                last_vin = vin.strip()
            except ApiError as e:
                st.error(e.message)
            except Exception:
                st.error("Backend not reachable for VIN lookup.")
                return None, None

        if car:
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Basic info**")
                st.write("VIN", car.get("vin") or "-")
                st.write("Year", car.get("year") or "-")
                st.write("Make", car.get("make") or "-")
                st.write("Model", car.get("model") or "-")
                st.write("Trim", car.get("trim") or "-")
                st.write("Body style", car.get("body_style") or "-")

            with cols[1]:
                st.markdown("**Stats**")
                st.write("Price", car.get("price") or "-")
                st.write("Mileage", car.get("mileage") or "-")
                econ = car.get("economy") or {}
                st.write("City MPG", econ.get("city_mpg") or "-")
                st.write("Highway MPG", econ.get("highway_mpg") or "-")
                st.write("Fuel type", car.get("fuel_type") or "-")
                st.write("Drivetrain", car.get("drivetrain") or "-")
                safety = car.get("safety") or {}
                st.write("Safety", safety.get("nhtsa_stars") or "-")

            if st.button("Explain this car", help="Calls /cars/{vin}/summary"):
                with st.spinner("Generating summary..."):
                    try:
                        summary = get_summary(vin.strip())
                        st.info(summary)
                    except ApiError as e:
                        st.error(e.message)
                    except Exception:
                        st.error("Backend not reachable for summary.")

    return car, last_vin
