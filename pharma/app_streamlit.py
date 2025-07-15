import streamlit as st
import pandas as pd
import plotly.express as px

# ─── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Prescription Explorer", page_icon="💊", layout="wide")
st.title("💊 Prescription Data Explorer")
st.markdown("Use the sidebar to filter; switch tabs to view by Medication or by Generic.")

# ─── Universal loader for “wide” CSVs ───────────────────────────────────────────
def load_unified(path: str, key_col: str):
    # 1) Read file
    df = pd.read_csv(path, dtype=str)

    # 2) Convert total_boites to int
    df['total_boites'] = (
        pd.to_numeric(df['total_boites'], errors='coerce')
          .fillna(0)
          .astype(int)
    )

    # 2) Identify ALL the prescriber‐breakdown columns (anything not a key)
    key_cols = ['BEN_REG','sexe','age','CIP13','total_boites']
    prescriber_cols = [c for c in df.columns if c not in key_cols]

    # 3) Coerce them to numeric as well
    df[prescriber_cols] = (
        df[prescriber_cols]
        .apply(pd.to_numeric, errors='coerce')
        .fillna(0)
        .astype(int)
    )
    # 3) Load maps
    sex_map = pd.read_csv('sex.csv',   dtype={'Key':str}).set_index('Key')['Value'].to_dict()
    pres_map = pd.read_csv('prescribers.csv', dtype={'Key':str}).set_index('Key')['Value'].to_dict()
    ben_map = pd.read_csv('ben_reg.csv',    dtype={'Key':str}).set_index('Key')['Value'].to_dict()
    age_map = pd.read_csv('age.csv',        dtype={'Key':str}).set_index('Key')['Value'].to_dict()
    cpi_map = pd.read_csv('cpi.csv',        dtype={'Key':str}).set_index('Key')['Value'].to_dict()

    # 4) Map Region / Sex / Age
    df['Region'] = df['BEN_REG'].map(ben_map).fillna(df['BEN_REG'])
    df['Sex']    = df['sexe'].   map(sex_map).fillna(df['sexe'])
    df['Age']    = df['age'].    map(age_map).fillna(df['age'])

    # 5) Rename key column for display
    if key_col == 'GEN_NUM':
        df['Generic'] = df['GEN_NUM']
        display = 'Generic'
    else:
        df['Medication'] = df['CIP13'].map(cpi_map).fillna(df['CIP13'])
        display = 'Medication'

    # 6) Drop raw columns **safely** (ignore if they don’t exist)
    df = df.drop(columns=['BEN_REG','sexe','age','CIP13','GEN_NUM'], errors='ignore')

    # 7) Identify & rename prescriber columns
    core = {'Region','Sex','Age', display, 'total_boites'}
    raw_pres = [c for c in df.columns if c not in core]
    df = df.rename(columns={c: pres_map.get(c, c) for c in raw_pres})
    prescribers = [pres_map.get(c, c) for c in raw_pres]

    return df, display, prescribers

# ─── Load both Medication & Generic tables ─────────────────────────────────────
df_med, display_med, pres_med = load_unified("unified_df.csv",  key_col='CIP13')
df_gen, display_gen, pres_gen = load_unified("unified_df_gen.csv", key_col='GEN_NUM')

# ─── Sidebar filters (unique labels) ───────────────────────────────────────────
st.sidebar.header("Filters")
sexes       = sorted(df_med['Sex'].unique())
ages        = sorted(df_med['Age'].unique())
regions     = sorted(df_med['Region'].unique())
all_pres    = sorted(set(pres_med + pres_gen))
meds        = sorted(df_med['Medication'].unique())
generics    = sorted(df_gen['Generic'].unique())

selected_sexes       = st.sidebar.multiselect("Sex",         sexes,        default=[])
selected_ages        = st.sidebar.multiselect("Age Groups",  ages,         default=[])
selected_regions     = st.sidebar.multiselect("Regions",     regions,      default=[])
# selected_prescribers = st.sidebar.multiselect("Prescribers", all_pres,     default=[])
selected_meds        = st.sidebar.multiselect("Medication",  meds,         default=[])
selected_gens        = st.sidebar.multiselect("Generic",     generics,     default=[])

# ─── Shared renderer ────────────────────────────────────────────────────────────
def render(df: pd.DataFrame, display: str, pres_list: list[str], selected_keys: list[str]):
    # Apply global filters
    d = df.copy()
    if selected_sexes:   d = d[d['Sex'].isin(selected_sexes)]
    if selected_ages:    d = d[d['Age'].isin(selected_ages)]
    if selected_regions: d = d[d['Region'].isin(selected_regions)]
    if selected_keys:    d = d[d[display].isin(selected_keys)]

    # Metrics row
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Boxes",       f"{d['total_boites'].sum():,}")
    c2.metric("Avg Boxes/Script",  f"{d['total_boites'].mean():.1f}")
    c3.metric(f"Unique {display}s", f"{d[display].nunique():,}")

    # Regional bar
    st.subheader("🌍 Regional Distribution")
    rd = (
        d.groupby('Region')['total_boites']
         .sum().reset_index()
         .sort_values('total_boites', ascending=True)
    )
    fig = px.bar(
        rd, x='total_boites', y='Region',
        orientation='h', color='total_boites',
        color_continuous_scale='Blues',
        labels={'total_boites':'Boxes'}, template='plotly_white'
    )
    fig.update_layout(
        margin=dict(l=120, r=20, t=20, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, linecolor='#ccc')
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Boxes: %{x:,}<extra></extra>",
        marker_line_width=0
    )
    st.plotly_chart(
        fig, use_container_width=True, config={'displayModeBar':False},
        key=f"{display}-regional"
    )

    # Age & Sex pies
    a1, a2 = st.columns(2)
    with a1:
        ad = d.groupby('Age')['total_boites'].sum().reset_index()
        st.plotly_chart(
            px.pie(ad, names='Age', values='total_boites', title="By Age"),
            use_container_width=True, key=f"{display}-age"
        )
    with a2:
        sd = d.groupby('Sex')['total_boites'].sum().reset_index()
        st.plotly_chart(
            px.pie(sd, names='Sex', values='total_boites', title="By Sex"),
            use_container_width=True, key=f"{display}-sex"
        )

    # Breakdown by display key
    st.subheader(f"Breakdown by {display}")
    for k in sorted(d[display].unique()):
        st.markdown(f"### {k}")
        sub = d[d[display] == k]

        # By prescriber
        pres_cols = pres_list
        dfp = sub[pres_cols].sum().reset_index()
        dfp.columns = ['Prescriber','Boxes']
        st.plotly_chart(
            px.pie(dfp, names='Prescriber', values='Boxes', title="By Prescriber"),
            use_container_width=True, key=f"{display}-pres-{k}"
        )

        # By region
        reg = sub.groupby('Region')['total_boites'].sum().reset_index()
        st.plotly_chart(
            px.pie(reg, names='Region', values='total_boites', title="By Region"),
            use_container_width=True, key=f"{display}-reg-{k}"
        )
        st.markdown("---")

# ─── Two tabs ─────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["By Medication", "By Generic"])
with tab1:
    render(df_med, display_med, pres_med, selected_meds)
with tab2:
    render(df_gen, display_gen, pres_gen, selected_gens)
