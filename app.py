import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Programme Dashboard",
    page_icon="📊",
    layout="wide",
)

CSV_URL = "https://docs.google.com/spreadsheets/d/13bFinzJP2bn9CvUxcwTbjdF2R1fBGlwbCCZFkcc_tx8/edit?usp=sharing"

@st.cache_data(ttl=60)
def load_data(url):
    data = pd.read_csv(url)
    data.columns = data.columns.str.strip()
    return data

st.title("Programme Performance Dashboard")
st.caption("Practice dashboard connected to Google Sheets")

if st.sidebar.button("Refresh data"):
    load_data.clear()

try:
    df = load_data(CSV_URL)
except Exception:
    st.error("Could not load the sheet. Check your published CSV link.")
    st.stop()

if df.empty:
    st.info("Add some rows to your Google Sheet.")
    st.stop()

numeric_columns = df.select_dtypes(include="number").columns.tolist()

if not numeric_columns:
    st.warning("Your sheet needs at least one numeric column.")
    st.stop()

st.sidebar.header("Dashboard settings")

category = st.sidebar.selectbox(
    "Compare by", df.columns.tolist()
)

metric = st.sidebar.selectbox(
    "Measure", numeric_columns
)

date_column = st.sidebar.selectbox(
    "Date column",
    ["None"] + df.columns.tolist(),
)

options = sorted(df[category].dropna().astype(str).unique())

selected = st.sidebar.multiselect(
    f"Filter {category}",
    options,
    default=options,
)

filtered = df[df[category].astype(str).isin(selected)].copy()

if filtered.empty:
    st.info("Select at least one category with data.")
    st.stop()

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Records", f"{len(filtered):,}")
kpi2.metric(f"Total {metric}", f"{filtered[metric].sum():,.1f}")
kpi3.metric(
    f"Average {metric} per record",
    f"{filtered[metric].mean():,.1f}",
)

summary = (
    filtered.groupby(category, as_index=False)[metric]
    .sum()
    .sort_values(metric, ascending=False)
)

left, right = st.columns(2)

with left:
    st.subheader(f"{metric} by {category}")
    figure = px.bar(
        summary,
        x=category,
        y=metric,
        color_discrete_sequence=["#2563EB"],
        template="plotly_white",
    )
    st.plotly_chart(figure, use_container_width=True)

with right:
    st.subheader("Trend over time")

    if date_column == "None":
        st.info("Choose a date column in the sidebar.")
    else:
        dated = filtered.copy()
        dated["_date"] = pd.to_datetime(
            dated[date_column], errors="coerce"
        ).dt.normalize()

        trend = (
            dated.dropna(subset=["_date"])
            .groupby("_date", as_index=False)[metric]
            .sum()
        )

        if trend.empty:
            st.warning("No valid dates found in that column.")
        else:
            figure = px.line(
                trend,
                x="_date",
                y=metric,
                markers=True,
                labels={"_date": "Date"},
                color_discrete_sequence=["#0D9488"],
                template="plotly_white",
            )
            st.plotly_chart(figure, use_container_width=True)

st.subheader("Detailed data")
st.dataframe(filtered, use_container_width=True, hide_index=True)

st.download_button(
    "Download filtered data",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="dashboard_data.csv",
    mime="text/csv",
)

st.caption(
    "Totals and averages are suitable for additive measures such as "
    "expenditure or counts. Rates and percentages may need different calculations."
)
