"""Streamlit theme configuration and CSS injection."""
import streamlit as st


def apply_custom_theme():
    """Apply custom dark theme with glassmorphic design."""
    st.markdown(
        """
        <style>
        /* Color variables matching original dashboard */
        :root {
            --bg0: #070A12;
            --bg1: #0B1630;
            --card: rgba(255,255,255,.06);
            --card2: rgba(255,255,255,.08);
            --border: rgba(255,255,255,.10);
            --text: rgba(255,255,255,.92);
            --muted: rgba(255,255,255,.70);
            --muted2: rgba(255,255,255,.55);
            --shadow: 0 20px 60px rgba(0,0,0,.45);
            --radius: 18px;

            --fair: #2ca02c;
            --peak: #d62728;
            --trough: #1f77b4;
            --ratio: #9467bd;
            --warn: #ffb020;
            --ok: #57d38c;
        }

        /* Main app background with gradient */
        .stApp {
            background:
                radial-gradient(1200px 700px at 20% 10%, rgba(148,103,189,.25), transparent 55%),
                radial-gradient(900px 600px at 80% 0%, rgba(31,119,180,.22), transparent 55%),
                radial-gradient(900px 700px at 50% 100%, rgba(44,160,44,.18), transparent 60%),
                linear-gradient(180deg, var(--bg0), var(--bg1));
        }

        /* Card styling */
        div[data-testid="stMetricValue"] {
            font-size: 24px;
            font-weight: 750;
            color: var(--text);
        }

        div[data-testid="stMetricLabel"] {
            font-size: 14px;
            color: var(--muted);
        }

        div[data-testid="stMetricDelta"] {
            font-size: 12px;
            color: var(--muted2);
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: var(--card);
            border-right: 1px solid var(--border);
        }

        /* Button styling */
        .stButton > button {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: var(--shadow);
        }

        .stButton > button:hover {
            border-color: rgba(255,255,255,.22);
            transform: translateY(-1px);
        }

        /* Selectbox and input styling */
        .stSelectbox > div > div,
        .stTextInput > div > div,
        .stDateInput > div > div,
        .stNumberInput > div > div {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
        }

        /* Expander styling */
        .streamlit-expanderHeader {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px 12px 0 0;
            color: var(--muted);
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background: var(--card2);
            color: var(--text);
            border-color: rgba(255,255,255,.18);
        }

        /* Header styling */
        h1, h2, h3 {
            color: var(--text) !important;
        }

        /* Hide Streamlit branding but keep header for mobile hamburger menu */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Custom metric cards */
        .metric-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 16px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(10px);
        }

        /* Status badge */
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid;
        }

        .status-badge.connected {
            background: rgba(87, 211, 140, 0.15);
            border-color: rgba(87, 211, 140, 0.35);
            color: var(--ok);
        }

        .status-badge.fallback {
            background: rgba(255, 176, 32, 0.15);
            border-color: rgba(255, 176, 32, 0.35);
            color: var(--warn);
        }

        /* Action tag */
        .action-tag {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .action-tag.buy {
            background: rgba(87, 211, 140, 0.15);
            border-color: rgba(87, 211, 140, 0.35);
            color: var(--ok);
        }

        .action-tag.sell {
            background: rgba(255, 176, 32, 0.15);
            border-color: rgba(255, 176, 32, 0.35);
            color: var(--warn);
        }

        .action-tag.hold {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.18);
            color: var(--muted);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_plotly_theme() -> dict:
    """
    Get Plotly theme configuration matching dark dashboard.

    Returns:
        Dictionary with Plotly layout defaults
    """
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "size": 11,
            "color": "rgba(255,255,255,.85)",
            "family": "system-ui, -apple-system, sans-serif",
        },
        "xaxis": {
            "showgrid": True,
            "gridcolor": "rgba(255,255,255,.06)",
            "tickfont": {"color": "rgba(255,255,255,.70)"},
            "zerolinecolor": "rgba(255,255,255,.10)",
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "rgba(255,255,255,.08)",
            "tickfont": {"color": "rgba(255,255,255,.70)"},
            "zerolinecolor": "rgba(255,255,255,.10)",
        },
        "margin": {"l": 48, "r": 18, "t": 10, "b": 35},
        "hovermode": "x unified",
        "hoverlabel": {
            "bgcolor": "rgba(20,20,30,0.95)",
            "font": {"size": 11, "color": "rgba(255,255,255,.92)"},
        },
    }


def get_chart_colors() -> dict:
    """
    Get color palette for charts.

    Returns:
        Dictionary with color codes
    """
    return {
        "price": "rgba(170,170,170,0.95)",
        "fair": "#2ca02c",
        "peak": "#d62728",
        "trough": "#1f77b4",
        "ratio": "#9467bd",
        "strat": "#57d38c",
        "hold": "rgba(170,170,170,0.70)",
        "weight": "#9467bd",
    }
