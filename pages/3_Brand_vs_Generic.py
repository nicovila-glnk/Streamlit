# pages/3_Brand_vs_Generic.py
import streamlit as st
import pandas as pd
import altair as alt
from utils.loaders import load_maps

# ─── Configuration ──────────────────────────────────────────────────────────────
# the two company CIP13 codes
cip_list = ['3400938014792', '3400938014914']

# ─── Load maps ──────────────────────────────────────────────────────────────────
sex_map, age_map, region_map, presc_map, cpi_map = load_maps()

# ─── Helper to load & prep summary tables ────────────────────────────────────────
def load_and_prep(path: str, code_col: str, code_map: dict, rename_to: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    # coerce numeric
    for c in ["brand_total", "generic_total", "combined_total", "brand_share"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    # compute generic_share if absent
    if "generic_share" not in df.columns and "generic_total" in df.columns:
        df["generic_share"] = df["generic_total"] / df["combined_total"]
    # map code → label
    df[code_col] = df[code_col].map(code_map).fillna(df[code_col])
    # rename code column
    return df.rename(columns={code_col: rename_to})

# ─── Load & prep each dimension ─────────────────────────────────────────────────
reg    = load_and_prep("data/region_summary_metrics.csv",       "BEN_REG",   region_map,   "Region")
age    = load_and_prep("data/age_summary_metrics.csv",          "age",       age_map,      "Age Group")
gender = load_and_prep("data/gender_summary_metrics.csv",       "sexe",      sex_map,      "Gender")
presc  = load_and_prep("data/prescriber_comparison_metrics.csv","PSP_SPE",   presc_map,    "Prescriber")

# ─── Load & prep CIP13 breakdown of generics ────────────────────────────────────
gp = pd.read_csv("data/generic_products_metrics.csv", dtype=str)
gp["total_boites"] = pd.to_numeric(gp["total_boites"], errors="coerce").fillna(0).astype(int)
gp["Generic"]     = gp["GEN_NUM"].map(cpi_map).fillna(gp["GEN_NUM"])
gp["Product"]     = gp["CIP13"].map(cpi_map).   fillna(gp["CIP13"])
# compute share within each generic group
gp["share"]       = gp["total_boites"] / gp.groupby("Generic")["total_boites"].transform("sum")
gp["is_ours"]     = gp["CIP13"].isin(cip_list)
# map demographics for filtering
gp["Region"]      = gp["BEN_REG"].map(region_map).fillna(gp["BEN_REG"])
gp["Age Group"]   = gp["age"].    map(age_map).   fillna(gp["age"])
gp["Gender"]      = gp["sexe"].   map(sex_map).   fillna(gp["sexe"])

# ─── Page UI ────────────────────────────────────────────────────────────────────
st.title("💊 Brand vs Generic Comparison")

view = st.selectbox(
    "Select dimension",
    ["Region", "Age Group", "Gender", "Prescriber", "Generic Products Detail"]
)

# ─── Volume plot for region/age/gender ──────────────────────────────────────────
def plot_volume(df: pd.DataFrame, dim: str):
    m = df.melt(
        id_vars=[dim, "combined_total", "brand_share", "generic_share"],
        value_vars=["brand_total", "generic_total"],
        var_name="Product Type",
        value_name="Boxes"
    )
    chart = (
        alt.Chart(m)
        .mark_bar(opacity=0.8)
        .encode(
            x=alt.X(f"{dim}:N", title=dim),
            y=alt.Y("Boxes:Q", title="Boxes"),
            color=alt.Color("Product Type:N", title=None,
                            scale=alt.Scale(domain=["brand_total","generic_total"],
                                            range=["#4C78A8","#E45756"])),
            tooltip=[
                dim,
                "Product Type",
                "Boxes",
                alt.Tooltip("brand_share:Q",   title="Brand share",  format=".1%"),
                alt.Tooltip("generic_share:Q", title="Generic share", format=".1%")
            ]
        )
        .properties(height=350)
    )
    st.subheader(f"📊 Volume by {dim}")
    st.altair_chart(chart, use_container_width=True)

# ─── Share line plot ────────────────────────────────────────────────────────────
def plot_share(df: pd.DataFrame, dim: str):
    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{dim}:N", title=dim),
            y=alt.Y("brand_share:Q", title="Brand share", axis=alt.Axis(format=".1%")),
            tooltip=[
                dim,
                alt.Tooltip("brand_share:Q",   title="Brand share",  format=".1%"),
                alt.Tooltip("generic_share:Q", title="Generic share", format=".1%")
            ]
        )
        .properties(height=300)
    )
    st.subheader(f"📈 Brand Share by {dim}")
    st.altair_chart(chart, use_container_width=True)

