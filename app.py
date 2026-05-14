import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import math

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
NASA_API_KEY = "DEMO_KEY"
NASA_NEO_URL = "https://api.nasa.gov/neo/rest/v1/feed"

st.set_page_config(
    page_title="🌍 NASA NEO Аналізатор Астероїдів",
    page_icon="☄️",
    layout="wide",
)

# ─────────────────────────────────────────────
# DATA FUNCTIONS
# ─────────────────────────────────────────────

def fetch_neo_data(start_date: date, end_date: date) -> list[dict]:
    """
    Завантажує дані з NASA NEO API.
    Автоматично розбиває запит на 7-денні відрізки.
    """
    all_asteroids = []
    current = start_date

    while current <= end_date:
        chunk_end = min(current + timedelta(days=6), end_date)
        params = {
            "start_date": current.isoformat(),
            "end_date": chunk_end.isoformat(),
            "api_key": NASA_API_KEY,
        }
        resp = requests.get(NASA_NEO_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        for day_str, neo_list in data["near_earth_objects"].items():
            for neo in neo_list:
                ca = neo["close_approach_data"][0]
                diam = neo["estimated_diameter"]["meters"]
                d_min = float(diam["estimated_diameter_min"])
                d_max = float(diam["estimated_diameter_max"])
                all_asteroids.append(
                    {
                        "name": neo["name"],
                        "date": day_str,
                        "is_hazardous": neo["is_potentially_hazardous_asteroid"],
                        "diameter_min_m": round(d_min, 2),
                        "diameter_max_m": round(d_max, 2),
                        "diameter_avg_m": round((d_min + d_max) / 2, 2),
                        "velocity_kmh": round(
                            float(ca["relative_velocity"]["kilometers_per_hour"]), 2
                        ),
                        "miss_distance_km": round(
                            float(ca["miss_distance"]["kilometers"]), 2
                        ),
                        "orbiting_body": ca["orbiting_body"],
                    }
                )

        current = chunk_end + timedelta(days=1)

    return all_asteroids


def build_dataframe(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def save_csv(df: pd.DataFrame, path: str = "asteroids.csv") -> None:
    df.to_csv(path, index=False)


# ─────────────────────────────────────────────
# SIDEBAR — PERIOD SELECTION
# ─────────────────────────────────────────────
st.sidebar.title("⚙️ Налаштування")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Оберіть період:",
    ["⏮ Попередні 7 днів", "⏭ Наступні 7 днів", "📅 Власний діапазон"],
)

today = date.today()
if mode == "⏮ Попередні 7 днів":
    start_date = today - timedelta(days=7)
    end_date = today - timedelta(days=1)
elif mode == "⏭ Наступні 7 днів":
    start_date = today
    end_date = today + timedelta(days=6)
else:
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Від", today - timedelta(days=7))
    end_date = col2.date_input("До", today)
    if start_date > end_date:
        st.sidebar.error("Дата початку не може бути пізніше дати кінця.")
        st.stop()

st.sidebar.markdown(
    f"**Обраний діапазон:**  \n`{start_date}` → `{end_date}`"
)

load_btn = st.sidebar.button("🚀 Завантажити дані", use_container_width=True)

# ─────────────────────────────────────────────
# MAIN AREA — HEADER
# ─────────────────────────────────────────────
st.title("☄️ NASA NEO — Аналіз навколоземних астероїдів")
st.markdown(
    "Дані отримуються в реальному часі з **NASA Near Earth Object Web Service**."
)
st.markdown("---")

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
if load_btn:
    with st.spinner("Отримую дані з NASA API…"):
        try:
            records = fetch_neo_data(start_date, end_date)
            df = build_dataframe(records)
            save_csv(df)
            st.session_state.df = df
            st.success(
                f"✅ Завантажено **{len(df)}** астероїдів за період "
                f"`{start_date}` – `{end_date}`"
            )
        except requests.exceptions.HTTPError as e:
            st.error(f"Помилка HTTP: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Помилка: {e}")
            st.stop()

df = st.session_state.get("df")

if df is None:
    st.info("👈 Натисніть **«Завантажити дані»** на панелі зліва, щоб розпочати аналіз.")
    st.stop()

# ─────────────────────────────────────────────
# DOWNLOAD CSV
# ─────────────────────────────────────────────
st.sidebar.markdown("---")
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    label="💾 Завантажити CSV",
    data=csv_bytes,
    file_name="asteroids.csv",
    mime="text/csv",
    use_container_width=True,
)

# ─────────────────────────────────────────────
# KPI METRICS
# ─────────────────────────────────────────────
st.subheader("📊 Зведена статистика")

