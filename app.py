"""
Nassau Candy Distributor: Factory Reallocation & Shipping Optimization dashboard.

Rebuilds the full analysis (factory mapping, distances, nearest-factory
comparison, scenario ranking, K-Means clusters) from the project CSV files and
lets you explore it with filters, sliders and a what-if simulator.

Run:  streamlit run app.py
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Nassau Candy | Factory Reallocation",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Project constants
# ---------------------------------------------------------------------------
FACTORIES = {
    "Lot's O' Nuts": (32.881893, -111.768036),
    "Wicked Choccy's": (32.076176, -81.088371),
    "Sugar Shack": (48.11914, -96.18115),
    "Secret Factory": (41.446333, -90.565487),
    "The Other Factory": (35.1175, -89.971107),
}
PRODUCT_TO_FACTORY = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar - Scrumdiddlyumptious": "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy": "Sugar Shack",
    "SweeTARTS": "Sugar Shack",
    "Nerds": "Sugar Shack",
    "Fun Dip": "Sugar Shack",
    "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory",
    "Hair Toffee": "The Other Factory",
    "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Kazookles": "The Other Factory",
}
REQUIRED_RAW = [
    "Order ID", "Order Date", "Ship Date", "Ship Mode", "Country/Region", "City",
    "State/Province", "Postal Code", "Division", "Region", "Product Name",
    "Sales", "Units", "Gross Profit", "Cost",
]
DEST_KEY = ["Country/Region", "City", "State/Province", "Postal Code"]
RAW_NAMES = ["Nassau_Candy_Distributor.csv", "Nassau Candy Distributor.csv"]
GEO_NAMES = ["factory_distance_comparison.csv", "destinations_with_clusters.csv", "destinations_geocoded.csv"]
FILE_SLOTS = {
    "raw": RAW_NAMES,
    "geo": GEO_NAMES,
    "dist": ["distance_analysis.csv"],
}
GEO_CACHE = Path(__file__).resolve().parent / "data" / "destinations_geocoded.csv"

INK, PAPER, BERRY, SLATE, TEAL, AMBER, MUTED, LINE = (
    "#1C2540", "#F6F7FB", "#B5295F", "#51618A", "#12857E", "#D9962B", "#6B7490", "#E3E6EF",
)
FACTORY_COLORS = {
    "Lot's O' Nuts": "#D08A2E",
    "Wicked Choccy's": "#5A3A29",
    "Sugar Shack": "#E0529C",
    "Secret Factory": "#12857E",
    "The Other Factory": "#6C77C9",
}
CLUSTER_COLORS = ["#2F6FDE", "#B5295F", "#12857E", "#D9962B", "#6C77C9",
                  "#5A3A29", "#E0529C", "#3A9BD9", "#7A8B2E", "#8A93A8"]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, .stApp, .stMarkdown, p, h1, h2, h3, h4, label, li, td, th, button, input, textarea,
[data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {{
    font-family: 'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}
.stApp {{ background: {PAPER}; color: {INK}; }}
.block-container {{ padding-top: 1.2rem; max-width: 1400px; }}
section[data-testid="stSidebar"] {{ background: #fff; border-right: 1px solid {LINE}; }}
h1, h2, h3, h4 {{ color: {INK}; letter-spacing: -0.01em; }}
.hero {{ background: {INK}; border-radius: 14px; padding: 26px 30px; margin-bottom: 14px; }}
.hero-title {{ color: #fff; font-size: 1.75rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.2; }}
.hero-sub {{ color: #AAB3CC; font-size: 0.95rem; margin-top: 4px; }}
.hero-finding {{ color: #fff; font-size: 1.05rem; font-weight: 600; margin-top: 16px; line-height: 1.5;
    border-left: 4px solid {BERRY}; padding-left: 14px; max-width: 980px; }}
.notice {{ background: #FFF7E6; border: 1px solid #F0D9A8; color: #6B4E10; border-radius: 10px;
    padding: 10px 14px; font-size: 0.88rem; margin-bottom: 14px; }}
div[data-testid="stMetric"] {{ background: #fff; border: 1px solid {LINE}; border-left: 4px solid {SLATE};
    border-radius: 10px; padding: 12px 16px; }}
div[data-testid="stMetricLabel"] {{ color: {MUTED}; font-weight: 600; }}
div[data-testid="stMetricValue"] {{ color: {INK}; font-weight: 800; }}
button[data-baseweb="tab"] {{ font-weight: 700; }}
.caption-note {{ color: {MUTED}; font-size: 0.86rem; margin: -4px 0 10px 0; }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def show(fig: go.Figure) -> None:
    """Render a Plotly chart at full width (works across Streamlit versions)."""
    try:
        st.plotly_chart(fig, width="stretch", theme=None)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, theme=None)


def table(df: pd.DataFrame, **kwargs) -> None:
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def style(fig: go.Figure, height: int = 360, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=44, b=8),
        font=dict(family="Manrope, system-ui, sans-serif", color=INK, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", y=-0.18, title=None),
        title=dict(font=dict(size=15, color=INK), x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor="#CBD0DD", title=None)
    fig.update_yaxes(gridcolor="#E7EAF2", zeroline=False)
    return fig


def money(x: float) -> str:
    return f"${x:,.0f}"


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


NORMALIZED_MAP = {normalize_name(k): v for k, v in PRODUCT_TO_FACTORY.items()}


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def clean_text(s: pd.Series) -> pd.Series:
    s = s.fillna("").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return s


def make_key(df: pd.DataFrame) -> pd.Series:
    parts = [clean_text(df[c]).str.casefold() for c in DEST_KEY]
    return parts[0] + "|" + parts[1] + "|" + parts[2] + "|" + parts[3]


def find_file(names: list[str]) -> Path | None:
    here = Path(__file__).resolve().parent
    for folder in (here / "data", here, Path("data")):
        for n in names:
            p = folder / n
            if p.exists():
                return p
    return None


# ---------------------------------------------------------------------------
# Data pipeline (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_geo(b: bytes) -> pd.DataFrame:
    geo = pd.read_csv(io.BytesIO(b), dtype={"Postal Code": str})
    geo.columns = [c.strip() for c in geo.columns]
    need = DEST_KEY + ["Latitude", "Longitude"]
    miss_geo = [c for c in need if c not in geo.columns]
    if miss_geo:
        raise ValueError("The coordinates file is missing these columns: " + ", ".join(miss_geo))
    geo = geo[need + (["Geocode_Method"] if "Geocode_Method" in geo.columns else [])].copy()
    geo["Latitude"] = pd.to_numeric(geo["Latitude"], errors="coerce")
    geo["Longitude"] = pd.to_numeric(geo["Longitude"], errors="coerce")
    geo = geo.dropna(subset=["Latitude", "Longitude"])
    geo["_key"] = make_key(geo)
    return geo.drop_duplicates("_key").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_dist(b: bytes) -> pd.DataFrame:
    cols = ["Row ID", "Current_Distance_km", "Nearest_Factory", "Nearest_Distance_km"]
    d = pd.read_csv(io.BytesIO(b))
    miss = [c for c in cols if c not in d.columns]
    if miss:
        raise ValueError("The distance file is missing these columns: " + ", ".join(miss))
    return d[cols].drop_duplicates("Row ID").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_plain(b: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(b))


@st.cache_data(show_spinner="Building the analysis from your files...")
def build_dataset(raw_bytes: bytes, geo: pd.DataFrame, dist: pd.DataFrame | None):
    df = pd.read_csv(io.BytesIO(raw_bytes), dtype={"Postal Code": str})
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED_RAW if c not in df.columns]
    if missing:
        raise ValueError("The orders file is missing these columns: " + ", ".join(missing))

    n_raw = len(df)
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True, errors="coerce")
    df["Lead Time Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Factory"] = df["Product Name"].map(lambda n: NORMALIZED_MAP.get(normalize_name(n)))
    n_unmapped = int(df["Factory"].isna().sum())
    df = df[df["Factory"].notna()].copy()
    df["Postal Code"] = clean_text(df["Postal Code"])
    df["_key"] = make_key(df)

    df = df.merge(geo[["_key", "Latitude", "Longitude"]], on="_key", how="left")

    # Fallback: match on country/city/state when that combination has a single location.
    miss = df["Latitude"].isna()
    if miss.any():
        g2 = geo.copy()
        g2["_ck"] = clean_text(g2["Country/Region"]).str.casefold() + "|" + clean_text(g2["City"]).str.casefold() + "|" + clean_text(g2["State/Province"]).str.casefold()
        uniq = g2.groupby("_ck").agg(lat=("Latitude", "nunique"), lon=("Longitude", "nunique"),
                                     Latitude=("Latitude", "first"), Longitude=("Longitude", "first"))
        uniq = uniq[(uniq["lat"] == 1) & (uniq["lon"] == 1)]
        ck = clean_text(df["Country/Region"]).str.casefold() + "|" + clean_text(df["City"]).str.casefold() + "|" + clean_text(df["State/Province"]).str.casefold()
        df.loc[miss, "Latitude"] = ck[miss].map(uniq["Latitude"])
        df.loc[miss, "Longitude"] = ck[miss].map(uniq["Longitude"])

    df["geo_ok"] = df["Latitude"].notna() & df["Longitude"].notna()

    names = list(FACTORIES)
    for n in names:
        df[f"d::{n}"] = np.nan
    ok = df["geo_ok"].to_numpy()
    if ok.any():
        mat = np.column_stack([
            haversine_km(df.loc[ok, "Latitude"], df.loc[ok, "Longitude"], *FACTORIES[n]) for n in names
        ])
        for i, n in enumerate(names):
            df.loc[ok, f"d::{n}"] = mat[:, i]
        idx_cur = df.loc[ok, "Factory"].map({n: i for i, n in enumerate(names)}).to_numpy()
        df["Nearest_Factory"] = None
        df.loc[ok, "Nearest_Factory"] = np.array(names)[mat.argmin(axis=1)]
        df["Nearest_Distance_km"] = np.nan
        df.loc[ok, "Nearest_Distance_km"] = mat.min(axis=1)
        df["Current_Distance_km"] = np.nan
        df.loc[ok, "Current_Distance_km"] = mat[np.arange(len(mat)), idx_cur]
    else:
        raise ValueError("None of the orders could be matched to a destination location.")

    n_filled = 0
    if dist is not None and "Row ID" in df.columns:
        lookup = dist.set_index("Row ID")
        gap = df["Current_Distance_km"].isna()
        for c in ["Current_Distance_km", "Nearest_Factory", "Nearest_Distance_km"]:
            df.loc[gap, c] = df.loc[gap, "Row ID"].map(lookup[c])
        n_filled = int((gap & df["Current_Distance_km"].notna()).sum())
    df["dist_ok"] = df["Current_Distance_km"].notna()
    df["Distance_Gap_km"] = (df["Current_Distance_km"] - df["Nearest_Distance_km"]).clip(lower=0)
    df["Is_Nearest"] = df["Factory"] == df["Nearest_Factory"]
    df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()

    info = {
        "n_raw": n_raw,
        "n_unmapped": n_unmapped,
        "n_no_coords": int((~df["geo_ok"]).sum()),
        "n_dist_filled": n_filled,
        "n_no_dist": int((~df["dist_ok"]).sum()),
        "n_duplicates": int(df.duplicated(subset=[c for c in df.columns if not c.startswith("d::")
                                                 and c not in ("_key", "Month")]).sum()),
        "geo_methods": geo["Geocode_Method"].value_counts().to_dict() if "Geocode_Method" in geo.columns else None,
        "n_destinations": int(df["_key"].nunique()),
    }
    return df, info


@st.cache_data(show_spinner=False)
def cluster_scores(loc: pd.DataFrame) -> pd.DataFrame:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    X = _sphere(loc)
    rows = []
    for k in range(2, 11):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
        rows.append({"Clusters": k, "Silhouette score": silhouette_score(X, labels)})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def cluster_labels(loc: pd.DataFrame, k: int) -> pd.DataFrame:
    from sklearn.cluster import KMeans

    out = loc.copy()
    out["Cluster"] = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(_sphere(out))
    return out


def location_table(d: pd.DataFrame):
    loc = (d[d["geo_ok"]].groupby("_key")
           .agg(City=("City", "first"), State=("State/Province", "first"),
                Latitude=("Latitude", "first"), Longitude=("Longitude", "first"))
           .reset_index())
    return loc, loc.drop_duplicates(["Latitude", "Longitude"]).reset_index(drop=True)


def _sphere(loc: pd.DataFrame) -> np.ndarray:
    lat, lon = np.radians(loc["Latitude"].to_numpy()), np.radians(loc["Longitude"].to_numpy())
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def geocode_missing(raw_bytes: bytes) -> None:
    """Look up coordinates with OpenStreetMap (about 1 second per place). Resumable."""
    from geopy.extra.rate_limiter import RateLimiter
    from geopy.geocoders import Nominatim

    raw = pd.read_csv(io.BytesIO(raw_bytes), dtype={"Postal Code": str})
    dest = raw[DEST_KEY].drop_duplicates().reset_index(drop=True)
    dest["Postal Code"] = clean_text(dest["Postal Code"])
    done = pd.read_csv(GEO_CACHE, dtype={"Postal Code": str}) if GEO_CACHE.exists() else pd.DataFrame(
        columns=DEST_KEY + ["Latitude", "Longitude", "Geocode_Method"])
    done_keys = set(make_key(done)) if len(done) else set()
    dest["_key"] = make_key(dest)
    todo = dest[~dest["_key"].isin(done_keys)]

    geocode = RateLimiter(Nominatim(user_agent="nassau_candy_dashboard").geocode,
                          min_delay_seconds=1.1, max_retries=2, error_wait_seconds=5)
    bar = st.progress(0.0, text="Looking up destinations...")
    rows = done.to_dict("records")
    for i, (_, r) in enumerate(todo.iterrows(), start=1):
        loc = geocode(f'{r["City"]}, {r["State/Province"]}, {r["Postal Code"]}, {r["Country/Region"]}')
        method = "Full address"
        if not loc:
            loc = geocode(f'{r["City"]}, {r["State/Province"]}, {r["Country/Region"]}')
            method = "City/state/country"
        rows.append({**{c: r[c] for c in DEST_KEY},
                     "Latitude": loc.latitude if loc else None,
                     "Longitude": loc.longitude if loc else None,
                     "Geocode_Method": method if loc else "Not found"})
        if i % 20 == 0 or i == len(todo):
            GEO_CACHE.parent.mkdir(exist_ok=True)
            pd.DataFrame(rows).to_csv(GEO_CACHE, index=False)
            bar.progress(i / len(todo), text=f"Looked up {i} of {len(todo)} destinations")
    GEO_CACHE.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(GEO_CACHE, index=False)


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------
def minmax(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else s * 0


def rank_scenarios(g: pd.DataFrame, w_dist: float, w_vol: float, w_sales: float, wonka_only: bool) -> pd.DataFrame:
    x = g[g["Factory"] != g["Nearest_Factory"]]
    if wonka_only:
        x = x[x["Product Name"].str.startswith("Wonka Bar")]
    if x.empty:
        return pd.DataFrame()
    s = (x.groupby(["Product Name", "Factory", "Nearest_Factory"])
           .agg(Order_Lines=("Order ID", "size"), Destinations=("_key", "nunique"),
                Units=("Units", "sum"), Sales=("Sales", "sum"),
                Avg_Current_km=("Current_Distance_km", "mean"),
                Avg_Alternative_km=("Nearest_Distance_km", "mean"))
           .reset_index())
    s["Distance_Reduction_%"] = (s["Avg_Current_km"] - s["Avg_Alternative_km"]) / s["Avg_Current_km"] * 100
    total = max(w_dist + w_vol + w_sales, 1e-9)
    s["Priority_Score"] = (w_dist * minmax(s["Distance_Reduction_%"]) + w_vol * minmax(s["Units"])
                           + w_sales * minmax(s["Sales"])) / total * 100
    s = s.sort_values("Priority_Score", ascending=False).reset_index(drop=True)
    s.insert(0, "Rank", s.index + 1)
    return s


def destination_summary(g: pd.DataFrame) -> pd.DataFrame:
    return (g.groupby("_key")
             .agg(City=("City", "first"), State=("State/Province", "first"),
                  Latitude=("Latitude", "first"), Longitude=("Longitude", "first"),
                  Units=("Units", "sum"), Sales=("Sales", "sum"),
                  Nearest_Factory=("Nearest_Factory", "first"),
                  Avg_Current_km=("Current_Distance_km", "mean"),
                  Nearest_km=("Nearest_Distance_km", "first"))
             .reset_index())


def base_map(height: int = 540) -> go.Figure:
    fig = go.Figure()
    fig.update_geos(scope="north america", lataxis_range=[23, 55], lonaxis_range=[-128, -55],
                    showcountries=True, countrycolor="#B9C0D0", showsubunits=True, subunitcolor="#DDE1EB",
                    landcolor="#EEF0F6", showlakes=True, lakecolor=PAPER, showocean=True, oceancolor="#F6F7FB",
                    bgcolor="rgba(0,0,0,0)", resolution=50)
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=0.02, x=0.01, bgcolor="rgba(255,255,255,0.8)"),
                      font=dict(family="Manrope, system-ui, sans-serif", color=INK))
    return fig


def add_factories(fig: go.Figure, names: list[str] | None = None) -> None:
    names = names or list(FACTORIES)
    fig.add_trace(go.Scattergeo(
        lat=[FACTORIES[n][0] for n in names], lon=[FACTORIES[n][1] for n in names],
        mode="markers+text", text=names, textposition="top center", name="Factories",
        marker=dict(symbol="star", size=17, color=[FACTORY_COLORS[n] for n in names],
                    line=dict(color="white", width=1.5)),
        hovertemplate="<b>%{text}</b><extra>Factory</extra>"))


def add_destinations(fig: go.Figure, d: pd.DataFrame, group_col: str, colors: dict, label=None) -> None:
    scale = 30 / np.sqrt(max(d["Units"].max(), 1))
    for key, part in d.groupby(group_col):
        fig.add_trace(go.Scattergeo(
            lat=part["Latitude"], lon=part["Longitude"], mode="markers",
            name=label(key) if label else str(key),
            marker=dict(size=np.sqrt(part["Units"]) * scale + 4, color=colors.get(key, SLATE),
                        opacity=0.72, line=dict(color="white", width=0.5)),
            customdata=np.column_stack([part["City"], part["State"], part["Units"], part["Avg_Current_km"].round(0)]),
            hovertemplate="<b>%{customdata[0]}, %{customdata[1]}</b><br>Units: %{customdata[2]:,}"
                          "<br>Avg distance now: %{customdata[3]:,} km<extra></extra>"))


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
st.sidebar.markdown("### Nassau Candy")
st.sidebar.caption("Factory reallocation and shipping optimization")


def get_bytes(slot: str) -> bytes | None:
    p = find_file(FILE_SLOTS[slot])
    return p.read_bytes() if p else None


file_bytes = {slot: get_bytes(slot) for slot in FILE_SLOTS}

raw_bytes, geo_bytes = file_bytes["raw"], file_bytes["geo"]

if raw_bytes is None or geo_bytes is None:
    st.error("The project data files were not found. Keep the `data` folder next to `app.py` with "
             "Nassau_Candy_Distributor.csv and factory_distance_comparison.csv inside it, then refresh.")
    st.stop()

try:
    data, info = build_dataset(raw_bytes, load_geo(geo_bytes),
                               load_dist(file_bytes["dist"]) if file_bytes["dist"] else None)
except Exception as exc:  # shown to the user instead of a stack trace
    st.error(f"Could not build the analysis. {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.markdown("### Filters")
dmin, dmax = data["Order Date"].min().date(), data["Order Date"].max().date()
date_range = st.sidebar.date_input("Order date", value=(dmin, dmax), min_value=dmin, max_value=dmax)


def pick(label: str, col: str) -> list[str]:
    options = sorted(data[col].dropna().unique())
    return st.sidebar.multiselect(label, options, default=options)


sel_div = pick("Division", "Division")
sel_reg = pick("Region", "Region")
sel_mode = pick("Ship mode", "Ship Mode")
sel_fac = pick("Current factory", "Factory")
sel_prod = pick("Product", "Product Name")

f = data.copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    f = f[(f["Order Date"].dt.date >= date_range[0]) & (f["Order Date"].dt.date <= date_range[1])]
f = f[f["Division"].isin(sel_div) & f["Region"].isin(sel_reg) & f["Ship Mode"].isin(sel_mode)
      & f["Factory"].isin(sel_fac) & f["Product Name"].isin(sel_prod)]

st.sidebar.caption(f"Showing {len(f):,} of {len(data):,} order lines")
if f.empty:
    st.warning("No orders match these filters. Widen the filters in the sidebar.")
    st.stop()
g = f[f["dist_ok"]]          # lines with a distance result
gm = g[g["geo_ok"]]            # lines that can also be drawn on a map

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
pct_near = g["Is_Nearest"].mean() * 100 if len(g) else 0
avg_now = g["Current_Distance_km"].mean() if len(g) else 0
avg_near = g["Nearest_Distance_km"].mean() if len(g) else 0
cut = (1 - avg_near / avg_now) * 100 if avg_now else 0

st.markdown(
    f"""<div class="hero">
