import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ---------------------------
# Configuration & Constants
# ---------------------------
DATA_DIR = Path(__file__).parent
FILE_LAKE_FOREST = DATA_DIR / "coste_lake_forest.csv"
FILE_MEMORIAL = DATA_DIR / "cost_memorial.csv"
FILE_DELNOR = DATA_DIR / "cost_delnor.csv"
FILE_DUPAGE = DATA_DIR / "cost_dupage.csv"
FILE_KISH = DATA_DIR / "cost_kishawakee.csv"
FILE_MCHENRY = DATA_DIR / "cost_mchenry.csv"
# Ownership files
FILE_OWNER_LAKE = DATA_DIR / "ownership_lake.csv"
FILE_OWNER_MEM = DATA_DIR / "ownership_memorial.csv"
# Key financial columns to spotlight on the dashboard
METRIC_COLUMNS = {
    "Operating Expense": "less_total_operating_expense",
    "Combined Charges": "combined_outpatient_inpatient_total_charges",
    "Net Patient Revenue": "net_patient_revenue",
    "Net Income": "net_income",
    "Total Assets": "total_assets",
    "Total Liabilities": "total_liabilities",
    "Cash (On Hand & In Banks)": "cash_on_hand_and_in_banks",
    "Net Revenue from Medicaid": "net_revenue_from_medicaid",
}

# Key cost breakdown columns to display as stacked bar
COST_BREAKDOWN_COLUMNS = {
    "Salaries": "total_salaries_from_worksheet_a",
    "Overhead": "overhead_non_salary_costs",
    "Depreciation": "depreciation_cost",
    "Charity Care": "cost_of_charity_care",
    "Bad Debt": "total_bad_debt_expense",
}

# Key revenue/income columns for stacked bar
REVENUE_COLUMNS = {
    "Net Patient Revenue": "net_patient_revenue",
    "Net Revenue from Medicaid": "net_revenue_from_medicaid",
    "Other Income": "total_other_income",
}
# Equipment-related cost / asset columns
EQUIPMENT_COLUMNS = {
    "Fixed Equipment": "fixed_equipment",
    "Major Movable Equipment": "major_movable_equipment",
    "Minor Equipment (Depreciable)": "minor_equipment_depreciable",
    "Health IT Designated Assets": "health_information_technology_designated_assets",
}
# ---------------------------
# Utility Functions
# ---------------------------
@st.cache_data(show_spinner=False)
def load_data():
    """Load financial and ownership data for all hospitals into dictionaries."""

    cost_files = {
        "Northwestern Lake Forest Hospital": FILE_LAKE_FOREST,
        "Northwestern Memorial Hospital": FILE_MEMORIAL,
        "Delnor-Community Hospital": FILE_DELNOR,
        "Central DuPage Hospital": FILE_DUPAGE,
        "Kishwaukee Community Hospital": FILE_KISH,
        "Northern Illinois Medical Center": FILE_MCHENRY,
    }

    ownership_files = {
        "Northwestern Lake Forest Hospital": FILE_OWNER_LAKE,
        "Northwestern Memorial Hospital": FILE_OWNER_MEM,
    }

    cost_dfs: dict[str, pd.DataFrame] = {}
    for hosp_name, path in cost_files.items():
        df = pd.read_csv(path)
        # Type conversions
        for col in METRIC_COLUMNS.values():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in list(COST_BREAKDOWN_COLUMNS.values()) + list(REVENUE_COLUMNS.values()) + list(EQUIPMENT_COLUMNS.values()):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        cost_dfs[hosp_name] = df

    ownership_dfs: dict[str, pd.DataFrame] = {}
    for hosp_name, path in ownership_files.items():
        if path.exists():
            ownership_dfs[hosp_name] = pd.read_csv(path)

    return cost_dfs, ownership_dfs


