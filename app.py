
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Nassau Candy | Shipping Optimization",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent

# ============================================================
# 2. DASHBOARD STYLING
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    [data-testid="stMetric"] {
        border: 1px solid rgba(100,130,180,0.25);
        padding: 16px;
        border-radius: 12px;
    }

    .hero {
        padding: 28px;
        border-radius: 16px;
        background: linear-gradient(120deg, #172554, #1d4ed8, #38bdf8);
        color: white;
        margin-bottom: 20px;
    }

    .hero h1 {
        color: white;
        margin: 0;
    }

    .hero p {
        color: #e0f2fe;
        margin-bottom: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>🍬 Nassau Candy</h1>
        <p>Distributor Factory Reallocation & Shipping Optimization</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write(
    "Analyze sales, products, factory assignments, shipping distances, "
    "and potential factory reallocation opportunities."
)

# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def first_existing(df, candidates):
    """Return the original column name matching a candidate."""

    if df is None or not hasattr(df, "columns"):
        return None

    column_map = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in column_map:
            return column_map[key]

    return None


def numeric_series(df, column):
    """Convert a column to numeric values safely."""

    if column is None or column not in df.columns:
        return pd.Series(0.0, index=df.index)

    return pd.to_numeric(
        df[column], errors="coerce"
    ).fillna(0)


def load_csv(uploaded_file, filename):
    """Load an uploaded CSV or a CSV stored beside app.py."""

    try:
        if uploaded_file is not None:
            return pd.read_csv(uploaded_file)

        file_path = ROOT / filename

        if file_path.exists():
            return pd.read_csv(file_path)

        return None

    except Exception as error:
        st.error(f"Could not load {filename}: {error}")
        return None


def money(value):
    return f"${value:,.2f}"


# ============================================================
# 4. LOAD PROJECT DATA
# ============================================================

with st.sidebar:
    st.header("📂 Project Data")

    st.caption(
        "Upload your analysis CSV files or keep them "
        "in the same folder as app.py."
    )

    orders_upload = st.file_uploader(
        "Orders CSV",
        type=["csv"],
        key="orders",
    )

    scenarios_upload = st.file_uploader(
        "Priority Scenarios CSV",
        type=["csv"],
        key="scenarios",
    )

    distance_upload = st.file_uploader(
        "Distance Analysis CSV",
        type=["csv"],
        key="distance",
    )

orders = load_csv(
    orders_upload,
    "factory_orders.csv",
)

scenarios = load_csv(
    scenarios_upload,
    "priority_scenarios.csv",
)

distances = load_csv(
    distance_upload,
    "distance_analysis.csv",
)

if orders is None:
    st.warning(
        "Please upload factory_orders.csv using the sidebar. "
        "You can download it from your Google Colab notebook."
    )

    st.info(
        "The other two CSV files are optional. "
        "The dashboard can start with factory_orders.csv alone."
    )

    st.stop()

if orders.empty:
    st.error("The orders CSV contains no data rows.")
    st.stop()

# ============================================================
# 5. IDENTIFY COLUMNS SAFELY
# ============================================================

factory_col = first_existing(
    orders,
    ["Factory", "Current Factory", "Assigned Factory"],
)

product_col = first_existing(
    orders,
    ["Product Name", "Product", "Product_Name"],
)

sales_col = first_existing(
    orders,
    ["Sales", "Total Sales"],
)

units_col = first_existing(
    orders,
    ["Units", "Quantity", "Order Quantity"],
)

profit_col = first_existing(
    orders,
    ["Gross Profit", "Profit", "Gross_Profit"],
)

cost_col = first_existing(
    orders,
    ["Cost", "Total Cost"],
)

city_col = first_existing(
    orders,
    ["City"],
)

state_col = first_existing(
    orders,
    ["State/Province", "State", "Province"],
)

order_date_col = first_existing(
    orders,
    ["Order Date", "Order_Date"],
)

ship_date_col = first_existing(
    orders,
    ["Ship Date", "Ship_Date"],
)

# ============================================================
# 6. SIDEBAR FILTERS
# ============================================================

filtered = orders.copy()

with st.sidebar:
    st.divider()
    st.header("🎛️ Dashboard Filters")

    if factory_col:
        factory_options = sorted(
            filtered[factory_col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_factories = st.multiselect(
            "Select factories",
            factory_options,
            default=factory_options,
        )

        filtered = filtered[
            filtered[factory_col]
            .astype(str)
            .isin(selected_factories)
        ]

    if product_col:
        product_options = sorted(
            filtered[product_col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_products = st.multiselect(
            "Select products",
            product_options,
            default=product_options,
        )

        filtered = filtered[
            filtered[product_col]
            .astype(str)
            .isin(selected_products)
        ]

    if state_col:
        state_options = sorted(
            filtered[state_col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_states = st.multiselect(
            "Select states / provinces",
            state_options,
            default=state_options,
        )

        filtered = filtered[
            filtered[state_col]
            .astype(str)
            .isin(selected_states)
        ]

# ============================================================
# 7. CALCULATE KPIs
# ============================================================

sales = numeric_series(filtered, sales_col)
units = numeric_series(filtered, units_col)
profit = numeric_series(filtered, profit_col)
cost = numeric_series(filtered, cost_col)

factory_count = (
    filtered[factory_col].nunique()
    if factory_col
    else 0
)

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Order Rows",
    f"{len(filtered):,}",
)

k2.metric(
    "Total Sales",
    money(sales.sum()),
)

k3.metric(
    "Total Units",
    f"{units.sum():,.0f}",
)

k4.metric(
    "Gross Profit",
    money(profit.sum()) if profit_col else "N/A",
)

k5.metric(
    "Factories",
    f"{factory_count:,}",
)

# ============================================================
# 8. DASHBOARD TABS
# ============================================================

(
    overview_tab,
    product_tab,
    factory_tab,
    shipping_tab,
    scenario_tab,
    quality_tab,
) = st.tabs(
    [
        "📊 Overview",
        "🍭 Products",
        "🏭 Factories",
        "🚚 Shipping Analysis",
        "💡 Recommendations",
        "🧹 Data Quality",
    ]
)

# ============================================================
# 9. OVERVIEW
# ============================================================

with overview_tab:
    st.subheader("Business Overview")

    left, right = st.columns(2)

    with left:
        st.markdown("#### Sales by Factory")

        if factory_col and sales_col:
            chart_df = filtered.copy()
            chart_df["_sales"] = numeric_series(
                chart_df, sales_col
            )

            chart_df = (
                chart_df.groupby(
                    factory_col,
                    dropna=False,
                    as_index=False,
                )["_sales"]
                .sum()
                .sort_values("_sales", ascending=False)
            )

            fig = px.bar(
                chart_df,
                x=factory_col,
                y="_sales",
                color=factory_col,
                title="Total Sales by Factory",
                labels={
                    factory_col: "Factory",
                    "_sales": "Sales ($)",
                },
            )

            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Factory and Sales columns are required.")

    with right:
        st.markdown("#### Units by Factory")

        if factory_col and units_col:
            chart_df = filtered.copy()
            chart_df["_units"] = numeric_series(
                chart_df, units_col
            )

            chart_df = (
                chart_df.groupby(
                    factory_col,
                    dropna=False,
                    as_index=False,
                )["_units"]
                .sum()
                .sort_values("_units", ascending=False)
            )

            fig = px.bar(
                chart_df,
                x=factory_col,
                y="_units",
                color=factory_col,
                title="Units by Factory",
                labels={
                    factory_col: "Factory",
                    "_units": "Units",
                },
            )

            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Factory and Units columns are required.")

    st.markdown("#### Orders Dataset Preview")

    st.dataframe(
        filtered.head(100),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Showing up to 100 of {len(filtered):,} filtered rows."
    )

# ============================================================
# 10. PRODUCT ANALYSIS
# ============================================================

with product_tab:
    st.subheader("Product Performance")

    if product_col:
        product_data = filtered.copy()

        product_data["_sales"] = numeric_series(
            product_data, sales_col
        )

        product_data["_units"] = numeric_series(
            product_data, units_col
        )

        product_data["_profit"] = numeric_series(
            product_data, profit_col
        )

        aggregations = {
            "Order Rows": (product_col, "size"),
            "Sales": ("_sales", "sum"),
            "Units": ("_units", "sum"),
        }

        if profit_col:
            aggregations["Gross Profit"] = (
                "_profit",
                "sum",
            )

        summary = (
            product_data.groupby(
                product_col,
                dropna=False,
            )
            .agg(**aggregations)
            .reset_index()
            .sort_values("Sales", ascending=False)
        )

        left, right = st.columns(2)

        with left:
            top_sales = summary.head(15).sort_values("Sales")

            fig = px.bar(
                top_sales,
                x="Sales",
                y=product_col,
                orientation="h",
                color="Sales",
                title="Top 15 Products by Sales",
                color_continuous_scale="Blues",
            )

            st.plotly_chart(fig, use_container_width=True)

        with right:
            top_units = summary.sort_values(
                "Units", ascending=False
            ).head(15).sort_values("Units")

            fig = px.bar(
                top_units,
                x="Units",
                y=product_col,
                orientation="h",
                color="Units",
                title="Top 15 Products by Units",
                color_continuous_scale="Teal",
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Product Summary")

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ Download Product Summary",
            summary.to_csv(index=False).encode("utf-8"),
            "product_summary.csv",
            "text/csv",
        )

    else:
        st.info("A Product Name column was not found.")

# ============================================================
# 11. FACTORY ANALYSIS
# ============================================================

with factory_tab:
    st.subheader("Factory Comparison")

    if factory_col:
        factory_data = filtered.copy()

        factory_data["_sales"] = numeric_series(
            factory_data, sales_col
        )

        factory_data["_units"] = numeric_series(
            factory_data, units_col
        )

        factory_data["_profit"] = numeric_series(
            factory_data, profit_col
        )

        aggregations = {
            "Order Rows": (factory_col, "size"),
            "Sales": ("_sales", "sum"),
            "Units": ("_units", "sum"),
        }

        if profit_col:
            aggregations["Gross Profit"] = (
                "_profit",
                "sum",
            )

        summary = (
            factory_data.groupby(
                factory_col,
                dropna=False,
            )
            .agg(**aggregations)
            .reset_index()
            .sort_values("Sales", ascending=False)
        )

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
        )

        fig = px.scatter(
            summary,
            x="Units",
            y="Sales",
            size="Order Rows",
            color=factory_col,
            hover_name=factory_col,
            title="Factory Sales vs Unit Volume",
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("A Factory column was not found in the orders CSV.")

# ============================================================
# 12. SHIPPING AND DISTANCE ANALYSIS
# ============================================================

with shipping_tab:
    st.subheader("Shipping Distance Analysis")

    if distances is not None:
        current_distance_col = first_existing(
            distances,
            ["Current_Distance_km", "Current Distance km"],
        )

        nearest_distance_col = first_existing(
            distances,
            ["Nearest_Distance_km", "Nearest Distance km"],
        )

        gap_col = first_existing(
            distances,
            [
                "Distance_Gap_km",
                "Potential_Distance_Difference_km",
            ],
        )

        nearest_factory_col = first_existing(
            distances,
            ["Nearest_Factory", "Nearest Factory"],
        )

        if current_distance_col:
            distance_data = distances.copy()

            # Apply factory filter only if the distance file has
            # a matching factory column.
            distance_factory_col = first_existing(
                distance_data,
                ["Factory", "Current Factory"],
            )

            if distance_factory_col and factory_col:
                allowed = filtered[factory_col].dropna().astype(str).unique()

                distance_data = distance_data[
                    distance_data[distance_factory_col]
                    .astype(str)
                    .isin(allowed)
                ]

            current_distance = pd.to_numeric(
                distance_data[current_distance_col],
                errors="coerce",
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Distance Records",
                f"{len(distance_data):,}",
            )

            c2.metric(
                "Average Current Distance",
                f"{current_distance.mean():,.1f} km"
                if current_distance.notna().any()
                else "N/A",
            )

            if gap_col:
                gap = pd.to_numeric(
                    distance_data[gap_col],
                    errors="coerce",
                )

                c3.metric(
                    "Rows with Positive Distance Gap",
                    f"{(gap > 0).sum():,}",
                )
            else:
                c3.metric(
                    "Nearest Factory Field",
                    "Available" if nearest_factory_col else "N/A",
                )

            left, right = st.columns(2)

            with left:
                distance_factory_col = first_existing(
                    distance_data,
                    ["Factory", "Current Factory"],
                )

                if distance_factory_col:
                    plot_data = distance_data.copy()

                    plot_data["_distance"] = pd.to_numeric(
                        plot_data[current_distance_col],
                        errors="coerce",
                    )

                    plot_data = (
                        plot_data.groupby(
                            distance_factory_col,
                            as_index=False,
                        )["_distance"]
                        .mean()
                    )

                    fig = px.bar(
                        plot_data,
                        x=distance_factory_col,
                        y="_distance",
                        color=distance_factory_col,
                        title="Average Current Distance by Factory",
                        labels={
                            "_distance": "Distance (km)",
                            distance_factory_col: "Factory",
                        },
                    )

                    fig.update_layout(showlegend=False)
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

            with right:
                if nearest_distance_col:
                    plot_data = distance_data[
                        [current_distance_col, nearest_distance_col]
                    ].copy()

                    plot_data.columns = [
                        "Current Factory Distance",
                        "Nearest Factory Distance",
                    ]

                    plot_data = plot_data.apply(
                        pd.to_numeric,
                        errors="coerce",
                    ).melt(
                        var_name="Distance Type",
                        value_name="Distance (km)",
                    )

                    fig = px.box(
                        plot_data,
                        x="Distance Type",
                        y="Distance (km)",
                        title="Current vs Nearest Factory Distance",
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

            st.dataframe(
                distance_data.head(500),
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "⬇️ Download Distance Analysis",
                distance_data.to_csv(index=False).encode("utf-8"),
                "filtered_distance_analysis.csv",
                "text/csv",
            )

            st.info(
                "Distances are straight-line estimates, not actual road "
                "distances or carrier shipping routes."
            )

        else:
            st.warning(
                "The distance CSV does not contain Current_Distance_km. "
                "Check its column names."
            )

    else:
        st.info(
            "Upload distance_analysis.csv to display distance comparisons."
        )

# ============================================================
# 13. REALLOCATION SCENARIOS
# ============================================================

with scenario_tab:
    st.subheader("Factory Reallocation Recommendations")

    if scenarios is not None:
        scenario_data = scenarios.copy()

        score_col = first_existing(
            scenario_data,
            ["Priority_Score", "Priority Score"],
        )

        scenario_product_col = first_existing(
            scenario_data,
            ["Product Name", "Product"],
        )

        current_factory_col = first_existing(
            scenario_data,
            ["Factory", "Current Factory"],
        )

        target_factory_col = first_existing(
            scenario_data,
            [
                "Nearest_Factory",
                "Suggested_Factory",
                "Target Factory",
            ],
        )

        if (
            scenario_product_col
            and product_col
            and selected_products
        ):
            scenario_data = scenario_data[
                scenario_data[scenario_product_col]
                .astype(str)
                .isin(selected_products)
            ]

        if score_col:
            scenario_data[score_col] = pd.to_numeric(
                scenario_data[score_col],
                errors="coerce",
            )

            scenario_data = scenario_data.sort_values(
                score_col,
                ascending=False,
            )

        max_rows = max(
            5,
            min(50, len(scenario_data) if len(scenario_data) >= 5 else 5),
        )

        top_n = st.slider(
            "Number of scenarios to display",
            min_value=5,
            max_value=max_rows,
            value=min(15, max_rows),
            step=5 if max_rows >= 10 else 1,
        )

        if score_col and scenario_product_col:
            plot_data = scenario_data.head(top_n).sort_values(
                score_col
            )

            hover_fields = [
                column
                for column in [
                    current_factory_col,
                    target_factory_col,
                    "Total_Units",
                    "Total_Sales",
                    "Potential_Distance_Reduction_Percent",
                ]
                if column and column in plot_data.columns
            ]

            fig = px.bar(
                plot_data,
                x=score_col,
                y=scenario_product_col,
                orientation="h",
                color=score_col,
                title="Highest-Priority Reallocation Scenarios",
                hover_data=hover_fields,
                color_continuous_scale="Blues",
            )

            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            scenario_data.head(top_n),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ Download Displayed Scenarios",
            scenario_data.head(top_n)
            .to_csv(index=False)
            .encode("utf-8"),
            "displayed_priority_scenarios.csv",
            "text/csv",
        )

        st.warning(
            "These are hypothetical analytical recommendations. "
            "Before reallocating products, validate factory capacity, "
            "product eligibility, inventory, customer service levels, "
            "road routes, and actual transport costs."
        )

    else:
        st.info(
            "Upload priority_scenarios.csv to view ranked "
            "reallocation candidates."
        )

# ============================================================
# 14. DATA QUALITY CHECKS
# ============================================================

with quality_tab:
    st.subheader("Data Quality Report")

    missing = (
        filtered.isna()
        .sum()
        .rename("Missing Values")
        .reset_index()
    )

    missing.columns = ["Column", "Missing Values"]

    missing = missing[
        missing["Missing Values"] > 0
    ].sort_values(
        "Missing Values",
        ascending=False,
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Rows with Missing Values",
        f"{filtered.isna().any(axis=1).sum():,}",
    )

    c2.metric(
        "Duplicate Rows",
        f"{filtered.duplicated().sum():,}",
    )

    c3.metric(
        "Total Columns",
        f"{filtered.shape[1]:,}",
    )

    if not missing.empty:
        st.markdown("#### Missing Values by Column")

        fig = px.bar(
            missing.sort_values("Missing Values"),
            x="Missing Values",
            y="Column",
            orientation="h",
            title="Missing Values",
            color="Missing Values",
            color_continuous_scale="Reds",
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            missing,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No missing values found in the filtered dataset.")

    if order_date_col and ship_date_col:
        order_dates = pd.to_datetime(
            filtered[order_date_col],
            errors="coerce",
        )

        ship_dates = pd.to_datetime(
            filtered[ship_date_col],
            errors="coerce",
        )

        invalid_dates = (
            order_dates.isna() | ship_dates.isna()
        )

        ship_before_order = (
            ship_dates < order_dates
        ).fillna(False)

        future_ship_dates = (
            ship_dates
            > pd.Timestamp.today().normalize()
            + pd.Timedelta(days=365)
        ).fillna(False)

        a, b, c = st.columns(3)

        a.metric(
            "Unparseable Date Rows",
            f"{invalid_dates.sum():,}",
        )

        b.metric(
            "Ship Before Order",
            f"{ship_before_order.sum():,}",
        )

        c.metric(
            "Ship Date Over 1 Year Ahead",
            f"{future_ship_dates.sum():,}",
        )

        st.warning(
            "The earlier data review flagged suspicious shipping dates "
            "far beyond order dates. Verify these records before making "
            "claims about delivery times or shipping performance."
        )

        preview_cols = [
            column
            for column in [
                order_date_col,
                ship_date_col,
            ]
            if column
        ]

        st.markdown("#### Date Quality Preview")

        st.dataframe(
            filtered[preview_cols].head(100),
            use_container_width=True,
            hide_index=True,
        )

    st.download_button(
        "⬇️ Download Filtered Orders",
        filtered.to_csv(index=False).encode("utf-8"),
        "filtered_factory_orders.csv",
        "text/csv",
    )

# ============================================================
# 15. FOOTER
# ============================================================

st.divider()

st.caption(
    "Nassau Candy Factory Reallocation & Shipping Optimization | "
    "Built with Python, Pandas, Streamlit and Plotly. "
    "Distance estimates are not verified transport savings."
)