# ─── Share difference plot ──────────────────────────────────────────────────────
def plot_diff(df: pd.DataFrame, dim: str):
    d = df.copy().assign(diff=(df["brand_total"] - df["generic_total"]) / df["combined_total"])
    chart = (
        alt.Chart(d)
        .mark_bar()
        .encode(
            y=alt.Y(f"{dim}:N", sort="-x", title=dim),
            x=alt.X("diff:Q", title="Δ Brand–Generic share", axis=alt.Axis(format=".1%")),
            color=alt.condition("datum.diff>0", alt.value("#4C78A8"), alt.value("#E45756")),
            tooltip=[
                dim,
                alt.Tooltip("diff:Q",         title="Δ share",      format=".1%"),
                alt.Tooltip("brand_share:Q",  title="Brand share",  format=".1%"),
                alt.Tooltip("generic_share:Q",title="Generic share",format=".1%")
            ]
        )
        .properties(height=400)
    )
    st.subheader(f"🔀 Share Difference by {dim}")
    st.altair_chart(chart, use_container_width=True)

# ─── Render based on selected view ───────────────────────────────────────────────
if view == "Region":
    plot_volume(reg,   "Region")
    plot_share(reg,    "Region")
    plot_diff(reg,     "Region")

elif view == "Age Group":
    plot_volume(age,   "Age Group")
    plot_share(age,    "Age Group")
    plot_diff(age,     "Age Group")

elif view == "Gender":
    plot_volume(gender,"Gender")
    plot_share(gender, "Gender")
    plot_diff(gender,  "Gender")

elif view == "Prescriber":
    st.subheader("📊 Brand vs Generic by Prescriber")
    bubble = (
        alt.Chart(presc)
        .mark_circle(opacity=0.7)
        .encode(
            x=alt.X("generic_total:Q", title="Generic boxes"),
            y=alt.Y("brand_total:Q",   title="Brand boxes"),
            size=alt.Size("combined_total:Q", title="Total volume"),
            color=alt.Color("brand_share:Q", title="Brand share", scale=alt.Scale(scheme="blues")),
            tooltip=[
                "Prescriber",
                alt.Tooltip("brand_share:Q",   title="Brand share",  format=".1%"),
                alt.Tooltip("generic_share:Q", title="Generic share",format=".1%"),
                "brand_total", "generic_total", "combined_total"
            ]
        )
        .interactive()
        .properties(height=500)
    )
    st.altair_chart(bubble, use_container_width=True)
    plot_diff(presc, "Prescriber")

else:  # Generic Products Detail
    st.subheader("🔍 Detailed Generic‐CIP Breakdown")

    # filters
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_generic = st.selectbox("Generic group", sorted(gp["Generic"].unique()))
    with c2:
        sel_region  = st.selectbox("Region", sorted(gp["Region"].unique()))
    with c3:
        sel_age     = st.selectbox("Age group", sorted(gp["Age Group"].unique()))
    with c4:
        sel_gender  = st.selectbox("Gender", sorted(gp["Gender"].unique()))

    sub = gp[
        (gp["Generic"]   == sel_generic) &
        (gp["Region"]    == sel_region ) &
        (gp["Age Group"] == sel_age    ) &
        (gp["Gender"]    == sel_gender )
    ]

    # Top 5 by volume
    st.markdown("### Top 5 CIP13 by Volume")
    top5 = sub.nlargest(5, "total_boites")
    bar = (
        alt.Chart(top5)
        .mark_bar()
        .encode(
            y=alt.Y("Product:N", sort="-x", title="Product"),
            x=alt.X("total_boites:Q", title="Boxes"),
            color=alt.condition("datum.is_ours", alt.value("#4C78A8"), alt.value("#ccc")),
            tooltip=[
                "Product",
                alt.Tooltip("total_boites:Q", title="Boxes", format=","),
                alt.Tooltip("share:Q",         title="Share",  format=".1%")
            ]
        )
        .properties(height=350)
    )
    st.altair_chart(bar, use_container_width=True)

    # Our products in top 5
    ours = top5[top5["is_ours"]]
    if not ours.empty:
        st.markdown("#### Our Products in Top 5")
        st.table(
            ours[["Product","total_boites","share"]]
               .rename(columns={"total_boites":"Boxes","share":"Share"})
               .assign(Share=lambda df: df["Share"].map("{:.1%}".format))
        )
    else:
        st.info("None of our two CIP13 are in the top 5 for this slice.")

    # Full share distribution
    st.markdown("### All Products Share")
    share = (
        alt.Chart(sub)
        .mark_bar()
        .encode(
            y=alt.Y("Product:N", sort="-x", title=None),
            x=alt.X("share:Q", title="Share", axis=alt.Axis(format=".1%")),
            color=alt.condition("datum.is_ours", alt.value("#4C78A8"), alt.value("#ccc")),
            tooltip=[
                "Product",
                alt.Tooltip("total_boites:Q", title="Boxes", format=","),
                alt.Tooltip("share:Q",         title="Share",  format=".1%")
            ]
        )
        .properties(height=500)
    )
    st.altair_chart(share, use_container_width=True)
