import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils.loaders import load_maps

# ───────────────────────────────────────────────────────────────────────────────
# CONFIGURATION: edit paths if your CSVs live elsewhere
# ───────────────────────────────────────────────────────────────────────────────
GENERIC_PATH = "data/unified_df_gen.csv"   # BEN_REG,sexe,age,GEN_NUM,total_boites,1…99
SANOFI_PATH  = "data/unified_df.csv"    # BEN_REG,sexe,age,CIP13,total_boites,1…99

# ───────────────────────────────────────────────────────────────────────────────
# LOAD DICTIONARIES
# ───────────────────────────────────────────────────────────────────────────────
sex_map, age_map, region_map, presc_map, _ = load_maps()

# ───────────────────────────────────────────────────────────────────────────────
# HELPERS: WIDE → LONG TRANSFORM
# ───────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_long(path: str, kind: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    presc_cols = [c for c in df.columns if c.isdigit()]

    # numeric coercion ---------------------------------------------------------
    df["total_boites"] = pd.to_numeric(df["total_boites"], errors="coerce").fillna(0).astype(int)
    for c in presc_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # map code → label ---------------------------------------------------------
    df["Region"]    = df["BEN_REG"].map(region_map).fillna(df["BEN_REG"])
    df["Age Group"] = df["age"].map(age_map).fillna(df["age"])
    df["Gender"]    = df["sexe"].map(sex_map).fillna(df["sexe"])

    # reshape long -------------------------------------------------------------
    long = df.melt(
        id_vars=["Region", "Age Group", "Gender"],
        value_vars=presc_cols,
        var_name="PSP_SPE",
        value_name="Boxes"
    )
    long = long[long["Boxes"] > 0]
    long["Prescriber"] = long["PSP_SPE"].map(presc_map).fillna(long["PSP_SPE"])
    long = long.drop(columns=["PSP_SPE"])

    return long.rename(columns={"Boxes": f"Boxes_{kind.capitalize()}"})

# LOAD BOTH DATASETS ------------------------------------------------------------
long_generic = load_long(GENERIC_PATH, "generic")
long_sanofi  = load_long(SANOFI_PATH,  "sanofi")

# OUTER MERGE TO COMBINE --------------------------------------------------------
long = pd.merge(
    long_generic,
    long_sanofi,
    on=["Region", "Age Group", "Gender", "Prescriber"],
    how="outer"
).fillna(0)

long["Boxes_Total"]   = long["Boxes_Generic"] + long["Boxes_Sanofi"]
long["Sanofi_Share"]  = np.where(long["Boxes_Total"] == 0, 0, long["Boxes_Sanofi"] / long["Boxes_Total"])

# ───────────────────────────────────────────────────────────────────────────────
# STREAMLIT APP
# ───────────────────────────────────────────────────────────────────────────────
st.title("💊 Irbesartan – Sanofi vs Generics")

view = st.radio("View by", ["Region", "Age Group", "Gender", "Prescriber"], horizontal=True)

# AGGREGATION ------------------------------------------------------------------