def financial_metrics_section(df: pd.DataFrame):
    """Render headline financial metrics."""
    metric_items = list(METRIC_COLUMNS.items())
    for start in range(0, len(metric_items), 4):
        row_items = metric_items[start:start + 4]
        cols = st.columns(len(row_items))
        for idx, (label, col_name) in enumerate(row_items):
            if col_name not in df.columns:
                continue
            val = df[col_name].sum()
            val_m = val / 1_000_000  # millions
            cols[idx].metric(label, f"${val_m:,.1f}M")


# ---------------------------
# Expense vs Revenue Chart
# ---------------------------


def expense_vs_revenue_chart(df: pd.DataFrame):
    """Display grouped bar of total expenses vs revenues per year."""
    # Aggregate required columns
    if "less_total_operating_expense" not in df.columns or "net_patient_revenue" not in df.columns:
        st.warning("Necessary columns for expense vs revenue chart are missing.")
        return

    agg_df = (
        df[["Year", "less_total_operating_expense", "net_patient_revenue", "total_other_income"]]
        .groupby("Year")
        .sum()
        .reset_index()
    )

    agg_df["Total Revenue"] = agg_df["net_patient_revenue"] + agg_df.get("total_other_income", 0)
    agg_df.rename(columns={"less_total_operating_expense": "Total Expense"}, inplace=True)

    plot_df = agg_df.melt(id_vars="Year", value_vars=["Total Expense", "Total Revenue"],
                          var_name="Category", value_name="Amount")

    fig = px.bar(
        plot_df,
        x="Year",
        y="Amount",
        color="Category",
        barmode="group",
        title="Revenue vs Expense by Fiscal Year",
        labels={"Amount": "USD", "Year": "Fiscal Year"},
        height=450,
        color_discrete_map={"Total Expense": "#EF553B", "Total Revenue": "#00CC96"},
    )
    fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0f", legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)


