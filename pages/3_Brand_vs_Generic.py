# pages/3_Brand_vs_Generic.py
import streamlit as st
import pandas as pd
import altair as alt
from utils.loaders import load_maps

# ─── Configuration ──────────────────────────────────────────────────────────────
cip_list = ['3400938014792', '3400938014914']  # your two brand CIP13s

# ─── Load code→label maps ───────────────────────────────────────────────────────
sex_map, age_map, region_map, presc_map, cpi_map = load_maps()

# ─── Helper: load & coerce each summary table ───────────────────────────────────
def load_and_prep(path: str, code_col: str, code_map: dict, rename_to: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    # numeric columns
    for c in ["brand_total","generic_total","combined_total","brand_share"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    # generic_share if missing
    if "generic_share" not in df.columns and "generic_total" in df.columns:
        df["generic_share"] = df["generic_total"] / df["combined_total"]
    # map code → label
    df[code_col] = df[code_col].map(code_map).fillna(df[code_col])
    return df.rename(columns={code_col: rename_to})

# ─── Load Region/Age/Gender tables ───────────────────────────────────────────────
reg    = load_and_prep("data/region_summary_metrics.csv",       "BEN_REG", region_map, "Region")
age    = load_and_prep("data/age_summary_metrics.csv",          "age",     age_map,    "Age Group")
gender = load_and_prep("data/gender_summary_metrics.csv",       "sexe",    sex_map,    "Gender")

# ─── Load Prescriber table & map Region for filtering ──────────────────────────
presc  = load_and_prep("data/prescriber_comparison_metrics.csv","PSP_SPE", presc_map, "Prescriber")
presc["Region"] = presc["BEN_REG"].map(region_map).fillna(presc["BEN_REG"])

# ─── Load Generic→CIP13 breakdown ───────────────────────────────────────────────
gp = pd.read_csv("data/generic_products_metrics.csv", dtype=str)
gp["total_boites"] = pd.to_numeric(gp["total_boites"], errors="coerce").fillna(0).astype(int)
gp["Generic"]   = gp["GEN_NUM"].map(cpi_map).fillna(gp["GEN_NUM"])
gp["Product"]   = gp["CIP13"].map(cpi_map).fillna(gp["CIP13"])
gp["share"]     = gp["total_boites"] / gp.groupby("Generic")["total_boites"].transform("sum")
gp["is_ours"]   = gp["CIP13"].isin(cip_list)
gp["Region"]    = gp["BEN_REG"].map(region_map).fillna(gp["BEN_REG"])
gp["Age Group"] = gp["age"].map(age_map).fillna(gp["age"])
gp["Gender"]    = gp["sexe"].map(sex_map).fillna(gp["sexe"])

# ─── Streamlit page ─────────────────────────────────────────────────────────────
st.title("💊 Brand vs Generic Comparison")

view = st.selectbox("Select dimension",
    ["Region","Age Group","Gender","Prescriber","Generic Products Detail"]
)

# ─── Volume, Share & Diff for Region/Age/Gender ────────────────────────────────
def plot_volume(df, dim):
    m = df.melt(
        id_vars=[dim, "combined_total","brand_share","generic_share"],
        value_vars=["brand_total","generic_total"],
        var_name="Product Type", value_name="Boxes"
    )
    chart = alt.Chart(m).mark_bar(opacity=0.8).encode(
        x=alt.X(f"{dim}:N", title=dim),
        y=alt.Y("Boxes:Q", title="Boxes"),
        color=alt.Color("Product Type:N", title=None,
                        scale=alt.Scale(domain=["brand_total","generic_total"],
                                        range=["#4C78A8","#E45756"])),
        tooltip=[
            dim, "Product Type", "Boxes",
            alt.Tooltip("brand_share:Q",   title="Brand share",  format=".1%"),
            alt.Tooltip("generic_share:Q", title="Generic share",format=".1%")
        ]
    ).properties(height=350)
    st.subheader(f"📊 Volume by {dim}")
    st.altair_chart(chart, use_container_width=True)

def plot_share(df, dim):
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X(f"{dim}:N", title=dim),
        y=alt.Y("brand_share:Q", title="Brand share", axis=alt.Axis(format=".1%")),
        tooltip=[
            dim,
            alt.Tooltip("brand_share:Q",   title="Brand share",  format=".1%"),
            alt.Tooltip("generic_share:Q", title="Generic share",format=".1%")
        ]
    ).properties(height=300)
    st.subheader(f"📈 Brand Share by {dim}")
    st.altair_chart(chart, use_container_width=True)

def plot_diff(df, dim):
    d = df.copy().assign(diff=(df["brand_total"]-df["generic_total"])/df["combined_total"])
    chart = alt.Chart(d).mark_bar().encode(
        y=alt.Y(f"{dim}:N", sort="-x", title=dim),
        x=alt.X("diff:Q", title="Δ Brand–Generic share", axis=alt.Axis(format=".1%")),
        color=alt.condition("datum.diff>0", alt.value("#4C78A8"), alt.value("#E45756")),
        tooltip=[
            dim,
            alt.Tooltip("diff:Q",         title="Δ share",      format=".1%"),
            alt.Tooltip("brand_share:Q",  title="Brand share",  format=".1%"),
            alt.Tooltip("generic_share:Q",title="Generic share",format=".1%")
        ]
    ).properties(height=400)
    st.subheader(f"🔀 Share Difference by {dim}")
    st.altair_chart(chart, use_container_width=True)

if view == "Region":
    # Add prescriber type filter
    prescriber_types = ["All"] + sorted(presc["Prescriber"].unique())
    selected_prescriber = st.selectbox("Filter by Prescriber Type", prescriber_types)
    
    # Filter data based on prescriber selection
    if selected_prescriber != "All":
        filtered_reg = reg.copy()
        # Get the filtered data from prescriber data
        filtered_presc = presc[presc["Prescriber"] == selected_prescriber]
        # Filter region data based on the filtered prescriber data
        filtered_reg = filtered_reg[filtered_reg["Region"].isin(filtered_presc["Region"].unique())]
        # Recalculate totals and shares
        filtered_reg["brand_total"] = filtered_reg["Region"].map(
            filtered_presc.groupby("Region")["brand_total"].sum()
        ).fillna(0)
        filtered_reg["generic_total"] = filtered_reg["Region"].map(
            filtered_presc.groupby("Region")["generic_total"].sum()
        ).fillna(0)
        filtered_reg["combined_total"] = filtered_reg["brand_total"] + filtered_reg["generic_total"]
        filtered_reg["brand_share"] = filtered_reg["brand_total"] / filtered_reg["combined_total"]
        filtered_reg["generic_share"] = filtered_reg["generic_total"] / filtered_reg["combined_total"]
        reg = filtered_reg

    plot_volume(reg,    "Region")
    plot_share(reg,     "Region")
    plot_diff(reg,      "Region")
    
    # Region table
    st.subheader("📋 Region Performance Table")
    display_data = reg.copy()
    display_data = display_data.sort_values("brand_share", ascending=False)
    display_data["Market Share"] = display_data["brand_share"].map("{:.1%}".format)
    display_data["Brand Boxes"] = display_data["brand_total"].map("{:,.0f}".format)
    display_data["Generic Boxes"] = display_data["generic_total"].map("{:,.0f}".format)
    display_data["Total Boxes"] = display_data["combined_total"].map("{:,.0f}".format)
    
    display_data = display_data[[
        "Region",
        "Market Share",
        "Brand Boxes",
        "Generic Boxes",
        "Total Boxes"
    ]]
    
    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True
    )