total = len(df)
hazardous = df["is_hazardous"].sum()
closest = df.loc[df["miss_distance_km"].idxmin()]
largest = df.loc[df["diameter_avg_m"].idxmax()]
fastest = df.loc[df["velocity_kmh"].idxmax()]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🌍 Усього астероїдів", total)
col2.metric(
    "⚠️ Небезпечних",
    hazardous,
    delta=f"{hazardous/total*100:.1f}%",
    delta_color="inverse",
)
col3.metric(
    "🎯 Найближчий",
    closest["name"],
    f"{closest['miss_distance_km']:,.0f} км",
)
col4.metric(
    "📏 Найбільший",
    largest["name"],
    f"{largest['diameter_avg_m']:.1f} м",
)
col5.metric(
    "⚡ Найшвидший",
    fastest["name"],
    f"{fastest['velocity_kmh']:,.0f} км/год",
)

st.markdown("---")

# ─────────────────────────────────────────────
# TAB LAYOUT
# ─────────────────────────────────────────────
tab_table, tab_charts, tab_details = st.tabs(
    ["📋 Таблиця даних", "📈 Графіки", "🔍 Деталі"]
)

# ── TAB 1: TABLE ─────────────────────────────
with tab_table:
    st.subheader("Всі астероїди за обраний період")

    # Filters
    c1, c2, c3 = st.columns(3)
    only_hazardous = c1.checkbox("Тільки небезпечні", value=False)
    min_diam = c2.slider(
        "Мін. діаметр (м)",
        0,
        int(df["diameter_avg_m"].max()) + 1,
        0,
    )
    max_dist = c3.slider(
        "Макс. відстань (тис. км)",
        0,
        int(df["miss_distance_km"].max() / 1000) + 1,
        int(df["miss_distance_km"].max() / 1000) + 1,
    )

    filtered = df.copy()
    if only_hazardous:
        filtered = filtered[filtered["is_hazardous"]]
    filtered = filtered[filtered["diameter_avg_m"] >= min_diam]
    filtered = filtered[filtered["miss_distance_km"] <= max_dist * 1000]

    display_df = filtered.copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df["is_hazardous"] = display_df["is_hazardous"].map(
        {True: "⚠️ Так", False: "✅ Ні"}
    )
    display_df["velocity_kmh"] = display_df["velocity_kmh"].apply(
        lambda x: f"{x:,.0f}"
    )
    display_df["miss_distance_km"] = display_df["miss_distance_km"].apply(
        lambda x: f"{x:,.0f}"
    )

    st.dataframe(
        display_df.rename(
            columns={
                "name": "Назва",
                "date": "Дата",
                "is_hazardous": "Небезпечний",
                "diameter_min_m": "Діам. мін (м)",
                "diameter_max_m": "Діам. макс (м)",
                "diameter_avg_m": "Діам. сер (м)",
                "velocity_kmh": "Швидкість (км/год)",
                "miss_distance_km": "Відстань (км)",
                "orbiting_body": "Орбіта",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Показано {len(filtered)} з {total} астероїдів")

# ── TAB 2: CHARTS ────────────────────────────
with tab_charts:

    # Chart 1 — Asteroids per day
    st.subheader("1️⃣ Кількість астероїдів за днями")
    daily = (
        df.groupby(df["date"].dt.strftime("%Y-%m-%d"))
        .agg(
            total=("name", "count"),
            hazardous=("is_hazardous", "sum"),
        )
        .reset_index()
        .rename(columns={"date": "Дата", "total": "Усього", "hazardous": "Небезпечних"})
    )
    fig1 = go.Figure()
    fig1.add_bar(x=daily["Дата"], y=daily["Усього"], name="Усього", marker_color="#4B8BBE")
    fig1.add_bar(
        x=daily["Дата"], y=daily["Небезпечних"], name="Небезпечних", marker_color="#E05252"
    )
    fig1.update_layout(
        barmode="overlay",
        xaxis_title="Дата",
        yaxis_title="Кількість",
        legend_title="Тип",
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig1, use_container_width=True)

    col_l, col_r = st.columns(2)

    # Chart 2 — Pie: hazardous ratio
    with col_l:
        st.subheader("2️⃣ Співвідношення небезпечних")
        pie_data = df["is_hazardous"].value_counts().reset_index()
        pie_data.columns = ["Тип", "Кількість"]
        pie_data["Тип"] = pie_data["Тип"].map({True: "⚠️ Небезпечні", False: "✅ Безпечні"})
        fig2 = px.pie(
            pie_data,
            names="Тип",
            values="Кількість",
            color="Тип",
            color_discrete_map={
                "⚠️ Небезпечні": "#E05252",
                "✅ Безпечні": "#4B8BBE",
            },
            hole=0.45,
        )
        fig2.update_layout(
            height=360,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 3 — Top 10 closest
    with col_r:
        st.subheader("3️⃣ Топ-10 найближчих до Землі")
        top10 = df.nsmallest(10, "miss_distance_km")[
            ["name", "miss_distance_km", "is_hazardous"]
        ].copy()
        top10["color"] = top10["is_hazardous"].map(
            {True: "#E05252", False: "#4B8BBE"}
        )
        fig3 = go.Figure(
            go.Bar(
                x=top10["miss_distance_km"],
                y=top10["name"],
                orientation="h",
                marker_color=top10["color"].tolist(),
                text=top10["miss_distance_km"].apply(lambda v: f"{v:,.0f} км"),
                textposition="outside",
            )
        )
        fig3.update_layout(
            xaxis_title="Відстань (км)",
            yaxis_title="",
            height=360,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Chart 4 — Size vs Distance scatter
    st.subheader("4️⃣ Залежність: Розмір ↔ Відстань до Землі")
    fig4 = px.scatter(
        df,
        x="miss_distance_km",
        y="diameter_avg_m",
        color=df["is_hazardous"].map({True: "⚠️ Небезпечний", False: "✅ Безпечний"}),
        color_discrete_map={"⚠️ Небезпечний": "#E05252", "✅ Безпечний": "#4B8BBE"},
        hover_name="name",
        hover_data={
            "miss_distance_km": ":,.0f",
            "diameter_avg_m": ":.1f",
            "velocity_kmh": ":,.0f",
        },
        labels={
            "miss_distance_km": "Відстань (км)",
            "diameter_avg_m": "Середній діаметр (м)",
            "color": "Статус",
        },
        size="diameter_avg_m",
        size_max=30,
        opacity=0.75,
        height=420,
    )
    fig4.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig4, use_container_width=True)

    # Chart 5 — Velocity vs Distance
    st.subheader("5️⃣ Залежність: Швидкість ↔ Відстань до Землі")
    fig5 = px.scatter(
        df,
        x="miss_distance_km",
        y="velocity_kmh",
        color=df["is_hazardous"].map({True: "⚠️ Небезпечний", False: "✅ Безпечний"}),
        color_discrete_map={"⚠️ Небезпечний": "#E05252", "✅ Безпечний": "#4B8BBE"},
        hover_name="name",
        trendline="ols",
        labels={
            "miss_distance_km": "Відстань (км)",
            "velocity_kmh": "Швидкість (км/год)",
            "color": "Статус",
        },
        height=420,
    )
    fig5.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig5, use_container_width=True)

# ── TAB 3: DETAIL VIEW ───────────────────────
with tab_details:
    st.subheader("🔍 Детальна інформація про астероїд")

    asteroid_names = df["name"].tolist()
    selected_name = st.selectbox("Оберіть астероїд:", asteroid_names)

    row = df[df["name"] == selected_name].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("📅 Дата", row["date"].strftime("%Y-%m-%d"))
    c2.metric(
        "⚠️ Небезпечний",
        "ТАК" if row["is_hazardous"] else "НІ",
    )
    c3.metric("🌐 Орбіта", row["orbiting_body"])

    c4, c5, c6 = st.columns(3)
    c4.metric("📏 Діам. мін", f"{row['diameter_min_m']:.1f} м")
    c5.metric("📏 Діам. сер", f"{row['diameter_avg_m']:.1f} м")
    c6.metric("📏 Діам. макс", f"{row['diameter_max_m']:.1f} м")

    c7, c8 = st.columns(2)
    c7.metric("⚡ Швидкість", f"{row['velocity_kmh']:,.0f} км/год")
    c8.metric("🎯 Відстань", f"{row['miss_distance_km']:,.0f} км")

    # Diameter gauge
    max_diam = df["diameter_avg_m"].max()
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=row["diameter_avg_m"],
            title={"text": "Середній діаметр (м)"},
            delta={"reference": df["diameter_avg_m"].mean()},
            gauge={
                "axis": {"range": [0, max_diam]},
                "bar": {"color": "#E05252" if row["is_hazardous"] else "#4B8BBE"},
                "steps": [
                    {"range": [0, max_diam * 0.33], "color": "#daf0da"},
                    {"range": [max_diam * 0.33, max_diam * 0.66], "color": "#fff3cd"},
                    {"range": [max_diam * 0.66, max_diam], "color": "#fdd"},
                ],
                "threshold": {
                    "line": {"color": "orange", "width": 3},
                    "thickness": 0.8,
                    "value": df["diameter_avg_m"].mean(),
                },
            },
        )
    )
    fig_gauge.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("---")
st.caption("Дані: NASA Near Earth Object Web Service · https://api.nasa.gov")
