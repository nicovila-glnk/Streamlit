import streamlit as st
from utils.loaders import load_unified
import plotly.express as px

# ─── Load data & mappings ───────────────────────────────────────────────────────
df_gen, display_gen, pres_gen = load_unified("data/unified_df_gen.csv", key_col="GEN_NUM")

# ─── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("Filters")
sexes    = sorted(df_gen["Sex"].unique())
ages     = sorted(df_gen["Age"].unique())
regions  = sorted(df_gen["Region"].unique())
generics = sorted(df_gen["Generic"].unique())

selected_sexes   = st.sidebar.multiselect("Sex", sexes, default=[])
selected_ages    = st.sidebar.multiselect("Age Groups", ages, default=[])
selected_regions = st.sidebar.multiselect("Regions", regions, default=[])
selected_gens    = st.sidebar.multiselect("Generics", generics, default=[])

# ─── Reuse the same render() as Medication ───────────────────────────────────────
def render(df, display, pres_list, selected_keys):
    d = df.copy()
    if selected_sexes:   d = d[d["Sex"].isin(selected_sexes)]
    if selected_ages:    d = d[d["Age"].isin(selected_ages)]
    if selected_regions: d = d[d["Region"].isin(selected_regions)]
    if selected_keys:    d = d[d[display].isin(selected_keys)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Boxes",       f"{d['total_boites'].sum():,}")
    c2.metric("Avg Boxes/Script",  f"{d['total_boites'].mean():.1f}")
    c3.metric(f"Unique {display}s", f"{d[display].nunique():,}")

    st.subheader("🌍 Regional Distribution")
    rd = (
        d.groupby("Region")["total_boites"]
         .sum().reset_index()
         .sort_values("total_boites", ascending=True)
    )
    fig = px.bar(rd, x="total_boites", y="Region", orientation="h",
                 color="total_boites", color_continuous_scale="Blues",
                 labels={"total_boites":"Boxes"}, template="plotly_white")
    fig.update_layout(margin=dict(l=120,r=20,t=20,b=20))
    fig.update_traces(hovertemplate="<b>%{y}</b><br>Boxes: %{x:,}<extra></extra>", marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    a1, a2 = st.columns(2)
    with a1:
        ad = d.groupby("Age")["total_boites"].sum().reset_index()
        st.plotly_chart(px.pie(ad, names="Age", values="total_boites", title="By Age"),
                        use_container_width=True)
    with a2:
        sd = d.groupby("Sex")["total_boites"].sum().reset_index()
        st.plotly_chart(px.pie(sd, names="Sex", values="total_boites", title="By Sex"),
                        use_container_width=True)

    st.subheader(f"Breakdown by {display}")
    for k in sorted(d[display].unique()):
        st.markdown(f"### {k}")
        sub = d[d[display] == k]
        dfp = sub[pres_list].sum().reset_index()
        dfp.columns = ["Prescriber", "Boxes"]
        st.plotly_chart(px.pie(dfp, names="Prescriber", values="Boxes", title="By Prescriber"),
                        use_container_width=True)
        reg = sub.groupby("Region")["total_boites"].sum().reset_index()
        st.plotly_chart(px.pie(reg, names="Region", values="total_boites", title="By Region"),
                        use_container_width=True)
        st.markdown("---")

st.title("💊 By Generic")
render(df_gen, display_gen, pres_gen, selected_gens)