elif view == "Age Group":
    plot_volume(age,    "Age Group")
    plot_share(age,     "Age Group")
    plot_diff(age,      "Age Group")
    
    # Age Group table
    st.subheader("📋 Age Group Performance Table")
    display_data = age.copy()
    display_data = display_data.sort_values("brand_share", ascending=False)
    display_data["Market Share"] = display_data["brand_share"].map("{:.1%}".format)
    display_data["Brand Boxes"] = display_data["brand_total"].map("{:,.0f}".format)
    display_data["Generic Boxes"] = display_data["generic_total"].map("{:,.0f}".format)
    display_data["Total Boxes"] = display_data["combined_total"].map("{:,.0f}".format)
    
    display_data = display_data[[
        "Age Group",
        "Market Share",
        "Brand Boxes",
        "Generic Boxes",
        "Total Boxes"
    ]]
    
    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True
    )

elif view == "Gender":
    plot_volume(gender, "Gender")
    plot_share(gender,  "Gender")
    plot_diff(gender,   "Gender")
    
    # Gender table
    st.subheader("📋 Gender Performance Table")
    display_data = gender.copy()
    display_data = display_data.sort_values("brand_share", ascending=False)
    display_data["Market Share"] = display_data["brand_share"].map("{:.1%}".format)
    display_data["Brand Boxes"] = display_data["brand_total"].map("{:,.0f}".format)
    display_data["Generic Boxes"] = display_data["generic_total"].map("{:,.0f}".format)
    display_data["Total Boxes"] = display_data["combined_total"].map("{:,.0f}".format)
    
    display_data = display_data[[
        "Gender",
        "Market Share",
        "Brand Boxes",
        "Generic Boxes",
        "Total Boxes"
    ]]
    
    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True
    )

