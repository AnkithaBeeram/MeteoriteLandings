import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

st.set_page_config(
    page_title="Meteorite Landings Observatory",
    layout="wide",
)

alt.data_transformers.disable_max_rows()

DATA_URL = "https://data.nasa.gov/docs/legacy/meteorite_landings/Meteorite_Landings.csv"
LOCAL_FILE = Path(__file__).resolve().parent / "Meteorite_Landings.csv"

@st.cache_data(show_spinner=False)
def load_data():
    source = "NASA Open Data"
    try:
        if LOCAL_FILE.exists():
            df = pd.read_csv(LOCAL_FILE)
            source = "Local CSV"
        else:
            df = pd.read_csv(DATA_URL)

        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["mass (g)"] = pd.to_numeric(df["mass (g)"], errors="coerce")
        df["reclat"] = pd.to_numeric(df["reclat"], errors="coerce")
        df["reclong"] = pd.to_numeric(df["reclong"], errors="coerce")

        df = df.dropna(subset=["year", "mass (g)", "reclat", "reclong"])
        df = df[df["mass (g)"] > 0]
        df["year"] = df["year"].astype(int)
        df = df[df["year"] <= 2025]
        df["recclass"] = df["recclass"].fillna("Unclassified")
        df["fall"] = df["fall"].fillna("Unknown")
        df["name"] = df["name"].fillna("Unknown")
        return df, source
    except Exception as exc: 
        st.error("Unable to load meteorite data.")
        st.exception(exc)
        return pd.DataFrame(), "Unavailable"


df, data_source = load_data()

title_col, refresh_col = st.columns([5, 1])
with title_col:
    st.title("Meteorite Landings Observatory")
with refresh_col:
    if st.button("🔄 Refresh Data", use_container_width=True):
        load_data.clear()
        st.experimental_rerun()

if df.empty:
    st.stop()

st.sidebar.header("Filters")

years = sorted(df["year"].unique().tolist())
year_range = st.sidebar.slider(
    "Year range",
    min(years),
    min(max(years), 2025),
    (max(min(years), 1800), min(max(years), 2025))
)

class_options = ["All classes"] + sorted(df["recclass"].unique().tolist())
selected_class = st.sidebar.selectbox("Meteorite class/type", class_options)

mass_min_value = float(df["mass (g)"].min())
mass_max_value = float(df["mass (g)"].max())
mass_default_low = float(df["mass (g)"].quantile(0.05))
mass_default_high = float(df["mass (g)"].quantile(0.95))
mass_lower = st.sidebar.number_input(
    "Mass min (g)",
    min_value=0.0,
    max_value=mass_max_value,
    value=mass_default_low,
    step=max(1.0, mass_default_high / 200)
)
mass_upper = st.sidebar.number_input(
    "Mass max (g)",
    min_value=mass_lower,
    max_value=mass_max_value,
    value=mass_default_high,
    step=max(1.0, mass_default_high / 200)
)

search_query = st.sidebar.text_input("Search by meteorite name", "")


filtered = df[
    (df["year"] >= year_range[0]) & (df["year"] <= year_range[1])
    & (df["mass (g)"] >= mass_lower) & (df["mass (g)"] <= mass_upper)
]
if selected_class != "All classes":
    filtered = filtered[filtered["recclass"] == selected_class]
if search_query:
    filtered = filtered[filtered["name"].str.contains(search_query, case=False, na=False)]

if filtered.empty:
    st.warning("No meteorites match these filters.")
    st.stop()


col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
col_kpi1.metric("Total Meteorites", f"{len(filtered):,}")
col_kpi2.metric("Classes", filtered["recclass"].nunique())
col_kpi3.metric("Years Covered", f"{year_range[0]}–{year_range[1]}")

st.header("Meteorite Landing Locations")
df_map = filtered.dropna(subset=["reclat", "reclong"]).copy()
df_map["reclat"] = pd.to_numeric(df_map["reclat"], errors="coerce")
df_map["reclong"] = pd.to_numeric(df_map["reclong"], errors="coerce")
df_map = df_map.dropna(subset=["reclat", "reclong"])

world = alt.topo_feature("https://vega.github.io/vega-datasets/data/world-110m.json", "countries")
world_layer = (
    alt.Chart(world)
    .mark_geoshape(fill="#f0f4fa", stroke="#c5d1e0", strokeWidth=0.6)
    .project(type="equalEarth")
    .properties(width=900, height=480)
)

points = (
    alt.Chart(df_map)
    .mark_circle(opacity=0.65, stroke="#0f2d50", strokeWidth=0.4)
    .encode(
        longitude="reclong:Q",
        latitude="reclat:Q",
        size=alt.Size("mass (g):Q", scale=alt.Scale(type="sqrt", range=[25, 700]), legend=None),
        color=alt.Color("recclass:N", title="Class", scale=alt.Scale(scheme="blues")),
        tooltip=[
            alt.Tooltip("name:N", title="Name"),
            alt.Tooltip("year:Q", title="Year"),
            alt.Tooltip("mass (g):Q", title="Mass (g)", format=","),
            alt.Tooltip("recclass:N", title="Class"),
            alt.Tooltip("fall:N", title="Fall"),
        ],
    )
)

st.altair_chart(world_layer + points, use_container_width=True)


col_timeline, col_mass = st.columns(2)

with col_timeline:
    st.subheader("Recorded Meteorite Landings Over Time")
    year_counts = filtered.groupby("year").size().reset_index(name="count")
    timeline_chart = (
        alt.Chart(year_counts)
        .mark_line(point=True)
        .encode(
            x=alt.X("year:Q", title="Year"),
            y=alt.Y("count:Q", title="Number of Meteorites"),
            tooltip=["year", "count"]
        )
        .properties(height=350)
    )
    st.altair_chart(timeline_chart, use_container_width=True)

with col_mass:
    st.subheader("Distribution of Meteorite Mass")
    df_mass = filtered[(filtered["mass (g)"] > 0)]
    mass_chart = (
        alt.Chart(df_mass)
        .mark_bar()
        .encode(
            x=alt.X('mass (g):Q', bin=alt.Bin(maxbins=40), title='Mass (grams)'),
            y=alt.Y('count():Q', title='Number of Meteorites'),
            tooltip=[alt.Tooltip('count():Q', title='Number in Bin')]
        )
        .properties(height=350)
    )
    st.altair_chart(mass_chart, use_container_width=True)

st.caption(f"Data Source: https://data.nasa.gov/dataset/meteorite-landings")