<div class="hero-title">Factory reallocation and shipping optimization</div>
<div class="hero-sub">Nassau Candy Distributor: where each product is made, and how far it travels</div>
<div class="hero-finding">Only {pct_near:.1f}% of order lines ship from the factory closest to the customer. 
Because the rest travel farther than they need to, the average straight-line trip is {avg_now:,.0f} km today 
and would be {avg_near:,.0f} km from the nearest factory ({cut:.0f}% shorter).</div>
</div>""",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="notice"><b>Read this first.</b> Distances are straight lines, not road routes. Nobody has confirmed '
    'that the other factories can make each product or have room to do it, so every scenario below is a lead to '
    'investigate, not an approved move or a cost saving.</div>',
    unsafe_allow_html=True,
)

tab_over, tab_net, tab_scen, tab_sim, tab_cluster, tab_rec, tab_dq = st.tabs(
    ["Overview", "Factory network", "Reallocation scenarios", "What-if simulator", "Demand clusters",
     "Recommendations", "Data quality"]
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
with tab_over:
    sales, profit, units = f["Sales"].sum(), f["Gross Profit"].sum(), f["Units"].sum()
    c = st.columns(6)
    c[0].metric("Sales", money(sales))
    c[1].metric("Gross profit", money(profit), f"{profit / sales * 100:.1f}% margin", delta_color="off")
    c[2].metric("Units sold", f"{units:,}")
    c[3].metric("Orders", f"{f['Order ID'].nunique():,}")
    c[4].metric("Avg distance now", f"{avg_now:,.0f} km")
    c[5].metric("Avg to nearest factory", f"{avg_near:,.0f} km", f"-{cut:.0f}%", delta_color="inverse")
    st.write("")

    left, right = st.columns(2)
    with left:
        div = f.groupby("Division", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)
        fig = px.bar(div, x="Division", y="Sales", text_auto=".3s", title="Sales by division",
                     color_discrete_sequence=[SLATE])
        show(style(fig, legend=False))
    with right:
        reg = f.groupby("Region", as_index=False)[["Sales", "Gross Profit"]].sum().sort_values("Sales", ascending=False)
        fig = px.bar(reg, x="Region", y=["Sales", "Gross Profit"], barmode="group",
                     title="Sales and gross profit by region", color_discrete_sequence=[SLATE, TEAL])
        fig.update_layout(yaxis_title=None)
        show(style(fig))

    left, right = st.columns(2)
    with left:
        trend = f.groupby("Month", as_index=False)["Sales"].sum()
        fig = px.area(trend, x="Month", y="Sales", title="Monthly sales by order date",
                      color_discrete_sequence=[BERRY])
        fig.update_traces(line_width=2, fillcolor="rgba(181,41,95,0.12)")
        show(style(fig, legend=False))
    with right:
        mode = f.groupby("Ship Mode", as_index=False).agg(Orders=("Order ID", "nunique"), Sales=("Sales", "sum"))
        fig = px.bar(mode.sort_values("Orders"), x="Orders", y="Ship Mode", orientation="h", text_auto=",",
                     title="Orders by ship mode", color_discrete_sequence=[SLATE])
        show(style(fig, legend=False))

    st.markdown("#### Products and where they are made")
    prod = (f.groupby(["Product Name", "Factory", "Division"])
              .agg(Units=("Units", "sum"), Sales=("Sales", "sum"), Gross_Profit=("Gross Profit", "sum"),
                   Avg_Distance_km=("Current_Distance_km", "mean"))
              .reset_index().sort_values("Sales", ascending=False))
    prod["Margin_%"] = prod["Gross_Profit"] / prod["Sales"] * 100
    table(prod, column_config={
        "Sales": st.column_config.NumberColumn(format="$%.0f"),
        "Gross_Profit": st.column_config.NumberColumn("Gross profit", format="$%.0f"),
        "Margin_%": st.column_config.ProgressColumn("Margin", format="%.1f%%", min_value=0, max_value=100),
        "Avg_Distance_km": st.column_config.NumberColumn("Avg distance (km)", format="%.0f"),
        "Product Name": "Product",
    })

# ---------------------------------------------------------------------------
# Factory network
# ---------------------------------------------------------------------------
with tab_net:
    if gm.empty:
        st.info("No orders with a known destination location match the filters.")
    else:
        dest = destination_summary(gm)
        mode = st.radio("Colour destinations by", ["Nearest factory", "Average distance now"], horizontal=True)
        fig = base_map()
        if mode == "Nearest factory":
            add_destinations(fig, dest, "Nearest_Factory", FACTORY_COLORS, label=lambda k: f"Nearest: {k}")
        else:
            dest["Distance band"] = pd.cut(dest["Avg_Current_km"], [0, 500, 1000, 2000, 3000, 10000],
                                           labels=["Under 500 km", "500 to 1,000 km", "1,000 to 2,000 km",
                                                   "2,000 to 3,000 km", "Over 3,000 km"])
            band_colors = dict(zip(dest["Distance band"].cat.categories,
                                   ["#12857E", "#7FB77E", "#D9962B", "#C8603A", "#8E1B3F"]))
            add_destinations(fig, dest.dropna(subset=["Distance band"]), "Distance band", band_colors)
        add_factories(fig)
        show(fig)
        st.markdown('<p class="caption-note">Bubble size shows units ordered. Stars mark the five factories. '
                    'Hover over a bubble for the city and its average distance.</p>', unsafe_allow_html=True)

        fs = (f.groupby("Factory")
                .agg(Order_Lines=("Order ID", "size"), Units=("Units", "sum"), Sales=("Sales", "sum"),
                     Gross_Profit=("Gross Profit", "sum")).reset_index())
        fd = (g.groupby("Factory")
                .agg(Avg_Now=("Current_Distance_km", "mean"), Avg_Nearest=("Nearest_Distance_km", "mean"),
                     At_Nearest=("Is_Nearest", "mean")).reset_index())
        ft = fs.merge(fd, on="Factory", how="left")
        ft["Margin_%"] = ft["Gross_Profit"] / ft["Sales"] * 100
        ft["Potential_Reduction_%"] = (1 - ft["Avg_Nearest"] / ft["Avg_Now"]) * 100
        ft["At_Nearest"] = ft["At_Nearest"] * 100
        ft = ft.sort_values("Sales", ascending=False)

        left, right = st.columns(2)
        with left:
            long = ft.melt(id_vars="Factory", value_vars=["Avg_Now", "Avg_Nearest"], var_name="Measure", value_name="km")
            long["Measure"] = long["Measure"].map({"Avg_Now": "Distance now", "Avg_Nearest": "Distance to nearest factory"})
            fig2 = px.bar(long, x="Factory", y="km", color="Measure", barmode="group", text_auto=".0f",
                          title="Average distance to customers, by current factory (km)",
                          color_discrete_map={"Distance now": SLATE, "Distance to nearest factory": BERRY})
            show(style(fig2))
        with right:
            now = g.groupby("Factory")["Units"].sum().rename("Where it is made now")
            near = g.groupby("Nearest_Factory")["Units"].sum().rename("Where it would be made if nearest")
            load = pd.concat([now, near], axis=1).fillna(0).reset_index().rename(columns={"index": "Factory"})
            load = load.melt(id_vars="Factory", var_name="View", value_name="Units")
            fig3 = px.bar(load, x="Factory", y="Units", color="View", barmode="group",
                          title="Units by factory: today versus nearest-factory view",
                          color_discrete_map={"Where it is made now": SLATE, "Where it would be made if nearest": BERRY})
            show(style(fig3))
            st.markdown('<p class="caption-note">The second bar is a thought experiment. It ignores whether a factory '
                        'has the capacity or the recipes to take on that volume.</p>', unsafe_allow_html=True)

        table(ft, column_config={
            "Order_Lines": "Order lines", "Sales": st.column_config.NumberColumn(format="$%.0f"),
            "Gross_Profit": st.column_config.NumberColumn("Gross profit", format="$%.0f"),
            "Avg_Now": st.column_config.NumberColumn("Avg distance now (km)", format="%.0f"),
            "Avg_Nearest": st.column_config.NumberColumn("Avg to nearest (km)", format="%.0f"),
            "At_Nearest": st.column_config.ProgressColumn("Lines at nearest factory", format="%.1f%%", min_value=0, max_value=100),
            "Margin_%": st.column_config.NumberColumn("Margin", format="%.1f%%"),
            "Potential_Reduction_%": st.column_config.NumberColumn("Possible distance cut", format="%.1f%%"),
        })

# ---------------------------------------------------------------------------
# Reallocation scenarios
# ---------------------------------------------------------------------------
with tab_scen:
    st.markdown("#### Rank the scenarios")
    st.write("Each scenario asks: *what if the customers whose nearest factory is X were served from X instead of the "
             "factory that makes this product today?* Scenarios are scored on three things. Change the weights to "
             "see how the ranking reacts.")
    w1, w2, w3, w4 = st.columns([1, 1, 1, 1.3])
    w_dist = w1.slider("Distance cut weight", 0, 100, 40, 5)
    w_vol = w2.slider("Units weight", 0, 100, 35, 5)
    w_sales = w3.slider("Sales weight", 0, 100, 25, 5)
    wonka_only = w4.toggle("Only the five Wonka Bars", value=True,
                           help="Rank only the five Wonka Bar products. Turn off to include all products.")
    if w_dist + w_vol + w_sales == 0:
        st.warning("Set at least one weight above zero.")
    else:
        scen = rank_scenarios(g, w_dist, w_vol, w_sales, wonka_only)
        if scen.empty:
            st.info("No scenarios for the current filters.")
        else:
            top = scen.iloc[0]
            m = st.columns(4)
            m[0].metric("Scenarios ranked", f"{len(scen)}")
            m[1].metric("Top scenario", top["Product Name"].replace("Wonka Bar - ", "").replace("Wonka Bar -", ""))
            m[2].metric("Move", f"{top['Factory']} to {top['Nearest_Factory']}")
            m[3].metric("Priority score", f"{top['Priority_Score']:.1f} / 100")
            st.write("")

            plot = scen.head(10).copy()
            plot["Scenario"] = plot["Product Name"] + ":  " + plot["Factory"] + " to " + plot["Nearest_Factory"]
            fig = px.bar(plot.sort_values("Priority_Score"), x="Priority_Score", y="Scenario", orientation="h",
                         text=plot.sort_values("Priority_Score")["Priority_Score"].round(1),
                         color="Distance_Reduction_%", color_continuous_scale=["#C9CEE0", BERRY],
                         title="Top 10 scenarios by priority score")
            fig.update_layout(coloraxis_colorbar=dict(title="Distance<br>cut %"), xaxis_range=[0, 105], yaxis_title=None)
            show(style(fig, height=430, legend=False))

            table(scen, column_config={
                "Product Name": "Product", "Factory": "Made now at", "Nearest_Factory": "Nearest factory",
                "Order_Lines": "Order lines",
                "Sales": st.column_config.NumberColumn(format="$%.0f"),
                "Avg_Current_km": st.column_config.NumberColumn("Avg now (km)", format="%.0f"),
                "Avg_Alternative_km": st.column_config.NumberColumn("Avg alternative (km)", format="%.0f"),
                "Distance_Reduction_%": st.column_config.NumberColumn("Distance cut", format="%.1f%%"),
                "Priority_Score": st.column_config.ProgressColumn("Priority score", format="%.1f", min_value=0, max_value=100),
            })
            st.download_button("Download ranked scenarios (CSV)", scen.to_csv(index=False).encode(),
                               "factory_reallocation_scenarios.csv", "text/csv")
            st.markdown("#### Look closely at one scenario")
            labels = {int(r.Rank): f"#{int(r.Rank)}  {r['Product Name']}: {r.Factory} to {r.Nearest_Factory}"
                      for _, r in scen.iterrows()}
            choice = st.selectbox("Scenario", list(labels), format_func=lambda k: labels[k])
            row = scen[scen["Rank"] == choice].iloc[0]
            sub = g[(g["Product Name"] == row["Product Name"]) & (g["Factory"] == row["Factory"])
                    & (g["Nearest_Factory"] == row["Nearest_Factory"])]
            sd = destination_summary(sub[sub["geo_ok"]]).sort_values("Units", ascending=False)

            left, right = st.columns([1.5, 1])
            with left:
                fig = base_map(480)
                top_d = sd.head(40)
                for fac, colr, nm in [(row["Factory"], "#8A93A8", "Today"), (row["Nearest_Factory"], BERRY, "Alternative")]:
                    lat, lon = [], []
                    for _, r in top_d.iterrows():
                        lat += [FACTORIES[fac][0], r["Latitude"], None]
                        lon += [FACTORIES[fac][1], r["Longitude"], None]
                    fig.add_trace(go.Scattergeo(lat=lat, lon=lon, mode="lines", name=f"{nm}: {fac}",
                                                line=dict(width=1, color=colr), opacity=0.55, hoverinfo="skip"))
                fig.add_trace(go.Scattergeo(
                    lat=top_d["Latitude"], lon=top_d["Longitude"], mode="markers", name="Customer destinations",
                    marker=dict(size=np.sqrt(top_d["Units"]) * 1.6 + 4, color=INK, opacity=0.7),
                    text=top_d["City"] + ", " + top_d["State"],
                    hovertemplate="<b>%{text}</b><br>%{marker.size:.0f}<extra></extra>"))
                add_factories(fig, [row["Factory"], row["Nearest_Factory"]])
                show(fig)
                st.markdown('<p class="caption-note">Lines run from each factory to the 40 biggest destinations in '
                            'this scenario. Grey lines are today. Berry lines are the alternative.</p>', unsafe_allow_html=True)
            with right:
                st.metric("Units affected", f"{int(row['Units']):,}")
                st.metric("Destinations", f"{int(row['Destinations']):,}")
                st.metric("Average trip", f"{row['Avg_Alternative_km']:,.0f} km",
                          f"-{row['Distance_Reduction_%']:.0f}% from {row['Avg_Current_km']:,.0f} km", delta_color="inverse")
                states = sub.groupby("State/Province")["Units"].sum().sort_values(ascending=False).head(8).reset_index()
                fig = px.bar(states.sort_values("Units"), x="Units", y="State/Province", orientation="h",
                             title="Top states in this scenario", color_discrete_sequence=[SLATE])
                show(style(fig, height=300, legend=False))

# ---------------------------------------------------------------------------
# What-if simulator
# ---------------------------------------------------------------------------
with tab_sim:
    st.markdown("#### Test a sourcing idea")
    st.write("Pick a product and choose which factories could make it. Each order is then served from the closest "
             "allowed factory, and the average trip is compared with today. Start with all five factories to see "
             "the best case, then remove the ones that could not realistically make the product.")
    if gm.empty:
        st.info("No orders with a known destination location match the filters.")
    else:
        products = sorted(gm["Product Name"].unique())
        c1, c2 = st.columns([1, 2])
        prod_pick = c1.selectbox("Product", products, index=0)
        current = gm.loc[gm["Product Name"] == prod_pick, "Factory"].iloc[0]
        allowed = c2.multiselect("Factories allowed to make it", list(FACTORIES), default=list(FACTORIES))
        if not allowed:
            st.warning("Choose at least one factory.")
        else:
            p = gm[gm["Product Name"] == prod_pick].copy()
            cols = [f"d::{n}" for n in allowed]
            dist_mat = p[cols].to_numpy()
            p["Sim_Factory"] = np.array(allowed)[dist_mat.argmin(axis=1)]
            p["Sim_km"] = dist_mat.min(axis=1)
            w = p["Units"].to_numpy()
            now_km = np.average(p["Current_Distance_km"], weights=w)
            sim_km = np.average(p["Sim_km"], weights=w)
            change = (sim_km / now_km - 1) * 100 if now_km else 0
            moved = p.loc[p["Sim_Factory"] != p["Factory"], "Units"].sum()

            m = st.columns(4)
            m[0].metric("Made today at", current)
            m[1].metric("Average trip now", f"{now_km:,.0f} km")
            m[2].metric("Average trip in this idea", f"{sim_km:,.0f} km", f"{change:+.1f}%", delta_color="inverse")
            m[3].metric("Units that change factory", f"{int(moved):,}", f"{moved / p['Units'].sum() * 100:.0f}% of this product", delta_color="off")
            st.write("")

            left, right = st.columns(2)
            with left:
                share = (p.groupby("Sim_Factory")["Units"].sum().reindex(allowed).fillna(0).reset_index())
                share.columns = ["Factory", "Units"]
                fig = px.bar(share, x="Factory", y="Units", color="Factory", color_discrete_map=FACTORY_COLORS,
                             title="Units each factory would make in this idea", text_auto=",")
                show(style(fig, legend=False))
            with right:
                p["Closer"] = np.where(p["Sim_km"] < p["Current_Distance_km"] - 1, "Closer", "Same or farther")
                cl = p.groupby("Closer")["Units"].sum().reset_index()
                fig = px.pie(cl, names="Closer", values="Units", hole=0.55, title="Units that would travel less",
                             color="Closer", color_discrete_map={"Closer": TEAL, "Same or farther": "#C9CEE0"})
                show(style(fig))
            st.markdown('<p class="caption-note">Distances are straight lines, weighted by units. This tests geography only. '
                        'It does not include production cost, capacity, ingredients or freight rates.</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Demand clusters
# ---------------------------------------------------------------------------
with tab_cluster:
    st.markdown("#### Where demand clusters")
    st.write("K-Means groups customer destinations by location (on a sphere, so longitude wraps correctly). "
             "The best number of groups is the one with the highest silhouette score, which measures how cleanly the groups separate.")
    try:
        loc, loc_unique = location_table(data)
        scores = cluster_scores(loc_unique[["Latitude", "Longitude"]])
        best_k = int(scores.loc[scores["Silhouette score"].idxmax(), "Clusters"])

        left, right = st.columns([1, 1.6])
        with left:
            fig = px.line(scores, x="Clusters", y="Silhouette score", markers=True,
                          title="Silhouette score by number of groups", color_discrete_sequence=[SLATE])
            fig.add_vline(x=best_k, line_dash="dot", line_color=BERRY,
                          annotation_text=f"Best: {best_k}", annotation_position="top")
            show(style(fig, height=300, legend=False))
            k = st.slider("Number of groups to show", 2, 10, best_k)
            if k != best_k:
                st.caption(f"The highest score is at {best_k} groups. You are viewing {k}.")
        lab = cluster_labels(loc_unique[["Latitude", "Longitude"]], k)
        loc = loc.merge(lab, on=["Latitude", "Longitude"], how="left")
        dest = destination_summary(gm).merge(loc[["_key", "Cluster"]], on="_key", how="left") if len(gm) else pd.DataFrame()

        with right:
            if dest.empty:
                st.info("No orders with a known destination location match the filters.")
            else:
                fig = base_map(360)
                dest["Cluster"] = dest["Cluster"].astype(int)
                add_destinations(fig, dest, "Cluster", dict(enumerate(CLUSTER_COLORS)), label=lambda c: f"Group {c}")
                add_factories(fig)
                show(fig)

        if not dest.empty:
            cs = (dest.groupby("Cluster")
                      .agg(Destinations=("_key", "size"), Units=("Units", "sum"), Sales=("Sales", "sum"),
                           Avg_Latitude=("Latitude", "mean"), Avg_Longitude=("Longitude", "mean"),
                           Avg_Distance_Now_km=("Avg_Current_km", "mean"))
                      .reset_index())
            cs["Demand_Share_%"] = cs["Units"] / cs["Units"].sum() * 100
            left, right = st.columns([1.6, 1])
            with left:
                table(cs, column_config={
                    "Sales": st.column_config.NumberColumn(format="$%.0f"),
                    "Avg_Latitude": st.column_config.NumberColumn("Avg latitude", format="%.2f"),
                    "Avg_Longitude": st.column_config.NumberColumn("Avg longitude", format="%.2f"),
                    "Avg_Distance_Now_km": st.column_config.NumberColumn("Avg distance now (km)", format="%.0f"),
                    "Demand_Share_%": st.column_config.ProgressColumn("Share of demand", format="%.1f%%", min_value=0, max_value=100),
                })
            with right:
                fig = px.bar(cs, x=cs["Cluster"].astype(str), y="Units", color=cs["Cluster"].astype(str),
                             color_discrete_sequence=CLUSTER_COLORS, title="Units by group", text_auto=",")
                show(style(fig, height=280, legend=False))
    except ImportError:
        st.info("This tab needs scikit-learn. Install it with `pip install scikit-learn` and refresh.")

# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
with tab_rec:
    st.markdown("#### What to do next")
    st.write("These recommendations come straight from the data and change when you change the filters in the sidebar. "
             "Choose what matters most and the ranking follows.")
    PRESETS = {"Balanced": (40, 35, 25), "Shortest trips first": (70, 15, 15), "Biggest volume first": (15, 50, 35)}
    c1, c2, c3 = st.columns([1.6, 1, 1])
    focus = c1.radio("What matters most?", list(PRESETS), horizontal=True)
    top_n = c2.slider("Moves to recommend", 1, 5, 3)
    all_prod = c3.toggle("Include all products", value=False, help="Off: the five Wonka Bars only. On: every product.")
    rec = rank_scenarios(g, *PRESETS[focus], not all_prod)

    if rec.empty:
        st.info("No recommendations for the current filters. Widen the filters in the sidebar.")
    else:
        rec["Suggested action"] = np.where(rec["Priority_Score"] >= 75, "Pilot first",
                                  np.where(rec["Priority_Score"] >= 50, "Evaluate next", "Keep for later"))
        top_n = min(top_n, len(rec))

        st.markdown("##### Top moves to look at")
        for col, (_, r) in zip(st.columns(top_n), rec.head(top_n).iterrows()):
            with col:
                with st.container(border=True):
                    st.markdown(f"**#{int(r['Rank'])}  {r['Product Name']}**")
                    st.markdown(f"Make it at **{r['Nearest_Factory']}** instead of {r['Factory']}")
                    st.metric("Average trip", f"{r['Avg_Alternative_km']:,.0f} km",
                              f"-{r['Distance_Reduction_%']:.0f}% from {r['Avg_Current_km']:,.0f} km", delta_color="inverse")
                    st.caption(f"{int(r['Units']):,} units across {int(r['Destinations']):,} destinations. "
                               f"Priority score {r['Priority_Score']:.0f} out of 100. {r['Suggested action']}.")

        best = rec.iloc[0]
        best_sub = g[(g["Product Name"] == best["Product Name"]) & (g["Factory"] == best["Factory"])
                     & (g["Nearest_Factory"] == best["Nearest_Factory"])]
        best_states = best_sub.groupby("State/Province")["Units"].sum().sort_values(ascending=False).head(3).index.tolist()
        st.success(
            f"**Start here:** {best['Product Name']}. {int(best['Units']):,} units go to customers who live closer to "
            f"{best['Nearest_Factory']} than to {best['Factory']}. Because those trips are shorter by "
            f"{best['Distance_Reduction_%']:.0f}% on average, this is the clearest place to test. "
            + (f"A pilot could begin with {', '.join(best_states)}, where most of the volume is." if best_states else "")
        )

        left, right = st.columns(2)
        with left:
            pairs = (g[g["Factory"] != g["Nearest_Factory"]]
                     .groupby(["Factory", "Nearest_Factory"])
                     .agg(Units=("Units", "sum"), Destinations=("_key", "nunique"),
                          Avg_Now=("Current_Distance_km", "mean"), Avg_Alt=("Nearest_Distance_km", "mean"))
                     .reset_index().sort_values("Units", ascending=False).head(8))
            pairs["Move"] = pairs["Factory"] + " to " + pairs["Nearest_Factory"]
            fig = px.bar(pairs.sort_values("Units"), x="Units", y="Move", orientation="h", color="Nearest_Factory",
                         color_discrete_map=FACTORY_COLORS, text_auto=",",
                         title="Factory pairs with the most volume to shift")
            fig.update_layout(yaxis_title=None)
            show(style(fig, height=380, legend=False))
        with right:
            extra = (g.assign(Extra=g["Units"] * g["Distance_Gap_km"])
                      .groupby("State/Province")["Extra"].sum().sort_values(ascending=False))
            top_states = extra.head(8).reset_index()
            top_states.columns = ["State", "Extra"]
            share = extra.head(5).sum() / extra.sum() * 100 if extra.sum() > 0 else 0
            fig = px.bar(top_states.sort_values("Extra"), x="Extra", y="State", orientation="h",
                         title="Where the avoidable distance is biggest", color_discrete_sequence=[BERRY])
            fig.update_layout(xaxis_title="Extra distance (units x km)", yaxis_title=None)
            show(style(fig, height=380, legend=False))
            st.caption(f"The five states shown first account for {share:.0f}% of all avoidable distance.")

        st.markdown("##### Suggested plan")
        st.markdown(
            f"1. **Confirm the products can be made elsewhere.** Check recipes, equipment and approvals at "
            f"{best['Nearest_Factory']} for {best['Product Name']}.\n"
            "2. **Check capacity.** A factory can only take on new volume if it has spare production time and storage.\n"
            "3. **Use real costs.** Replace straight-line distance with road distance and freight rates, so the saving can be measured in money.\n"
            "4. **Fix the shipping dates.** Delivery time cannot be judged until order and ship dates are correct (see Data quality).\n"
            "5. **Run a small pilot.** Move one product to a few destinations, compare it with today, then decide whether to widen it."
        )

        with st.expander("All ranked moves with a suggested action", expanded=False):
            show_cols = ["Rank", "Product Name", "Factory", "Nearest_Factory", "Units", "Sales",
                         "Distance_Reduction_%", "Priority_Score", "Suggested action"]
            table(rec[show_cols], column_config={
                "Product Name": "Product", "Factory": "Made now at", "Nearest_Factory": "Nearest factory",
                "Sales": st.column_config.NumberColumn(format="$%.0f"),
                "Distance_Reduction_%": st.column_config.NumberColumn("Distance cut", format="%.1f%%"),
                "Priority_Score": st.column_config.ProgressColumn("Priority score", format="%.1f", min_value=0, max_value=100),
            })
            st.caption("Pilot first: score 75 or more. Evaluate next: 50 to 74. Keep for later: under 50.")
            st.download_button("Download recommendations (CSV)", rec.to_csv(index=False).encode(),
                               "recommendations.csv", "text/csv")

# ---------------------------------------------------------------------------
# Data quality and method
# ---------------------------------------------------------------------------
with tab_dq:
    lt = data["Lead Time Days"]
    flagged = (lt > 365).mean() * 100
    st.markdown("#### Shipping dates cannot be trusted")
    st.markdown(
        f"Every shipment in the file has a ship date that is **{lt.min():,.0f} to {lt.max():,.0f} days** after the order date "
        f"(median {lt.median():,.0f}). That is about {lt.median() / 365:.1f} years, and the pattern is the same for Same Day and "
        f"Standard Class. Because of this, the project does **not** use delivery time in any recommendation. "
        f"Only distance, units and sales are used. The dates should be checked at the source before any lead-time analysis."
    )
    m = st.columns(4)
    m[0].metric("Order lines", f"{info['n_raw']:,}")
    m[1].metric("Lead times over 1 year", f"{flagged:.0f}%")
    m[2].metric("Ship date before order date", f"{int((lt < 0).sum()):,}")
    m[3].metric("Lines not shown on maps", f"{info['n_no_coords']:,}")

    left, right = st.columns(2)
    with left:
        fig = px.histogram(data, x="Lead Time Days", color="Ship Mode", nbins=60, barmode="overlay", opacity=0.7,
                           title="Order-to-ship gap in days, by ship mode",
                           color_discrete_sequence=[SLATE, BERRY, TEAL, AMBER])
        show(style(fig))
    with right:
        cross = pd.crosstab(data["Order Date"].dt.year, data["Ship Date"].dt.year)
        fig = px.imshow(cross, text_auto=True, aspect="auto", color_continuous_scale=["#EEF0F6", SLATE],
                        labels=dict(x="Ship year", y="Order year", color="Lines"),
                        title="Order year against ship year")
        fig.update_layout(coloraxis_showscale=False)
        show(style(fig, legend=False))

    st.markdown("#### Data checks")
    checks = pd.DataFrame([
        ["Order lines in the file", f"{info['n_raw']:,}"],
        ["Lines whose product has no factory mapping (dropped)", f"{info['n_unmapped']:,}"],
        ["Unique destinations", f"{info['n_destinations']:,}"],
        ["Lines with no destination coordinates (left off maps and the simulator)", f"{info['n_no_coords']:,}"],
        ["Of those, lines whose distances came from distance_analysis.csv", f"{info['n_dist_filled']:,}"],
        ["Lines with no distance result at all", f"{info['n_no_dist']:,}"],
        ["Exact duplicate lines", f"{info['n_duplicates']:,}"],
        ["Rows where Sales differs from Gross Profit + Cost",
         f"{int((~np.isclose(data['Sales'] - data['Gross Profit'] - data['Cost'], 0)).sum()):,}"],
    ], columns=["Check", "Result"])
    table(checks)
    if info["geo_methods"]:
        st.caption("How destinations were located: " + ", ".join(f"{k}: {v}" for k, v in info["geo_methods"].items()))

    st.markdown("#### How this was built")
    st.markdown(
        "1. **Factory mapping.** The orders file has no factory column, so each product is matched to its factory using the project's mapping table.\n"
        "2. **Locations.** Each destination (city, state, postal code) has a latitude and longitude from OpenStreetMap, "
        "falling back to city level when a postal code was not found.\n"
        "3. **Distance.** Straight-line (haversine) distance from every destination to every factory.\n"
        "4. **Comparison.** For every order line, today's factory is compared with the nearest factory.\n"
        "5. **Scenarios.** Lines whose nearest factory differs from today's are grouped by product and factory pair, then scored on "
        "distance cut, units and sales (each scaled 0 to 1, then weighted).\n"
        "6. **Clusters.** K-Means on destination locations, with the group count chosen by silhouette score."
    )
    st.markdown("#### What this does not tell you")
    st.markdown(
        "- Whether another factory can make the product.\n"
        "- Whether a factory has spare capacity.\n"
        "- Road distance, freight cost or real delivery time.\n"
        "- The ranking depends on the weights you choose, so a different weighting can change the order.\n"
        "- Next steps: confirm product eligibility and capacity, get road distances and freight rates, fix the ship dates, "
        "then pilot only the scenarios that pass."
    )
    with st.expander("Factory locations and product mapping"):
        fl = pd.DataFrame([{"Factory": n, "Latitude": v[0], "Longitude": v[1]} for n, v in FACTORIES.items()])
        pm = pd.DataFrame(sorted(PRODUCT_TO_FACTORY.items(), key=lambda kv: (kv[1], kv[0])),
                          columns=["Product", "Factory"])
        a, b = st.columns(2)
        with a:
            table(fl)
        with b:
            table(pm)
    st.download_button("Download order-level distance comparison (CSV)",
                       g.drop(columns=[c for c in g.columns if c.startswith("d::") or c in ("_key", "Month")]).to_csv(index=False).encode(),
                       "factory_distance_comparison.csv", "text/csv")
