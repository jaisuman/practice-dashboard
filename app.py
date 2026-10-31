import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection


st.set_page_config(
    page_title="Programme Dashboard",
    page_icon="📊",
    layout="wide",
)

# REPLACE "Sheet1" with the exact tab name in your Google Sheet.
WORKSHEET_NAME = "Sheet1"


@st.cache_data(ttl=60)
def load_data(worksheet_name):
    connection = st.connection(
        "gsheets",
        type=GSheetsConnection,
    )

    # Reads the private spreadsheet using Streamlit Secrets.
    data = connection.read(
        worksheet=worksheet_name,
        ttl=0,
    )

    data.columns = data.columns.astype(str).str.strip()
    return data.dropna(how="all")


st.title("Programme Performance Dashboard")
st.caption("Practice dashboard connected to Google Sheets")

if st.sidebar.button("Refresh data"):
    load_data.clear()

try:
    df = load_data(WORKSHEET_NAME)
except Exception:
    st.error(
        "Could not load the private Google Sheet. "
        "Check Streamlit Secrets, the worksheet tab name, "
        "and the service account's Viewer access."
    )
    st.stop()

if df.empty:
    st.info("Add some rows to your Google Sheet.")
    st.stop()

numeric_columns = df.select_dtypes(
    include="number"
).columns.tolist()

if not numeric_columns:
    st.warning(
        "Your sheet needs at least one numeric column. "
        "Store numbers without typed currency symbols."
    )
    st.stop()


# SIDEBAR
st.sidebar.header("Dashboard settings")

category = st.sidebar.selectbox(
    "Compare by",
    df.columns.tolist(),
)

metric = st.sidebar.selectbox(
    "Measure",
    numeric_columns,
)

date_column = st.sidebar.selectbox(
    "Date column",
    options=[None] + df.columns.tolist(),
    format_func=lambda value: (
        "No date chart" if value is None else value
    ),
)

category_values = (
    df[category].astype("string").fillna("(Blank)")
)

options = sorted(category_values.unique().tolist())

selected = st.sidebar.multiselect(
    f"Filter {category}",
    options=options,
    default=options,
)

filtered = df.loc[
    category_values.isin(selected)
].copy()

if filtered.empty:
    st.info("Select at least one category with data.")
    st.stop()

if filtered[metric].notna().sum() == 0:
    st.warning("The selected rows contain no values for this measure.")
    st.stop()


# KPI CARDS
kpi1, kpi2, kpi3 = st.columns(3)

kpi1.metric(
    "Records",
    f"{len(filtered):,}",
)

kpi2.metric(
    f"Total {metric}",
    f"{filtered[metric].sum():,.1f}",
)

kpi3.metric(
    f"Average {metric} per record",
    f"{filtered[metric].mean():,.1f}",
)


# Build chart data separately so the original table is preserved.
chart_data = pd.DataFrame({
    "Category": category_values.loc[filtered.index],
    "Value": filtered[metric],
})

summary = (
    chart_data.groupby("Category", as_index=False)["Value"]
    .sum(min_count=1)
    .sort_values("Value", ascending=False)
)

left, right = st.columns(2)

with left:
    st.subheader(f"{metric} by {category}")

    figure = px.bar(
        summary,
        x="Category",
        y="Value",
        labels={
            "Category": category,
            "Value": metric,
        },
        color_discrete_sequence=["#2563EB"],
        template="plotly_white",
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
    )

with right:
    st.subheader("Trend over time")

    if date_column is None:
        st.info("Choose a date column in the sidebar.")
    else:
        dated = pd.DataFrame({
            "Date": pd.to_datetime(
                filtered[date_column],
                errors="coerce",
            ).dt.normalize(),
            "Value": filtered[metric],
        })

        trend = (
            dated.dropna(subset=["Date"])
            .groupby("Date", as_index=False)["Value"]
            .sum(min_count=1)
            .sort_values("Date")
        )

        if trend.empty:
            st.warning(
                "No valid dates found in that column. "
                "Use consistent dates such as 2026-10-01."
            )
        else:
            figure = px.line(
                trend,
                x="Date",
                y="Value",
                markers=True,
                labels={"Value": metric},
                color_discrete_sequence=["#0D9488"],
                template="plotly_white",
            )

            st.plotly_chart(
                figure,
                use_container_width=True,
            )


# TABLE AND DOWNLOAD
st.subheader("Detailed data")

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download filtered data",
    data=filtered.to_csv(index=False).encode("utf-8-sig"),
    file_name="dashboard_data.csv",
    mime="text/csv",
)

st.caption(
    "Totals are suitable for additive measures such as expenditure "
    "or counts. Rates and percentages may need weighted calculations. "
    "Click Refresh data to fetch the latest sheet values."
)
