import streamlit as st
import pandas as pd


def table(recos):
    if not isinstance(recos, list) or not recos:
        st.warning("No recommendations to display.")
        return None

    df = pd.json_normalize(recos)

    # if we have listing_url, turn it into a clickable link
    if "listing_url" in df.columns:
        df["Listing"] = df["listing_url"].apply(
            lambda url: f"[Open listing]({url})" if isinstance(url, str) else ""
        )

    cols = [c for c in [
        "year","make","model","trim","price","mileage","distance_miles",
        "city_mpg","highway_mpg","safety_rating","Listing"
    ] if c in df.columns]

    if cols:
        df = df[cols]

    st.markdown("**Recommendations**")
    st.dataframe(df, use_container_width=True)
    return df



def mpg_chart(df):
    if df is None or df.empty:
        return

    mpg_cols = [c for c in ["city_mpg", "highway_mpg"] if c in df.columns]
    if not mpg_cols:
        st.info("No MPG data to chart.")
        return

    label_cols = [c for c in ["make", "model", "trim", "year"] if c in df.columns]
    df = df.copy()
    if label_cols:
        df["label"] = df[label_cols].astype(str).agg(" ".join, axis=1)
    else:
        df["label"] = range(len(df))

    plot_df = df[["label"] + mpg_cols].set_index("label")
    st.bar_chart(plot_df)
