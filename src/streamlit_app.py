import streamlit as st
import pandas as pd
import altair as alt
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium
from pathlib import Path
from data_prep import clean_df

st.set_page_config(
    page_title="Meteorite Landings Observatory",
    layout="wide",
)

alt.data_transformers.disable_max_rows()

DATA_URL = "https://data.nasa.gov/docs/legacy/meteorite_landings/Meteorite_Landings.csv"
LOCAL_FILE = Path(__file__).resolve().parent / "Meteorite_Landings.csv"

CATEGORY_COLORS = {
    "Stony": "#00a0e1",
    "Stony-iron": "#e6a532",
    "Iron": "#d7642c",
    "Other": "#41afaa",
}

category_order = ["Stony", "Stony-iron", "Iron", "Other"]

@st.cache_data(show_spinner=False)
def load_data():
    source = "NASA Open Data"
    try:
        if LOCAL_FILE.exists():
            df = pd.read_csv(LOCAL_FILE)
            source = "Local CSV"
        else:
            df = pd.read_csv(DATA_URL)

        df = clean_df(df)
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
    if st.button("Refresh Data", use_container_width=True):
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
    (max(min(years), 1900), min(max(years), 2025)),
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
    step=max(1.0, mass_default_high / 200),
)
mass_upper = st.sidebar.number_input(
    "Mass max (g)",
    min_value=mass_lower,
    max_value=mass_max_value,
    value=mass_default_high,
    step=max(1.0, mass_default_high / 200),
)

search_query = st.sidebar.text_input("Search by meteorite name", "")

filtered = df[
    (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
    & (df["mass (g)"] >= mass_lower)
    & (df["mass (g)"] <= mass_upper)
]
if selected_class != "All classes":
    filtered = filtered[filtered["recclass"] == selected_class]
if search_query:
    filtered = filtered[
        filtered["name"].str.contains(search_query, case=False, na=False)
    ]

if filtered.empty:
    st.warning("No meteorites match these filters.")
    st.stop()

col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
col_kpi1.metric("Total Meteorites", f"{len(filtered):,}")
col_kpi2.metric("Classes", filtered["recclass"].nunique())
col_kpi3.metric("Years Covered", f"{year_range[0]}-{year_range[1]}")

overview, deep_dive_tab = st.tabs(["Overview", "Deep Dive"])
with overview:
    # don't like the folium map
    st.header("Meteorite Landing Locations")
    df_map = filtered.dropna(subset=["reclat", "reclong"]).copy()

    if not df_map.empty:
        center_lat = float(df_map["reclat"].mean())
        center_lon = float(df_map["reclong"].mean())
    else:
        center_lat, center_lon = 0.0, 0.0

    folium_map = folium.Map(
        location=[center_lat, center_lon],
        tiles="CartoDB positron",
        zoom_start=2,
    )

    if not df_map.empty:
        locations = df_map[["reclat", "reclong"]].values.tolist()
        FastMarkerCluster(locations).add_to(folium_map)

    st_folium(folium_map, width=900, height=480)

    col_timeline, col_mass = st.columns(2)

    with col_timeline:
        st.subheader("Recorded Meteorite Landings Over Time")
        max_year = filtered['year'].max()
        min_year = filtered['year'].min()

        timeline_chart = alt.Chart(filtered).mark_line(point=True).encode(
        x=alt.X(
            'year:Q',
            title='Year',
            scale=alt.Scale(domain=[min_year, max_year]),
            axis=alt.Axis(format='d')
        ),
        y=alt.Y(
            'count(year):Q',
            title='Number of Meteorites'
        ),
        tooltip=['year', 'count(year)']).properties(
        title='Recorded Meteorite Landings Over Time',
        height=350).configure_view(
        strokeWidth=0).configure_axis(grid=False)
        st.altair_chart(timeline_chart, use_container_width=True)

    with col_mass:
        st.subheader("Distribution of Meteorite Mass")
        mass_chart = (
            alt.Chart(filtered)
            .mark_bar()
            .encode(
                x=alt.X(
                    "mass (g):Q", bin=alt.Bin(maxbins=40), title="Mass (grams)"
                ),
                y=alt.Y("count():Q", title="Number of Meteorites"),
                tooltip=[alt.Tooltip("count():Q", title="Number in Bin")],
            )
            .properties(height=350)
        )
        st.altair_chart(mass_chart, use_container_width=True)



with deep_dive_tab:
    st.subheader("Mass by Category")
    df_mass_positive = filtered[filtered["mass (g)"] > 0]

    boxplot_category = (
        alt.Chart(df_mass_positive)
        .mark_boxplot(extent='min-max')
        .encode(
            x=alt.X(
                "category:N",
                sort=category_order,
                axis=alt.Axis(labelAngle=0),
                title="Meteorite category",
            ),
            y=alt.Y(
                "mass (g):Q",
                scale=alt.Scale(type="log"),
                axis=alt.Axis(format="~g"),
                title="Mass (grams, log scale)",
            ),
            color=alt.Color(
                "category:N",
                scale=alt.Scale(domain=list(CATEGORY_COLORS.keys()), range=list(CATEGORY_COLORS.values())),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("recclass:N", title="Class"),
                alt.Tooltip("mass (g):Q", title="Mass (g)", format=","),
                alt.Tooltip("category:N", title="Category"),
            ],
        )
        .properties(width=400)
    )
    st.altair_chart(boxplot_category, use_container_width=True)

    st.subheader("Mass by Fall Status")
    fall_order = ["Fell", "Found"]

    boxplot_fall = (
        alt.Chart(df_mass_positive)
        .mark_boxplot(extent='min-max')
        .encode(
            x=alt.X(
                "fall:N",
                sort=fall_order,
                axis=alt.Axis(labelAngle=0),
                title="Recovery status"
            ),
            y=alt.Y(
                "mass (g):Q",
                scale=alt.Scale(type="log"),
                axis=alt.Axis(format="~g"),
                title="Mass (grams, log scale)"
            ),
            color=alt.Color("fall:N", legend=None),
            tooltip=[
                alt.Tooltip("recclass:N", title="Class"),
                alt.Tooltip("mass (g):Q", title="Mass (g)", format=","),
                alt.Tooltip("category:N", title="Category"),
            ],
        )
        .properties(width=400)
    )
    st.altair_chart(boxplot_fall, use_container_width=True)

st.caption("Data Source: https://data.nasa.gov/dataset/meteorite-landings")