def time_series_chart(df: pd.DataFrame, selected_labels: list[str]):
    """Show grouped bar chart for selected metrics per Year."""
    if not selected_labels:
        st.info("Select at least one metric to display the chart.")
        return

    # Prepare data
    metrics_to_plot = {lbl: METRIC_COLUMNS[lbl] for lbl in selected_labels}
    group_df = df[["Year"] + list(metrics_to_plot.values())].groupby("Year").sum().reset_index()
    melted = group_df.melt(id_vars="Year", var_name="Metric", value_name="Value")
    # Map technical column names back to friendly labels
    inv_map = {v: k for k, v in metrics_to_plot.items()}
    melted["Metric"] = melted["Metric"].map(inv_map)

    fig = px.bar(melted, x="Year", y="Value", color="Metric", barmode="group",
                 title="Financial Metrics by Fiscal Year", height=500,
                 labels={"Value": "Amount (USD)", "Year": "Fiscal Year"})
    fig.update_layout(legend_title_text="Metric", yaxis_tickprefix="$", yaxis_tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------
# Ownership Visualisation
# ---------------------------

def ownership_metrics_section(df: pd.DataFrame):
    """Display quick metrics about ownership entities."""
    total = df["associate_id_owner"].nunique()
    individuals = df[df["type_owner"] == "I"]["associate_id_owner"].nunique()
    orgs = df[df["type_owner"] == "O"]["associate_id_owner"].nunique()

    cols = st.columns(3)
    cols[0].metric("Total Unique Owners", f"{total}")
    cols[1].metric("Individuals", f"{individuals}")
    cols[2].metric("Organizations", f"{orgs}")


def ownership_charts(df: pd.DataFrame):
    """Render ownership breakdown charts."""
    st.markdown("#### Ownership Breakdown")

    # Role distribution
    role_counts = df["role_text_owner"].fillna("Unknown").value_counts().reset_index()
    role_counts.columns = ["Role", "Count"]
    fig_role = px.bar(role_counts, x="Role", y="Count", title="Owners by Role")
    fig_role.update_layout(xaxis_title="Role", yaxis_title="Count", height=400)

    # Type distribution
    type_counts = df["type_owner"].fillna("Unknown").value_counts().reset_index()
    type_counts.columns = ["Type", "Count"]
    fig_type = px.pie(type_counts, names="Type", values="Count", hole=0.4, title="Owner Type Composition")

    col1, col2 = st.columns([2, 1])
    col1.plotly_chart(fig_role, use_container_width=True)
    col2.plotly_chart(fig_type, use_container_width=True)

    # Detailed table
    with st.expander("View detailed ownership records"):
        display_cols = [
            "first_name_owner", "middle_name_owner", "last_name_owner",
            "organization_name_owner", "role_text_owner", "association_date_owner",
            "city_owner", "state_owner",
        ]
        st.dataframe(df[display_cols].fillna(""), use_container_width=True, hide_index=True)


def render_tab(df: pd.DataFrame, title: str, ownership_df: pd.DataFrame | None = None, key_prefix: str | None = None):
    """Render the content for a single hospital or combined view."""
    key_prefix = key_prefix or title.replace(" ", "_").lower()
    st.subheader(title)

    # Sidebar-like filters within the tab for cleaner UX
    with st.expander("Filters", expanded=True):
        available_years = sorted(df["Year"].dropna().unique())
        years = st.multiselect(
            "Fiscal Year",
            options=available_years,
            default=available_years,
            key=f"{key_prefix}_year_filter",
        )
        filtered_df = df[df["Year"].isin(years)] if years else df.copy()

    # Key Metrics
    financial_metrics_section(filtered_df)

    # Charts
    st.markdown("---")
    selected_metrics = st.multiselect(
        "Select metrics to visualize by year",
        options=list(METRIC_COLUMNS.keys()),
        default=["Operating Expense", "Combined Charges", "Cash (On Hand & In Banks)", "Net Revenue from Medicaid"],
        key=f"{key_prefix}_metric_selector",
    )
    time_series_chart(filtered_df, selected_metrics)

    # Expense vs Revenue summary
    st.markdown("---")
    expense_vs_revenue_chart(filtered_df)

    # Cost Breakdown Section
    st.markdown("---")
    st.markdown("### Cost Breakdown by Fiscal Year")

    show_breakdown = st.toggle(
        "Show cost breakdown chart",
        value=True,
        key=f"{key_prefix}_show_breakdown",
    )
    if show_breakdown:
        cost_breakdown_chart(filtered_df)

    # Revenue Breakdown Section
    st.markdown("---")
    st.markdown("### Revenue & Income Breakdown by Fiscal Year")

    show_rev = st.toggle(
        "Show revenue breakdown chart",
        value=True,
        key=f"{key_prefix}_show_rev_breakdown",
    )
    if show_rev:
        revenue_breakdown_chart(filtered_df)

    # Equipment Breakdown Section
    st.markdown("---")
    st.markdown("### Equipment & Asset Breakdown by Fiscal Year")

    show_equipment = st.toggle(
        "Show equipment asset breakdown chart",
        value=False,
        key=f"{key_prefix}_show_equipment_breakdown",
    )
    if show_equipment:
        equipment_breakdown_chart(filtered_df)

    # Raw Data preview
    st.markdown("---")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # Ownership section (only if ownership data provided)
    if ownership_df is not None:
        st.markdown("---")
        ownership_metrics_section(ownership_df)
        ownership_charts(ownership_df)


# ---------------------------
# Cost Breakdown Chart
# ---------------------------


def cost_breakdown_chart(df: pd.DataFrame):
    """Render stacked bar chart of cost categories by year."""
    required_cols = [COST_BREAKDOWN_COLUMNS[label] for label in COST_BREAKDOWN_COLUMNS]
    # Filter out columns not present in DF
    present_map = {label: col for label, col in COST_BREAKDOWN_COLUMNS.items() if col in df.columns}
    if not present_map:
        st.warning("No cost breakdown columns available in dataset.")
        return

    total_cost_field = "less_total_operating_expense" if "less_total_operating_expense" in df.columns else "total_costs"
    group_cols = list(present_map.values()) + [total_cost_field]
    group_df = df[["Year"] + group_cols].groupby("Year").sum().reset_index()

    # Compute other costs and ensure non-negative for stacking
    group_df["Other"] = group_df[total_cost_field] - group_df[list(present_map.values())].sum(axis=1)
    group_df["Other"] = group_df["Other"].clip(lower=0)

    # Prepare melt for plotting
    plot_cols = list(present_map.keys()) + ["Other"]
    col_map = {**present_map, "Other": "Other"}
    melted = group_df.melt(id_vars="Year", value_vars=[col_map[label] if label != "Other" else "Other" for label in plot_cols],
                           var_name="Category", value_name="Amount")

    # Map technical names back to labels
    inv_map = {v: k for k, v in present_map.items()}
    melted["Category"] = melted["Category"].map(inv_map).fillna("Other")

    fig = px.bar(
        melted,
        x="Year",
        y="Amount",
        color="Category",
        title="Operating Expense Breakdown",
        labels={"Amount": "USD", "Year": "Fiscal Year"},
        height=500,
    )
    fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0f", legend_title_text="Cost Category")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------
# Revenue Breakdown Chart
# ---------------------------


def revenue_breakdown_chart(df: pd.DataFrame):
    """Render horizontal stacked bar chart of revenue categories by year."""
    present_map = {label: col for label, col in REVENUE_COLUMNS.items() if col in df.columns}
    if not present_map:
        st.warning("No revenue breakdown columns available in dataset.")
        return

    group_df = df[["Year"] + list(present_map.values())].groupby("Year").sum().reset_index()

    melted = group_df.melt(id_vars="Year", var_name="Category", value_name="Amount")
    inv_map = {v: k for k, v in present_map.items()}
    melted["Category"] = melted["Category"].map(inv_map)

    fig = px.bar(
        melted,
        x="Amount",
        y="Year",
        color="Category",
        orientation="h",
        title="Stacked Revenue & Income Breakdown",
        labels={"Amount": "USD", "Year": "Fiscal Year"},
        height=500,
    )
    fig.update_layout(xaxis_tickprefix="$", xaxis_tickformat=",.0f", legend_title_text="Revenue Category")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------
# Equipment Breakdown Chart
# ---------------------------


def equipment_breakdown_chart(df: pd.DataFrame):
    """Render horizontal stacked bar chart of equipment-related asset categories by year."""
    present_map = {label: col for label, col in EQUIPMENT_COLUMNS.items() if col in df.columns}
    if not present_map:
        st.warning("No equipment-related columns available in dataset.")
        return

    group_df = df[["Year"] + list(present_map.values())].groupby("Year").sum().reset_index()

    melted = group_df.melt(id_vars="Year", var_name="Category", value_name="Amount")
    inv_map = {v: k for k, v in present_map.items()}
    melted["Category"] = melted["Category"].map(inv_map)

    fig = px.bar(
        melted,
        x="Amount",
        y="Year",
        color="Category",
        orientation="h",
        title="Equipment & Asset Breakdown",
        labels={"Amount": "USD", "Year": "Fiscal Year"},
        height=500,
    )
    fig.update_layout(xaxis_tickprefix="$", xaxis_tickformat=",.0f", legend_title_text="Equipment Category")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------
# Streamlit Page Settings
# ---------------------------
st.set_page_config(
    page_title="Hospital Cost Report Dashboard",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Northwestern Medicine – Hospital Cost Reports")

# Load Data
cost_dfs, ownership_dfs = load_data()
combined_df = pd.concat(cost_dfs.values(), ignore_index=True)

# Sidebar selector for hospital views
hospital_options = ["Combined – All Hospitals"] + list(cost_dfs.keys())
selected_hospital = st.sidebar.selectbox("Select Hospital", hospital_options)

# Determine dataframe and ownership based on selection
if selected_hospital == "Combined – All Hospitals":
    render_tab(combined_df, selected_hospital, key_prefix="combined")
else:
    df_selected = cost_dfs[selected_hospital]
    own_selected = ownership_dfs.get(selected_hospital)
    slug = selected_hospital.lower().replace(" ", "_")
    render_tab(df_selected, selected_hospital, ownership_df=own_selected, key_prefix=slug) 