def aggregate(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    agg = (
        df.groupby(dim)[["Boxes_Generic", "Boxes_Sanofi"]]
          .sum()
          .reset_index()
    )
    agg["Boxes_Total"]  = agg["Boxes_Generic"] + agg["Boxes_Sanofi"]
    total_all = agg["Boxes_Total"].sum()
    agg["Sanofi_Share"] = np.where(agg["Boxes_Total"] == 0, 0, agg["Boxes_Sanofi"] / agg["Boxes_Total"])
    agg["Volume_Share"] = np.where(total_all == 0, 0, agg["Boxes_Total"] / total_all)
    return agg.sort_values("Boxes_Total", ascending=False)

# PLOT -------------------------------------------------------------------------

def plot_volume(df: pd.DataFrame, dim: str):
    melted = df.melt(
        id_vars=[dim, "Sanofi_Share", "Volume_Share"],
        value_vars=["Boxes_Sanofi", "Boxes_Generic"],
        var_name="Product", value_name="Boxes"
    )
    color = alt.Scale(domain=["Boxes_Sanofi", "Boxes_Generic"], range=["#4C78A8", "#E45756"])
    chart = (
        alt.Chart(melted)
        .mark_bar(opacity=0.85)
        .encode(
            x=alt.X(f"{dim}:N", sort="-y"),
            y="Boxes:Q",
            color=alt.Color("Product:N", scale=color, title=None),
            tooltip=[
                dim,
                alt.Tooltip("Boxes:Q", format=","),
                alt.Tooltip("Volume_Share:Q",  title="Volume Share", format=".1%"),
                alt.Tooltip("Sanofi_Share:Q",  title="Sanofi Share", format=".1%")
            ]
        )
        .properties(height=400)
    )
    st.altair_chart(chart, use_container_width=True)

# TABLE RENDER -----------------------------------------------------------------

def display_table(df: pd.DataFrame, dim: str):
    table = df.copy()
    table["Sanofi Share"]  = table["Sanofi_Share"].map("{:.1%}".format)
    table["Volume Share"]  = table["Volume_Share"].map("{:.1%}".format)
    table["Sanofi Boxes"]  = table["Boxes_Sanofi"].map("{:,.0f}".format)
    table["Generic Boxes"] = table["Boxes_Generic"].map("{:,.0f}".format)
    table["Total Boxes"]   = table["Boxes_Total"].map("{:,.0f}".format)
    st.dataframe(
        table[[dim, "Volume Share", "Sanofi Share", "Sanofi Boxes", "Generic Boxes", "Total Boxes" ]],
        hide_index=True,
        use_container_width=True
    )

# FILTERED AGG + UI ------------------------------------------------------------
if view == "Region":
    presc_filter = st.selectbox("Prescriber", ["All"] + sorted(long["Prescriber"].unique()))
    df_view = long if presc_filter == "All" else long[long["Prescriber"] == presc_filter]
    agg = aggregate(df_view, "Region")
    plot_volume(agg, "Region")
    display_table(agg, "Region")

elif view == "Age Group":
    reg_filter = st.selectbox("Region", ["All"] + sorted(long["Region"].unique()))
    df_view = long if reg_filter == "All" else long[long["Region"] == reg_filter]
    agg = aggregate(df_view, "Age Group")
    plot_volume(agg, "Age Group")
    display_table(agg, "Age Group")

elif view == "Gender":
    c1, c2 = st.columns(2)
    with c1:
        reg_filter = st.selectbox("Region", ["All"] + sorted(long["Region"].unique()))
    with c2:
        age_filter = st.selectbox("Age Group", ["All"] + sorted(long["Age Group"].unique()))

    df_view = long.copy()
    if reg_filter != "All":
        df_view = df_view[df_view["Region"] == reg_filter]
    if age_filter != "All":
        df_view = df_view[df_view["Age Group"] == age_filter]
    agg = aggregate(df_view, "Gender")
    plot_volume(agg, "Gender")
    display_table(agg, "Gender")

else:  # Prescriber
    col1, col2, col3 = st.columns(3)
    with col1:
        reg_filter = st.selectbox("Region", ["All"] + sorted(long["Region"].unique()))
    with col2:
        age_filter = st.selectbox("Age Group", ["All"] + sorted(long["Age Group"].unique()))
    with col3:
        gender_filter = st.selectbox("Gender", ["All"] + sorted(long["Gender"].unique()))

    df_view = long.copy()
    if reg_filter != "All":
        df_view = df_view[df_view["Region"] == reg_filter]
    if age_filter != "All":
        df_view = df_view[df_view["Age Group"] == age_filter]
    if gender_filter != "All":
        df_view = df_view[df_view["Gender"] == gender_filter]

    agg = aggregate(df_view, "Prescriber")

    bar = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            y=alt.Y("Prescriber:N", sort="-x"),
            x=alt.X("Boxes_Total:Q", title="Total Boxes"),
            color=alt.value("#4C78A8"),
            tooltip=[
                "Prescriber",
                alt.Tooltip("Boxes_Total:Q", format=","),
                alt.Tooltip("Volume_Share:Q", title="Volume Share", format=".1%"),
                alt.Tooltip("Sanofi_Share:Q", title="Sanofi Share", format=".1%")
            ]
        )
        .properties(height=500)
    )
    st.altair_chart(bar, use_container_width=True)
    display_table(agg, "Prescriber")