# ─── PRESCRIBER: separate share computations ────────────────────────────────────
elif view == "Prescriber":
    # ─── Filters for aggregation ────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        regions = ["All"] + sorted(presc["Region"].unique())
        sel_reg = st.selectbox("Filter by Region", regions)
    with col2:
        ages = ["All"] + sorted(presc["age"].unique())
        sel_age = st.selectbox("Filter by Age Group", ages)
    with col3:
        genders = ["All"] + sorted(presc["sexe"].unique())
        sel_gender = st.selectbox("Filter by Gender", genders)

    # Apply filters
    df_presc = presc.copy()
    if sel_reg != "All":
        df_presc = df_presc[df_presc["Region"] == sel_reg]
    if sel_age != "All":
        df_presc = df_presc[df_presc["age"] == sel_age]
    if sel_gender != "All":
        df_presc = df_presc[df_presc["sexe"] == sel_gender]

    # Aggregate data by prescriber
    agg_data = df_presc.groupby("Prescriber").agg({
        "brand_total": "sum",
        "generic_total": "sum",
        "combined_total": "sum"
    }).reset_index()

    # Calculate market share
    agg_data["market_share"] = agg_data["brand_total"] / agg_data["combined_total"]

    # Display aggregated results
    st.subheader("📊 Prescriber Performance")
    
    # Volume chart
    m = agg_data.melt(
        id_vars=["Prescriber", "market_share"],
        value_vars=["brand_total", "generic_total"],
        var_name="Product Type",
        value_name="Boxes"
    )
    
    chart = alt.Chart(m).mark_bar(opacity=0.8).encode(
        x=alt.X("Prescriber:N", title="Prescriber", sort="-y"),
        y=alt.Y("Boxes:Q", title="Boxes"),
        color=alt.Color("Product Type:N", title=None,
                       scale=alt.Scale(domain=["brand_total", "generic_total"],
                                     range=["#4C78A8", "#E45756"])),
        tooltip=[
            "Prescriber",
            "Product Type",
            "Boxes",
            alt.Tooltip("market_share:Q", title="Market Share", format=".1%")
        ]
    ).properties(height=400)
    
    st.altair_chart(chart, use_container_width=True)

    # Market share chart
    share_chart = alt.Chart(agg_data).mark_bar().encode(
        y=alt.Y("Prescriber:N", sort="-x", title="Prescriber"),
        x=alt.X("market_share:Q", title="Market Share", axis=alt.Axis(format=".1%")),
        color=alt.condition("datum.market_share>0", alt.value("#4C78A8"), alt.value("#E45756")),
        tooltip=[
            "Prescriber",
            alt.Tooltip("market_share:Q", title="Market Share", format=".1%"),
            alt.Tooltip("brand_total:Q", title="Brand Boxes"),
            alt.Tooltip("combined_total:Q", title="Total Boxes")
        ]
    ).properties(height=500)
    
    st.subheader("📈 Market Share by Prescriber")
    st.altair_chart(share_chart, use_container_width=True)

    # Summary statistics
    st.subheader("📋 Summary Statistics")
    total_brand = agg_data["brand_total"].sum()
    total_combined = agg_data["combined_total"].sum()
    overall_share = total_brand / total_combined if total_combined > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Brand Boxes", f"{total_brand:,.0f}")
    with col2:
        st.metric("Total Combined Boxes", f"{total_combined:,.0f}")
    with col3:
        st.metric("Overall Market Share", f"{overall_share:.1%}")

    # Table view of aggregated data
    st.subheader("📋 Detailed Prescriber Data")
    
    # Format the data for display
    display_data = agg_data.copy()
    display_data = display_data.sort_values("market_share", ascending=False)
    display_data["Market Share"] = display_data["market_share"].map("{:.1%}".format)
    display_data["Brand Boxes"] = display_data["brand_total"].map("{:,.0f}".format)
    display_data["Generic Boxes"] = display_data["generic_total"].map("{:,.0f}".format)
    display_data["Total Boxes"] = display_data["combined_total"].map("{:,.0f}".format)
    
    # Select columns to display and rename them
    display_data = display_data[[
        "Prescriber",
        "Market Share",
        "Brand Boxes",
        "Generic Boxes",
        "Total Boxes"
    ]]
    
    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True
    )

else:  # Generic Products Detail
    st.subheader("🔍 Detailed Generic‐CIP Breakdown")

    # filters
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_generic = st.selectbox("Generic group", sorted(gp["Generic"].unique()))
    with c2:
        sel_region = st.selectbox("Region", sorted(gp["Region"].unique()))
    with c3:
        sel_age = st.selectbox("Age group", sorted(gp["Age Group"].unique()))
    with c4:
        sel_gender = st.selectbox("Gender", sorted(gp["Gender"].unique()))

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
