import streamlit as st
import pandas as pd

def table(recos):
    if not isinstance(recos, list) or not recos:
        st.warning("No recommendations to display.")
        return None
    df = pd.json_normalize(recos)
    cols = [c for c in [
        'year','make','model','trim','price','economy.city_mpg','economy.hwy_mpg','economy.mpge','safety.nhtsa_stars','score','rationale'
    ] if c in df.columns]
    if cols:
        df = df[cols]
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False)
    st.download_button("Export CSV", csv, file_name="recommendations.csv")
    return df

def mpg_chart(df):
    if df is None or df.empty:
        return
    mpg_cols = [c for c in ['economy.mpge','economy.hwy_mpg','economy.city_mpg'] if c in df.columns]
    if not mpg_cols:
        st.info("No MPG/MPGe data to chart.")
        return
    label_cols = [c for c in ['make','model','trim','year'] if c in df.columns]
    df = df.copy()
    df['label'] = df[label_cols].astype(str).agg(' '.join, axis=1) if label_cols else range(len(df))
    plot_df = df[['label'] + mpg_cols].set_index('label')
    st.bar_chart(plot_df)
