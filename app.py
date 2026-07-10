import streamlit as st
from db import DB
from survival_analysis import kaplan_meier_points
from datetime import date, timedelta
import altair as alt
import os
import re
import html
import pandas as pd
from urllib.parse import quote

st.set_page_config(page_title="Mouse Colony Manager", page_icon="🐭", layout="wide")

st.markdown("""
<style>
    :root {
        --lab-primary: #527da8;
        --lab-primary-hover: #466f98;
        --lab-primary-soft: #e8f0f8;
        --lab-border: #e1e7ef;
        --lab-page: #f7f8fa;
    }
    [data-testid="stAppViewContainer"] {
        background: var(--lab-page);
    }
    .block-container {
        max-width: 1240px;
        padding-top: 1.35rem;
        padding-bottom: 2rem;
    }
    .app-topbar {
        align-items: flex-end;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.7rem;
        padding-bottom: 0.75rem;
    }
    .app-title {
        color: #111827;
        font-size: 1.15rem;
        font-weight: 750;
        letter-spacing: 0;
        line-height: 1.2;
    }
    .app-subtitle {
        color: #6b7280;
        font-size: 0.82rem;
        margin-top: 0.15rem;
    }
    .page-header {
        margin: 0.85rem 0 0.7rem 0;
    }
    .page-header h1 {
        color: #111827;
        font-size: 1.45rem;
        font-weight: 760;
        letter-spacing: 0;
        line-height: 1.2;
        margin: 0;
    }
    .page-header p {
        color: #6b7280;
        font-size: 0.9rem;
        margin: 0.2rem 0 0 0;
    }
    div.stButton > button {
        min-height: 2.65rem;
        white-space: nowrap;
    }
    div.stButton > button[kind="primary"] {
        background: var(--lab-primary) !important;
        border-color: var(--lab-primary) !important;
        color: #ffffff !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: var(--lab-primary-hover) !important;
        border-color: var(--lab-primary-hover) !important;
        color: #ffffff !important;
    }
    [data-testid="stWidgetLabel"] p {
        color: #374151;
        font-size: 0.92rem;
        font-weight: 720;
    }
    .toolbar-count {
        align-items: center;
        color: #1f2937;
        display: flex;
        font-weight: 750;
        min-height: 2.65rem;
    }
    .empty-panel {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        margin: 0.75rem 0 0.85rem 0;
        padding: 0.9rem 1rem;
    }
    .empty-panel strong {
        color: #111827;
        display: block;
        font-size: 0.98rem;
        margin-bottom: 0.2rem;
    }
    .empty-panel span {
        color: #64748b;
        font-size: 0.88rem;
    }
    .summary-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #94a3b8;
        border-radius: 8px;
        min-height: 5.35rem;
        padding: 0.85rem 0.95rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .summary-card-blue { border-left-color: #2563eb; }
    .summary-card-green { border-left-color: #059669; }
    .summary-card-amber { border-left-color: #d97706; }
    .summary-card-red { border-left-color: #dc2626; }
    .summary-label {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    .summary-value {
        color: #111827;
        font-size: 1.9rem;
        font-weight: 780;
        line-height: 1.1;
        margin-top: 0.25rem;
    }
    .summary-detail {
        color: #64748b;
        font-size: 0.82rem;
        margin-top: 0.22rem;
    }
    .section-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        min-height: 9rem;
        padding: 0.9rem 1rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035);
    }
    .section-title {
        color: #111827;
        font-size: 1rem;
        font-weight: 750;
        margin-bottom: 0.55rem;
    }
    .soft-row {
        align-items: center;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        display: flex;
        justify-content: space-between;
        margin-top: 0.45rem;
        padding: 0.55rem 0.65rem;
    }
    .soft-row-title {
        color: #111827;
        font-size: 0.88rem;
        font-weight: 700;
    }
    .soft-row-meta {
        color: #64748b;
        font-size: 0.78rem;
        margin-top: 0.1rem;
    }
    .empty-note {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 6px;
        color: #64748b;
        font-size: 0.86rem;
        padding: 0.7rem 0.75rem;
    }
    .gene-chip-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
    }
    .gene-chip {
        align-items: center;
        background: #ffffff;
        border: 1px solid #dbe3ef;
        border-radius: 999px;
        display: inline-flex;
        gap: 0.4rem;
        padding: 0.28rem 0.35rem 0.28rem 0.65rem;
    }
    .gene-chip span:first-child {
        color: #1f2937;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .gene-chip-count {
        background: #2563eb;
        border-radius: 999px;
        color: #ffffff;
        font-size: 0.76rem;
        font-weight: 800;
        min-width: 1.4rem;
        padding: 0.08rem 0.42rem;
        text-align: center;
    }
    .gene-chip-stripe {
        border-radius: 999px;
        display: inline-block;
        height: 0.34rem;
        min-width: 1.25rem;
    }
    .gene-stripe {
        border-radius: 999px;
        height: 0.18rem;
        margin-top: 0.34rem;
        overflow: hidden;
        width: 100%;
    }
    .gene-stripe-empty {
        background: #edf1f5;
    }
    .mouse-card, .cage-card {
        background: #ffffff;
        border: 1px solid var(--lab-border);
        border-radius: 8px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.045);
        min-height: 7.1rem;
        padding: 0.75rem 0.8rem;
    }
    .mouse-card {
        cursor: pointer;
        min-height: 6.25rem;
        padding: 0.62rem 0.72rem;
        transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
    }
    .mouse-card:hover {
        border-color: #b9cbe0;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.07);
        transform: translateY(-1px);
    }
    .cage-card {
        cursor: pointer;
        display: flex;
        flex-direction: column;
        min-height: 11.25rem;
        overflow: visible;
        transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
    }
    .cage-card:hover {
        border-color: #b9cbe0;
        box-shadow: 0 9px 22px rgba(15, 23, 42, 0.075);
        transform: translateY(-1px);
    }
    div[class*="st-key-cage_click_"] {
        height: 12.25rem;
        margin-top: -12.25rem;
        position: relative;
        z-index: 3;
    }
    div[class*="st-key-cage_click_"] button {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: transparent !important;
        height: 12.25rem;
        min-height: 12.25rem;
        padding: 0 !important;
    }
    div[class*="st-key-cage_click_"] button:hover,
    div[class*="st-key-cage_click_"] button:focus {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: transparent !important;
    }
    div[class*="st-key-sel_mouse_"] {
        height: 7.15rem;
        margin-top: -7.15rem;
        position: relative;
        z-index: 3;
    }
    div[class*="st-key-sel_mouse_"] button {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: transparent !important;
        height: 7.15rem;
        min-height: 7.15rem;
        padding: 0 !important;
    }
    div[class*="st-key-sel_mouse_"] button:hover,
    div[class*="st-key-sel_mouse_"] button:focus {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: transparent !important;
    }
    .mouse-card-selected, .cage-card-selected {
        background: #f3f8fd;
        border-color: #8db4dc;
        box-shadow: 0 0 0 1px rgba(82, 125, 168, 0.18), 0 8px 20px rgba(15, 23, 42, 0.055);
    }
    .card-top {
        align-items: center;
        display: flex;
        gap: 0.45rem;
        justify-content: space-between;
    }
    .card-title {
        color: #111827;
        font-size: 0.98rem;
        font-weight: 820;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .card-meta {
        color: #5f6f84;
        font-size: 0.82rem;
        line-height: 1.3;
        margin-top: 0.25rem;
    }
    .card-genotype {
        color: #1f2937;
        font-size: 0.84rem;
        font-weight: 700;
        line-height: 1.34;
        margin-top: 0.32rem;
        min-height: 1.55rem;
        overflow: hidden;
    }
    .card-genotype-line {
        overflow: visible;
        white-space: normal;
        word-break: break-word;
    }
    .card-bottom-spacer {
        flex: 1;
        min-height: 0.65rem;
    }
    .status-pill, .sex-pill {
        border-radius: 999px;
        display: inline-block;
        font-size: 0.8rem;
        font-weight: 800;
        line-height: 1;
        padding: 0.34rem 0.62rem;
        white-space: nowrap;
    }
    .mouse-detail-header {
        margin: 0.2rem 0 0.35rem 0;
    }
    .mouse-detail-title {
        color: #111827;
        font-size: 1.05rem;
        font-weight: 820;
        line-height: 1.25;
    }
    .mouse-detail-grid {
        background: #ffffff;
        border: 1px solid #dfe6ef;
        border-radius: 8px;
        display: grid;
        gap: 0.45rem 0.75rem;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin: 0.35rem 0 0.55rem 0;
        padding: 0.65rem 0.75rem;
    }
    .mouse-detail-item {
        min-width: 0;
    }
    .mouse-detail-item:nth-child(9) {
        grid-column: 1 / -1;
    }
    .mouse-detail-label {
        color: #6b7280;
        font-size: 0.72rem;
        font-weight: 750;
        line-height: 1.15;
        margin-bottom: 0.12rem;
    }
    .mouse-detail-value {
        color: #1f2937;
        font-size: 0.86rem;
        font-weight: 680;
        line-height: 1.28;
        overflow-wrap: anywhere;
    }
    .detail-section-title {
        color: #1f2937;
        font-size: 0.95rem;
        font-weight: 820;
        margin: 0.45rem 0 0.15rem 0;
    }
    .compact-muted {
        color: #6b7280;
        font-size: 0.82rem;
        margin: 0.05rem 0 0.25rem 0;
    }
    div[data-testid="stForm"] {
        padding: 0.55rem 0.7rem 0.65rem;
    }
    div[data-testid="stTextArea"] textarea {
        min-height: 4.6rem !important;
    }
    div[data-testid="stExpander"] details {
        background: #ffffff;
        border-radius: 8px;
    }
    div[data-testid="stExpander"] summary {
        min-height: 2.4rem;
    }
    @media (max-width: 900px) {
        .mouse-detail-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    @media (max-width: 560px) {
        .mouse-detail-grid {
            grid-template-columns: 1fr;
        }
    }
    .sex-m { background: #dbeafe; color: #1d4ed8; }
    .sex-f { background: #fce7f3; color: #be185d; }
    .sex-u { background: #f1f5f9; color: #475569; }
    .tone-breeding { background: #e7e7ff; color: #4f46a6; }
    .tone-holding { background: #dff4fb; color: #087092; }
    .tone-waiting_split, .tone-soon, .tone-due { background: #fff0d6; color: #a65312; }
    .tone-overdue { background: #f8d7d4; color: #9d2f2a; }
    .tone-done { background: #dff4fb; color: #087092; }
    .tone-inactive { background: #edf1f5; color: #5c6674; }
    .tone-dead { background: #e5e7eb; color: #374151; }
    .tone-muted { background: #f1f5f9; color: #475569; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom-color: #e2e8f0; }
    .stTabs [data-baseweb="tab"] { color: #374151; padding: 0.35rem 0.65rem; font-size: 0.96rem; }
    .stTabs [aria-selected="true"] { color: var(--lab-primary) !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: var(--lab-primary) !important; }
    .cage-section-title {
        color: #1f2937;
        font-size: 1.02rem;
        font-weight: 820;
        margin: 1rem 0 0.45rem 0;
    }
    div[class*="st-key-cage_group_"] {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        margin: 0.55rem 0 1.1rem 0;
        padding: 0.85rem 0.95rem 1rem 0.95rem;
    }
    .cage-group-header {
        align-items: center;
        display: flex;
        gap: 0.85rem;
        justify-content: space-between;
        margin-bottom: 0.55rem;
    }
    .cage-group-title {
        align-items: center;
        display: flex;
        gap: 0.7rem;
        min-width: 0;
    }
    .cage-group-stripe {
        border-radius: 999px;
        display: inline-block;
        flex: 0 0 7.4rem;
        height: 0.36rem;
        overflow: hidden;
    }
    .cage-group-name {
        color: #111827;
        font-size: 1rem;
        font-weight: 820;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .cage-group-count {
        color: #64748b;
        flex: 0 0 auto;
        font-size: 0.82rem;
        font-weight: 720;
    }
    hr { margin: 0.75rem 0; }
    h3 { margin: 0.35rem 0 0.25rem 0; font-size: 1.08rem; }
    .stMarkdown { margin-bottom: 0; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.45rem; }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.7rem 0.85rem;
    }
    div[data-testid="stButton"] button {
        border-radius: 6px;
        font-weight: 650;
        min-height: 2.15rem;
        padding: 0.3rem 0.7rem;
    }
    .stSelectbox > div { min-height: unset; }
    .stMultiSelect > div { min-height: unset; }
    section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

db = DB()
WEANING_DAYS = 21

# ── Helpers ───────────────────────────────────────────────────────

STATUS_EMOJI = {
    "breeding": "🔵",
    "holding": "🟢",
    "waiting_split": "🟡",
    "dead": "⚫",
}
MOUSE_LIVE_STATUS_OPTIONS = ["breeding", "holding", "waiting_split"]
MOUSE_STATUS_OPTIONS = MOUSE_LIVE_STATUS_OPTIONS + ["dead"]
MOUSE_STATUS_LABELS = {
    "breeding": "breeding",
    "holding": "holding",
    "waiting_split": "waiting split",
    "dead": "dead",
}
DEATH_METHODS = ["Natural death", "Experimental harvest"]
COMMON_GENES = [
    # Add your default genes here, or manage them via ⚙️ Settings
]
ALLELE_SUGGESTIONS = {
    "floxed": ["fl", "+", "Δ"],
    "cre": ["Tg", "0"],
    "reporter": ["Tg", "0"],
    "default": ["?", "fl", "+", "Tg", "0", "WT", "KO"],
}
ALLELE_OPTIONS = ["+", "-", "?", "fl", "Δ", "Tg", "0", "WT", "KO", "Other..."]


def allele_input(label, key, default="?", compact=False):
    """Selectable allele with optional custom text fallback."""
    opts = list(ALLELE_OPTIONS)
    if default not in opts and default:
        opts.insert(-1, default)
    choice = st.selectbox(
        label, opts,
        index=opts.index(default) if default in opts else 0,
        key=key,
        label_visibility="collapsed" if compact else "visible",
    )
    if choice == "Other...":
        return st.text_input(f"{label} (custom)", value=default, key=f"{key}_custom")
    return choice


def compact_genotype_inputs(prefix="", genes=None):
    """Compact 3-gene input: 3 columns, each stacks gene + 2 alleles.
    Returns list of (gene, allele1, allele2) for non-empty genes."""
    if genes is None:
        genes = gene_choices()
    results = []
    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            gene = st.selectbox(f"Gene {i+1}", [""] + genes, key=f"{prefix}g{i}", label_visibility="collapsed", placeholder="Gene...")
            a1 = allele_input("Allele 1", key=f"{prefix}a{i}_1")
            a2 = allele_input("Allele 2", key=f"{prefix}a{i}_2")
            if gene:
                results.append((gene, a1, a2))
    return results


def genotype_summary(mouse_id):
    rows = db.get_mouse_genotypes(mouse_id)
    if not rows:
        return "—"
    parts = []
    for r in rows:
        parts.append(f"{r['gene']} {r['allele1']}/{r['allele2']}")
    return "; ".join(parts)


GENE_COLORS = [
    # festival-of-lights
    "#FF4500",
    "#FFD700",
    "#FF69B4",
    "#00FF00",
    "#00FFFF",
    "#FF00FF",
    "#1E90FF",
    "#FF8C00",
    "#ADFF2F",
    # fiesta-celebration
    "#E4007C",
    "#FFED00",
    "#00AEEF",
    "#F26C24",
    "#8DC63F",
    "#662D91",
    "#EC008C",
    "#FFF200",
]

DEFAULT_GENE_COLOR_OVERRIDES = {
    "cag": "#662D91",
    "lamp1": "#FFD700",
    "ng2dsred": "#FF4500",
    "pdgfrb": "#1E90FF",
    "pex3c": "#8DC63F",
    "ai14": "#E4007C",
    "cdh5": "#00FFFF",
    "pex26d": "#FF8C00",
}
GENE_COLOR_OVERRIDES_CACHE = None


def stable_gene_index(gene):
    total = 0
    for char in str(gene or "").strip().lower():
        total = (total * 31 + ord(char)) % 1000003
    return total


def gene_color_key(gene):
    return re.sub(r"\s+", " ", str(gene or "").strip().lower()).replace("β", "b")


def normalize_hex_color(color):
    color = str(color or "").strip()
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", color)
    if not match:
        return None
    return f"#{match.group(1).upper()}"


def color_from_overrides(gene, overrides):
    key = gene_color_key(gene)
    base_key = re.sub(r"-(creert2|creer|cre)$", "", key)
    if key in overrides:
        return normalize_hex_color(overrides[key])
    if base_key in overrides:
        return normalize_hex_color(overrides[base_key])
    return None


def default_gene_color(gene):
    if not gene:
        return "#EDF1F5"
    override = color_from_overrides(gene, DEFAULT_GENE_COLOR_OVERRIDES)
    if override:
        return override
    return GENE_COLORS[stable_gene_index(gene) % len(GENE_COLORS)]


def configured_gene_color_overrides():
    global GENE_COLOR_OVERRIDES_CACHE
    if GENE_COLOR_OVERRIDES_CACHE is None:
        overrides = dict(DEFAULT_GENE_COLOR_OVERRIDES)
        for gene, color in db.get_gene_colors().items():
            clean_color = normalize_hex_color(color)
            if clean_color:
                overrides[gene_color_key(gene)] = clean_color
        GENE_COLOR_OVERRIDES_CACHE = overrides
    return GENE_COLOR_OVERRIDES_CACHE


def gene_color(gene):
    if not gene:
        return "#EDF1F5"
    override = color_from_overrides(gene, configured_gene_color_overrides())
    if override:
        return override
    return GENE_COLORS[stable_gene_index(gene) % len(GENE_COLORS)]


def normalize_gene_names(genes):
    clean = []
    seen = set()
    for gene in genes or []:
        gene = str(gene or "").strip()
        key = gene.lower()
        if gene and key not in seen:
            clean.append(gene)
            seen.add(key)
    return sorted(clean, key=str.lower)


def mouse_gene_names(mouse_id):
    return normalize_gene_names([row["gene"] for row in db.get_mouse_genotypes(mouse_id)])


def gene_stripe_style(genes):
    genes = normalize_gene_names(genes)
    if not genes:
        return "background:#edf1f5;"
    if len(genes) == 1:
        return f"background:{gene_color(genes[0])};"
    segment = 100 / len(genes)
    stops = []
    for index, gene in enumerate(genes):
        start = index * segment
        end = (index + 1) * segment
        color = gene_color(gene)
        stops.append(f"{color} {start:.2f}%")
        stops.append(f"{color} {end:.2f}%")
    return "background:linear-gradient(90deg," + ",".join(stops) + ");"


def gene_stripe_html(genes, title=""):
    genes = normalize_gene_names(genes)
    title_attr = esc(title or ", ".join(genes) or "No genotype")
    class_name = "gene-stripe" if genes else "gene-stripe gene-stripe-empty"
    return f'<div class="{class_name}" style="{gene_stripe_style(genes)}" title="{title_attr}"></div>'


def gene_stripe_chip_html(genes):
    genes = normalize_gene_names(genes)
    if not genes:
        return ""
    return f'<span class="gene-chip-stripe" style="{gene_stripe_style(genes)}"></span>'


def gene_stripe_data_uri(genes):
    genes = normalize_gene_names(genes)
    width = 42
    height = 6
    if not genes:
        rects = f'<rect x="0" y="0" width="{width}" height="{height}" rx="3" fill="#edf1f5"/>'
    else:
        segment = width / len(genes)
        rects = ""
        for index, gene in enumerate(genes):
            x = index * segment
            rects += (
                f'<rect x="{x:.2f}" y="0" width="{segment + 0.5:.2f}" '
                f'height="{height}" fill="{gene_color(gene)}"/>'
            )
        rects = f'<clipPath id="r"><rect width="{width}" height="{height}" rx="3"/></clipPath><g clip-path="url(#r)">{rects}</g>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{rects}</svg>'
    return "data:image/svg+xml;utf8," + quote(svg)


def mouse_age_label(birth_date, today=None):
    birth = parse_date(birth_date)
    if not birth:
        return "?d"
    days = ((today or date.today()) - birth).days
    return f"{days}d"


def sex_display(sex):
    return {
        "M": "Male ♂",
        "F": "Female ♀",
        "U": "Unknown",
    }.get(sex or "U", "Unknown")


def sex_symbol(sex):
    return {"M": "♂", "F": "♀"}.get(sex or "U", "?")


def sex_option_label(value):
    if value == "All":
        return "All"
    if value == "Mix":
        return "Mixed ♂♀"
    if value == "—":
        return "—"
    return sex_display(value)


def female_tag_list(cage):
    if not cage:
        return []
    try:
        raw_tags = cage["female_tags"]
    except (KeyError, IndexError):
        raw_tags = None
    if not raw_tags:
        return []
    return [tag.strip() for tag in str(raw_tags).split(",") if tag.strip()]


def mouse_display_title(mouse):
    geno = genotype_summary(mouse["id"])
    return (
        f"{mouse['ear_tag']}-{mouse_age_label(mouse['birth_date'])}-"
        f"{sex_display(mouse['sex'])}--{geno} - {MOUSE_STATUS_LABELS.get(mouse['status'], mouse['status'])}"
    )


def copy_table_editor_sex_date(count, default_birth):
    if count <= 1:
        return
    first_sex = st.session_state.get("te_sex_0", "M")
    first_birth = st.session_state.get("te_birth_0", default_birth)
    for i in range(1, count):
        st.session_state[f"te_sex_{i}"] = first_sex
        st.session_state[f"te_birth_{i}"] = first_birth


def copy_table_editor_genotypes(count, gene_count):
    if count <= 1:
        return
    for gi in range(gene_count):
        a1_key = f"te_a1_{gi}_0"
        a2_key = f"te_a2_{gi}_0"
        a1_val = st.session_state.get(a1_key, "?")
        a2_val = st.session_state.get(a2_key, "?")
        a1_custom = st.session_state.get(f"{a1_key}_custom", "")
        a2_custom = st.session_state.get(f"{a2_key}_custom", "")
        for i in range(1, count):
            st.session_state[f"te_a1_{gi}_{i}"] = a1_val
            st.session_state[f"te_a2_{gi}_{i}"] = a2_val
            st.session_state[f"te_a1_{gi}_{i}_custom"] = a1_custom
            st.session_state[f"te_a2_{gi}_{i}_custom"] = a2_custom


def queue_bulk_import_notice(message, level="success"):
    notices = st.session_state.get("bulk_import_notices", [])
    notices.append({"message": message, "level": level})
    st.session_state.bulk_import_notices = notices


def render_bulk_import_notices():
    notices = st.session_state.pop("bulk_import_notices", [])
    for notice in notices:
        level = notice.get("level", "success")
        message = notice.get("message", "")
        if level == "warning":
            st.warning(message)
        elif level == "error":
            st.error(message)
        elif level == "info":
            st.info(message)
        else:
            st.success(message)


def import_result_message(action, tags):
    if not tags:
        return f"{action} 0 mice."
    preview = ", ".join(tags[:6])
    if len(tags) > 6:
        preview += f", +{len(tags) - 6} more"
    return f"{action} {len(tags)} mice: {preview}"


def zygosity(a1, a2):
    if a1 == "?" or a2 == "?":
        return "?"
    if a1 == a2:
        return "Homo"
    return "Het"


def status_badge(status):
    emoji = STATUS_EMOJI.get(status, "")
    label = MOUSE_STATUS_LABELS.get(status, status)
    return f"{emoji} {label}".strip()


def normalize_mouse_status(status, default="holding"):
    status = (status or default).strip()
    aliases = {
        "active": "holding",
        "assigned": "holding",
        "genotyping": "waiting_split",
        "waiting split": "waiting_split",
        "waiting": "waiting_split",
    }
    status = aliases.get(status, status)
    return status if status in MOUSE_STATUS_OPTIONS else default


def parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def parse_excel_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    normalized = value.replace("/", "-").replace(".", "-")
    parts = normalized.split("-")
    if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
        year, month, day = [int(p.strip()) for p in parts]
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return parse_date(normalized)


def normalize_excel_sex(value):
    raw = str(value or "").strip()
    lowered = raw.lower()
    if raw in ("♀", "女") or lowered in ("f", "female"):
        return "F"
    if raw in ("♂", "男") or lowered in ("m", "male"):
        return "M"
    if lowered in ("u", "unknown", "?"):
        return "U"
    return None


def parse_excel_genotype(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("／", "/").replace("\\", "/")
    compact = raw.replace(" ", "")
    compact_lower = compact.lower()
    if compact_lower in ("+", "pos", "positive", "阳性"):
        return "+", "0"
    if compact_lower in ("-", "neg", "negative", "阴性"):
        return "0", "0"
    if "/" in compact:
        bits = [b.strip() for b in compact.split("/", 1)]
        return bits[0] or "?", bits[1] or "?"
    return compact, "?"


def split_excel_line(line, delimiter):
    if delimiter == "Comma":
        return [p.strip() for p in line.split(",")]
    return [p.strip() for p in line.split("\t")]


def find_excel_header(lines, delimiter):
    for index, line in enumerate(lines):
        cells = split_excel_line(line, delimiter)
        normalized = [c.strip().lower() for c in cells]
        if "id" in normalized and "gender" in normalized and "dob" in normalized:
            return index, cells
    return None, []


def parse_excel_genotype_table(data_text, delimiter="Tab"):
    lines = [line.rstrip("\n") for line in data_text.splitlines() if line.strip()]
    header_index, headers = find_excel_header(lines, delimiter)
    if header_index is None:
        return {
            "rows": [],
            "genes": [],
            "errors": ["Could not find a header row with id, gender, and DOB."],
        }

    normalized_headers = [h.strip().lower() for h in headers]
    id_col = normalized_headers.index("id")
    gender_col = normalized_headers.index("gender")
    dob_col = normalized_headers.index("dob")
    gene_cols = [
        (i, h.strip())
        for i, h in enumerate(headers)
        if i not in (id_col, gender_col, dob_col) and h.strip()
    ]

    rows = []
    errors = []
    for visual_row, line in enumerate(lines[header_index + 1:], start=header_index + 2):
        cells = split_excel_line(line, delimiter)
        if not any(cells):
            continue
        max_col = max([id_col, gender_col, dob_col] + [i for i, _ in gene_cols])
        if len(cells) <= max_col:
            errors.append(f"Row {visual_row}: expected {max_col + 1} columns, got {len(cells)}.")
            continue

        source_id = cells[id_col].strip()
        sex = normalize_excel_sex(cells[gender_col])
        birth = parse_excel_date(cells[dob_col])
        if not source_id:
            errors.append(f"Row {visual_row}: missing id.")
        if sex is None:
            errors.append(f"Row {visual_row}: cannot parse gender '{cells[gender_col]}'.")
        if birth is None:
            errors.append(f"Row {visual_row}: cannot parse DOB '{cells[dob_col]}'.")

        genotypes = []
        for col_index, gene in gene_cols:
            parsed = parse_excel_genotype(cells[col_index])
            if parsed:
                genotypes.append((gene, parsed[0], parsed[1]))

        rows.append(
            {
                "row": visual_row,
                "source_id": source_id,
                "sex": sex,
                "birth_date": str(birth) if birth else "",
                "genotypes": genotypes,
            }
        )

    return {
        "rows": rows,
        "genes": [gene for _, gene in gene_cols],
        "errors": errors,
    }


def excel_prefixed_tag(prefix, source_id):
    prefix = str(prefix or "").strip()
    source_id = str(source_id or "").strip()
    if not prefix or not source_id:
        return ""
    separator = "" if prefix.endswith(("-", "_")) else "-"
    return f"{prefix}{separator}{source_id}"


def validate_excel_import_tags(rows, tag_prefix):
    errors = []
    prepared_rows = []
    clean_prefix = str(tag_prefix or "").strip()
    if rows and not clean_prefix:
        errors.append("Suggested ID Prefix is required.")

    for row in rows:
        prepared = dict(row)
        prepared["tag"] = excel_prefixed_tag(clean_prefix, row.get("source_id"))
        prepared_rows.append(prepared)

    tags = [row["tag"] for row in prepared_rows if row["tag"]]
    duplicate_tags = sorted({tag for tag in tags if tags.count(tag) > 1})
    if duplicate_tags:
        errors.append("Duplicate generated Ear Tag / ID in pasted table: " + ", ".join(duplicate_tags))
    existing_tags = db.find_existing_ear_tags(tags)
    if existing_tags:
        errors.append("Ear Tag / ID already exists: " + ", ".join(existing_tags))

    return prepared_rows, errors


def litter_due_date(litter):
    birth = parse_date(litter["birth_date"])
    return birth + timedelta(days=WEANING_DAYS) if birth else None


def litter_age_days(litter, today=None):
    birth = parse_date(litter["birth_date"])
    if not birth:
        return None
    return ((today or date.today()) - birth).days


def litter_split_status(litter, today=None):
    if litter["weaning_date"]:
        return "Split"
    today = today or date.today()
    due = litter_due_date(litter)
    age = litter_age_days(litter, today)
    if not due or age is None:
        return "No date"
    delta = (due - today).days
    if delta > 0:
        return f"Day {age} · split in {delta}d"
    if delta == 0:
        return "Due today"
    return f"Overdue {abs(delta)}d"


def litter_split_tone(litter, today=None):
    if litter["weaning_date"]:
        return "done"
    due = litter_due_date(litter)
    if not due:
        return "muted"
    delta = (due - (today or date.today())).days
    if delta < 0:
        return "overdue"
    if delta == 0:
        return "due"
    if delta <= 3:
        return "soon"
    return "muted"


def split_reminder_status(reminder, today=None):
    if reminder["resolved"]:
        return "Done"
    today = today or date.today()
    due = parse_date(reminder["due_date"])
    if not due:
        return "No date"
    delta = (due - today).days
    if delta > 0:
        return f"Split in {delta}d"
    if delta == 0:
        return "Due today"
    return f"Overdue {abs(delta)}d"


def split_reminder_tone(reminder, today=None):
    if reminder["resolved"]:
        return "done"
    due = parse_date(reminder["due_date"])
    if not due:
        return "muted"
    delta = (due - (today or date.today())).days
    if delta < 0:
        return "overdue"
    if delta == 0:
        return "due"
    if delta <= 3:
        return "soon"
    return "muted"


def generated_pup_tags(prefix, start_number, count):
    prefix = prefix.strip()
    if not prefix or count <= 0:
        return []
    separator = "" if prefix.endswith(("-", "_")) else "-"
    return [f"{prefix}{separator}{int(start_number) + i:03d}" for i in range(int(count))]


def gene_id_prefix(genes):
    parts = []
    seen = set()
    for gene in genes:
        part = gene.strip().split("-", 1)[0].strip()
        part = re.sub(r"(?i)(creer|creert2|cre)$", "", part).strip("-_ ")
        if part and part.lower() not in seen:
            parts.append(part)
            seen.add(part.lower())
    return "-".join(parts) if parts else "M"


def gene_choices(extra=None):
    choices = []
    seen = set()
    for gene in list(extra or []) + db.get_custom_genes() + db.get_distinct_genes() + COMMON_GENES:
        gene = (gene or "").strip()
        key = gene.lower()
        if gene and key not in seen:
            choices.append(gene)
            seen.add(key)
    return choices


def preview_tags(tags, limit=8):
    if len(tags) <= limit:
        return ", ".join(tags)
    return ", ".join(tags[:4] + ["..."] + tags[-2:])


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def render_summary_card(label, value, detail="", tone="blue"):
    st.markdown(
        f"""
        <div class="summary-card summary-card-{esc(tone)}">
            <div class="summary-label">{esc(label)}</div>
            <div class="summary-value">{esc(value)}</div>
            <div class="summary-detail">{esc(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_card(title, body_html):
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{esc(title)}</div>
            {body_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def soft_row(title, meta, badge="", badge_tone="muted"):
    badge_html = (
        f'<span class="status-pill tone-{esc(badge_tone)}">{esc(badge)}</span>'
        if badge else ""
    )
    return (
        '<div class="soft-row">'
        '<div>'
        f'<div class="soft-row-title">{esc(title)}</div>'
        f'<div class="soft-row-meta">{esc(meta)}</div>'
        '</div>'
        f'{badge_html}'
        '</div>'
    )


def render_empty_note(text):
    return f'<div class="empty-note">{esc(text)}</div>'


def due_litters(today=None):
    today = today or date.today()
    items = []
    for litter in db.get_all_litters():
        due = litter_due_date(litter)
        if not litter["weaning_date"] and due and due <= today:
            items.append((litter, due))
    return items


def due_split_reminders(today=None):
    today = today or date.today()
    items = []
    for reminder in db.get_all_split_reminders(active_only=True):
        due = parse_date(reminder["due_date"])
        if due and due <= today:
            items.append((reminder, due))
    return items


def gene_combo_stats(mouse_ids=None):
    from collections import defaultdict

    if mouse_ids is not None:
        mouse_ids = set(mouse_ids)
    grouped = defaultdict(list)
    for row in db.get_all_genotypes():
        if mouse_ids is not None and row["mouse_id"] not in mouse_ids:
            continue
        grouped[row["mouse_id"]].append(row)

    combo_counts = defaultdict(int)

    for genos in grouped.values():
        distinct_genes = sorted({g["gene"] for g in genos})
        if not distinct_genes:
            continue
        genes = " + ".join(distinct_genes)
        combo_counts[genes] += 1

    rows = [{"Genes": genes, "Count": count} for genes, count in combo_counts.items()]
    rows.sort(key=lambda r: (-r["Count"], r["Genes"]))
    return rows


def gene_chip_counts_html(rows, empty_text):
    if not rows:
        return render_empty_note(empty_text)
    chips_html = '<div class="gene-chip-wrap">'
    for row in rows:
        genes = [gene.strip() for gene in row["Genes"].split(" + ") if gene.strip()]
        chips_html += (
            f'<div class="gene-chip">'
            f'{gene_stripe_chip_html(genes)}'
            f'<span>{esc(row["Genes"])}</span>'
            f'<span class="gene-chip-count">{esc(row["Count"])}</span>'
            f'</div>'
        )
    chips_html += '</div>'
    return chips_html


def cage_gene_set(cage):
    genes = set()
    for mouse in cage_mice(cage):
        for genotype in db.get_mouse_genotypes(mouse["id"]):
            genes.add(genotype["gene"])
    return genes


def cage_gene_names(cage):
    genes = set()
    for mouse in cage_mice(cage):
        genes.update(mouse_gene_names(mouse["id"]))
    return normalize_gene_names(genes)


def cage_mice(cage):
    # birth_cage_id is historical provenance. Current membership comes from
    # parent/member links and the mouse's current cage location only.
    return list(db.get_current_cage_mice(cage["id"]))


def mouse_option_label(mouse):
    geno = genotype_summary(mouse["id"])
    geno_text = f" · {geno}" if geno != "—" else ""
    location = mouse["cage_location"] or "unassigned"
    return f"{mouse['ear_tag']} ({sex_display(mouse['sex'])}, {mouse_age_label(mouse['birth_date'])}, {location}{geno_text})"


def mouse_label_maps(mice):
    label_to_id = {mouse_option_label(m): m["id"] for m in mice}
    id_to_label = {m["id"]: mouse_option_label(m) for m in mice}
    return label_to_id, id_to_label


def short_mouse_label_maps(mice):
    label_to_id = {str(m["ear_tag"]): m["id"] for m in mice}
    id_to_label = {m["id"]: str(m["ear_tag"]) for m in mice}
    return label_to_id, id_to_label


def assign_mice_to_cage(cage, mouse_ids, cage_type, cage_label):
    """Sync selected cage members while preserving non-member mice born/recorded in the cage."""
    mouse_ids = {mid for mid in mouse_ids if mid is not None}
    old_label = cage["cage_label"]
    old_assigned_ids = set()
    if cage["male_id"]:
        old_assigned_ids.add(cage["male_id"])
    old_assigned_ids.update(m["id"] for m in db.get_cage_females(cage["id"]))
    if cage_type == "holding":
        old_assigned_ids.update(
            m["id"] for m in db.get_all_mice()
            if m["cage_location"] == old_label
        )

    for mouse in db.get_all_mice():
        if mouse["cage_location"] == old_label:
            if old_label != cage_label:
                db.update_mouse(mouse["id"], cage_location=cage_label)
            if mouse["id"] in old_assigned_ids and mouse["id"] not in mouse_ids:
                db.update_mouse(
                    mouse["id"],
                    cage_location=None,
                    status="holding" if mouse["status"] == "breeding" else mouse["status"],
                )

    status = "breeding" if cage_type == "breeding" else "holding"
    for mouse_id in mouse_ids:
        db.update_mouse(mouse_id, status=status, cage_location=cage_label)


def unlink_mice_from_cage_links(mouse_ids, keep_cage_id=None):
    mouse_ids = {mid for mid in mouse_ids if mid is not None}
    if not mouse_ids:
        return
    for cage in db.get_all_breeding_cages():
        if keep_cage_id is not None and cage["id"] == keep_cage_id:
            continue
        if cage["male_id"] in mouse_ids:
            db.update_breeding_cage(cage["id"], male_id=None)
        current_females = db.get_cage_females(cage["id"])
        kept_female_ids = [m["id"] for m in current_females if m["id"] not in mouse_ids]
        if len(kept_female_ids) != len(current_females):
            db.set_cage_females(cage["id"], kept_female_ids)


def assign_table_mice_to_cage(mouse_ids, cage):
    mouse_ids = [mid for mid in mouse_ids if mid is not None]
    if not mouse_ids:
        return 0

    unlink_mice_from_cage_links(mouse_ids, keep_cage_id=cage["id"])
    parent_ids = {cage["male_id"]} if cage["male_id"] else set()
    if cage["cage_type"] == "breeding":
        parent_ids.update(m["id"] for m in db.get_cage_females(cage["id"]))
    for mouse_id in mouse_ids:
        if cage["cage_type"] == "holding":
            target_status = "holding"
        else:
            target_status = "breeding" if mouse_id in parent_ids else "waiting_split"
        db.update_mouse(mouse_id, status=target_status, cage_location=cage["cage_label"])

    if cage["cage_type"] == "holding":
        current_ids = [m["id"] for m in db.get_cage_females(cage["id"])]
        merged_ids = list(dict.fromkeys(current_ids + mouse_ids))
        db.set_cage_females(cage["id"], merged_ids)

    return len(mouse_ids)


def cage_assignment_option_label(cage):
    cage_type = "Breeding" if cage["cage_type"] == "breeding" else "Holding"
    return f"{cage['cage_label']} · {cage_type} · {len(cage_mice(cage))} mice"


def inject_cage_styles():
    st.markdown(
        """
        <style>
        .cage-meta {
            color: #5f6368;
            font-size: 0.9rem;
            line-height: 1.35;
        }
        .cage-status {
            border-radius: 999px;
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 700;
            margin-top: 0.35rem;
            padding: 0.18rem 0.55rem;
        }
        .cage-status-muted { background: #edf2f7; color: #334155; }
        .cage-status-soon { background: #fff7d6; color: #8a5a00; }
        .cage-status-due { background: #ffe9bc; color: #8a4b00; }
        .cage-status-overdue { background: #ffe1df; color: #9f1d1d; }
        .cage-status-done { background: #dff7ea; color: #17633a; }
        .cage-status-breeding { background: #dbeafe; color: #1e40af; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_pedigree(tag, max_depth=3):
    """Render ASCII pedigree tree for a mouse up to max_depth generations."""
    mouse = db.get_mouse_by_tag(tag)
    if not mouse:
        return "Mouse not found."

    lines = []

    def _node(t, depth, is_last, prefix):
        if depth >= max_depth or not t:
            return
        m = db.get_mouse_by_tag(t)
        if not m:
            return
        connector = "└── " if is_last else "├── "
        indent = "    " if is_last else "│   "
        gs = genotype_summary(m["id"])
        gs_str = f"  {gs}" if gs != "—" else ""
        sym = sex_symbol(m["sex"])
        lines.append(f"{prefix}{connector}{sym} **{t}**{gs_str}")

        kids = []
        if m["father_tag"]:
            kids.append(m["father_tag"])
        if m["mother_tag"]:
            kids.append(m["mother_tag"])
        for i, kid in enumerate(kids):
            _node(kid, depth + 1, i == len(kids) - 1, prefix + indent)

    gs = genotype_summary(mouse["id"])
    gs_str = f"  {gs}" if gs != "—" else ""
    sym = sex_symbol(mouse["sex"])
    lines.append(f"{sym} **{tag}** (self){gs_str}")

    kids = []
    if mouse["father_tag"]:
        kids.append(mouse["father_tag"])
    if mouse["mother_tag"]:
        kids.append(mouse["mother_tag"])
    for i, kid in enumerate(kids):
        _node(kid, 1, i == len(kids) - 1, "")

    return "\n".join(lines)


# ── Top Navigation ────────────────────────────────────────────────

NAV_ITEMS = [
    {"key": "dashboard", "label": "Dashboard"},
    {"key": "add_import", "label": "Add / Import"},
    {"key": "mice", "label": "Mice"},
    {"key": "cages", "label": "Cages"},
    {"key": "settings", "label": "Settings"},
]
NAV_KEYS = {item["key"] for item in NAV_ITEMS}


def set_current_page(page_key):
    st.session_state.current_page = page_key if page_key in NAV_KEYS else "dashboard"


def go_to_page(page_key):
    set_current_page(page_key)
    st.rerun()


def render_top_nav():
    if "current_page" not in st.session_state:
        set_current_page("dashboard")
    if st.session_state.current_page not in NAV_KEYS:
        set_current_page("dashboard")

    st.markdown(
        """
        <div class="app-topbar">
            <div>
                <div class="app-title">Mouse Colony Manager</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_cols = st.columns(len(NAV_ITEMS))
    for col, item in zip(nav_cols, NAV_ITEMS):
        is_current = st.session_state.current_page == item["key"]
        if col.button(
            item["label"],
            key=f"nav_{item['key']}",
            type="primary" if is_current else "secondary",
            width="stretch",
        ):
            go_to_page(item["key"])


def render_page_header(title="", description=""):
    return


render_top_nav()
page = st.session_state.current_page

# ── Dashboard ─────────────────────────────────────────────────────

def dashboard_page():
    render_page_header()
    stats = db.get_stats()
    split_due_litter_rows = due_litters()
    split_due_reminder_rows = due_split_reminders()
    split_due_count = len(split_due_litter_rows) + len(split_due_reminder_rows)
    distinct_genes = db.get_distinct_genes()
    cages = db.get_all_breeding_cages()
    active_breeding_cages = [
        cage for cage in cages
        if cage["cage_type"] == "breeding" and cage["status"] == "active"
    ]
    breeding_mouse_ids = {
        mouse["id"]
        for cage in active_breeding_cages
        for mouse in cage_mice(cage)
    }
    active_mouse_ids = {
        mouse["id"] for mouse in db.get_all_mice()
        if mouse["status"] != "dead"
    }
    other_mouse_ids = active_mouse_ids - breeding_mouse_ids
    breeding_gene_rows = gene_combo_stats(breeding_mouse_ids)
    other_gene_rows = gene_combo_stats(other_mouse_ids)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_summary_card("Total mice", stats["total_mice"], "All registered mice", "blue")
    with c2:
        render_summary_card("Total cages", len(cages), "All registered cages", "green")
    with c3:
        split_tone = "red" if split_due_count else "amber"
        split_detail = "Needs attention" if split_due_count else "No due reminders"
        render_summary_card("Split due", split_due_count, split_detail, split_tone)

    if stats["total_mice"] == 0 and not distinct_genes and not cages:
        st.markdown(
            """
            <div class="empty-panel">
                <strong>Start by setting up the colony basics.</strong>
                <span>Add genes, import mice, then create cages when animals are ready to assign.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        a1, a2, a3, _ = st.columns([1, 1, 1, 3])
        if a1.button("Add genes", key="empty_add_genes", width="stretch"):
            go_to_page("settings")
        if a2.button("Import mice", key="empty_import_mice", width="stretch"):
            go_to_page("add_import")
        if a3.button("Create cage", key="empty_create_cage", width="stretch"):
            go_to_page("cages")

    st.divider()

    left, right = st.columns(2)

    with left:
        if not split_due_count:
            split_html = render_empty_note("No split reminders due today.")
        else:
            today = date.today()
            rows = []
            for litter, due in split_due_litter_rows:
                days = (today - due).days
                timing = "Due today" if days == 0 else f"Overdue {days}d"
                tone = "due" if days == 0 else "overdue"
                meta = f"Litter · Born {litter['birth_date']} · {litter['total_born'] or '?'} born"
                rows.append(soft_row(litter["cage_label"], meta, timing, tone))
            for reminder, due in split_due_reminder_rows:
                days = (today - due).days
                timing = "Due today" if days == 0 else f"Overdue {days}d"
                tone = "due" if days == 0 else "overdue"
                meta = f"Reminder · Due {reminder['due_date']}"
                if reminder["notes"]:
                    meta += f" · {reminder['notes']}"
                rows.append(soft_row(reminder["cage_label"], meta, timing, tone))
            rows = rows[:10]
            split_html = "".join(rows)
        render_section_card("Split reminders", split_html)

    with right:
        litters = db.get_all_litters()
        if not litters:
            recent_html = render_empty_note("No litters recorded yet.")
        else:
            rows = []
            for litter in litters[:10]:
                meta = f"Born {litter['birth_date']} · {litter['total_born']} born"
                badge = f"{litter['weaned_count'] or 0} weaned"
                rows.append(soft_row(litter["cage_label"], meta, badge, "done"))
            recent_html = "".join(rows)
        render_section_card("Recent litters", recent_html)

    st.divider()
    st.subheader("Gene Type Counts")
    gene_left, gene_right = st.columns(2)
    with gene_left:
        render_section_card(
            "Breeding cages",
            gene_chip_counts_html(breeding_gene_rows, "No genotyped mice in active breeding cages."),
        )
    with gene_right:
        render_section_card(
            "Other mice",
            gene_chip_counts_html(other_gene_rows, "No genotyped mice outside active breeding cages."),
        )


# ── Mouse Registry ────────────────────────────────────────────────

def mouse_registry_page():
    render_page_header()

    tab_bulk, tab_add = st.tabs(["📥 Bulk Import", "➕ Add Mouse"])

    with tab_bulk:
        _bulk_import_form()

    with tab_add:
        _add_mouse_form()


def view_edit_mice_page():
    render_page_header()
    tab_list, tab_weight, tab_archive = st.tabs(["View / Edit Mice", "Weight / Survival", "Death Archive"])
    with tab_list:
        _mouse_list()
    with tab_weight:
        _weight_survival_page()
    with tab_archive:
        _death_archive_page()


def _add_mouse_form(prefill_tag="", prefill_birth=None, prefill_father="", prefill_mother=""):
    with st.form("add_mouse_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        ear_tag = c1.text_input("Ear Tag / ID *", value=prefill_tag)
        sex = c2.selectbox("Sex", ["U", "M", "F"], format_func=sex_option_label)
        birth_date = c3.date_input("Birth Date", value=prefill_birth or date.today())

        c4, c5 = st.columns(2)
        father_tag = c4.text_input("Father Tag (父本)", value=prefill_father)
        mother_tag = c5.text_input("Mother Tag (母本)", value=prefill_mother)

        c6, c7 = st.columns(2)
        status = c6.selectbox(
            "Status",
            MOUSE_LIVE_STATUS_OPTIONS,
            index=MOUSE_LIVE_STATUS_OPTIONS.index("holding"),
            format_func=lambda x: MOUSE_STATUS_LABELS[x],
        )
        cage_location = c7.text_input("Cage Location")
        notes = st.text_area("Notes")

        col_geno, _ = st.columns([1, 2])
        add_geno_now = col_geno.checkbox("Add genotypes now", value=True)

        if add_geno_now:
            st.caption("Genotypes:")
            add_genes = compact_genotype_inputs(prefix="add_")

        submitted = st.form_submit_button("Register Mouse")
        if submitted:
            if not ear_tag.strip():
                st.error("Ear tag is required.")
                return
            if db.get_mouse_by_tag(ear_tag.strip()):
                st.error(f"Mouse '{ear_tag}' already exists.")
                return
            mid = db.add_mouse(
                ear_tag=ear_tag.strip(),
                birth_date=str(birth_date) if birth_date else None,
                sex=sex,
                father_tag=father_tag.strip() or None,
                mother_tag=mother_tag.strip() or None,
                status=status,
                cage_location=cage_location.strip() or None,
                notes=notes.strip() or None,
            )
            if add_geno_now:
                for g, a1, a2 in add_genes:
                    db.set_genotype(mid, g, a1.strip() or "?", a2.strip() or "?")
            st.success(f"Mouse '{ear_tag}' registered successfully.")
            st.rerun()


def _weight_survival_page():
    selected_mice = _weight_mouse_selection()
    selected_ids = [m["id"] for m in selected_mice]

    st.divider()
    left, right = st.columns([1, 1])
    with left:
        _record_weight_panel(selected_mice)
    with right:
        _record_survival_panel(selected_mice)

    st.divider()
    chart_left, chart_right = st.columns([1, 1])
    with chart_left:
        _render_weight_curve(selected_ids)
    with chart_right:
        _render_survival_curve(selected_mice)


def _weight_mouse_selection():
    cages = db.get_all_breeding_cages(status_filter="active")
    cage_options = {}
    for cage in cages:
        cage_type = "Breeding" if cage["cage_type"] == "breeding" else "Holding"
        cage_options[f"{cage['cage_label']} · {cage_type} · {len(cage_mice(cage))} mice"] = cage
    selected_cage_labels = st.multiselect(
        "Cages",
        list(cage_options.keys()),
        default=list(cage_options.keys()),
        key="weight_cages",
        placeholder="Choose cages...",
    )

    cage_ids = [cage_options[label]["id"] for label in selected_cage_labels]
    mice_by_id = {}
    for label in selected_cage_labels:
        for mouse in cage_mice(cage_options[label]):
            mice_by_id[mouse["id"]] = mouse
    selected_cage_names = {cage_options[label]["cage_label"] for label in selected_cage_labels}
    for mouse in db.get_death_archive():
        if mouse["previous_cage_location"] in selected_cage_names:
            mice_by_id[mouse["id"]] = mouse
    mice = sorted(mice_by_id.values(), key=lambda m: str(m["ear_tag"]))

    if not mice:
        st.caption("No mice found in the selected cages.")
        return []

    rows = [
        {
            "Include": True,
            "ID": str(mouse["ear_tag"]),
            "Sex": sex_display(mouse["sex"]),
            "Age": mouse_age_label(
                mouse["birth_date"],
                parse_date(mouse["end_date"]) if mouse["status"] == "dead" else None,
            ),
            "Cage": mouse["cage_location"] or mouse["previous_cage_location"] or "unassigned",
            "Genotype": genotype_summary(mouse["id"]),
        }
        for mouse in mice
    ]
    cage_sig = "_".join(str(cid) for cid in cage_ids) or "none"
    edited = st.data_editor(
        pd.DataFrame(rows),
        key=f"weight_mouse_table_{cage_sig}",
            width="stretch",
        hide_index=True,
        disabled=["ID", "Sex", "Age", "Cage", "Genotype"],
        column_config={
            "Include": st.column_config.CheckboxColumn("Include", default=True, width="small"),
            "ID": st.column_config.TextColumn("ID", width="medium"),
            "Sex": st.column_config.TextColumn("Sex", width="small"),
            "Age": st.column_config.TextColumn("Age", width="small"),
            "Cage": st.column_config.TextColumn("Cage", width="medium"),
            "Genotype": st.column_config.TextColumn("Genotype", width="large"),
        },
    )
    selected_tags = set(edited.loc[edited["Include"], "ID"].astype(str).tolist())
    selected_mice = [m for m in mice if str(m["ear_tag"]) in selected_tags]
    st.caption(f"{len(selected_mice)} mice selected for curves")
    return selected_mice


def _record_weight_panel(mice):
    st.markdown('<div class="detail-section-title">Record Weight</div>', unsafe_allow_html=True)
    if not mice:
        st.info("Choose at least one cage with mice first.")
        return

    label_to_id, _ = short_mouse_label_maps(mice)
    with st.form("record_weight_form"):
        w1, w2, w3 = st.columns([2.1, 1, 1])
        mouse_label = w1.selectbox("Mouse", list(label_to_id.keys()), key="weight_mouse")
        measure_date = w2.date_input("Date", value=date.today(), key="weight_date")
        weight_g = w3.number_input("Weight (g)", min_value=0.0, value=20.0, step=0.1, format="%.1f")
        notes = st.text_input("Notes", key="weight_notes")
        submitted = st.form_submit_button("Save weight")
        if submitted:
            try:
                db.upsert_weight(
                    label_to_id[mouse_label],
                    str(measure_date),
                    float(weight_g),
                    notes.strip() or None,
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            st.success("Weight saved.")
            st.rerun()

    records = db.get_weight_records([m["id"] for m in mice])
    if records:
        with st.expander("Weight records", expanded=False):
            table = [
                {
                    "Date": r["measure_date"],
                    "Mouse": r["ear_tag"],
                    "Sex": sex_display(r["sex"]),
                    "Weight (g)": r["weight_g"],
                    "Notes": r["notes"] or "",
                }
                for r in records
            ]
            st.dataframe(table, width="stretch", hide_index=True)
            delete_options = {
                f"{r['measure_date']} · {r['ear_tag']} · {r['weight_g']} g": r["id"]
                for r in records
            }
            with st.form("delete_weight_form"):
                target = st.selectbox("Delete weight record", list(delete_options.keys()))
                delete = st.form_submit_button("Delete weight", type="secondary")
                if delete:
                    db.delete_weight(delete_options[target])
                    st.warning("Weight record deleted.")
                    st.rerun()


def _record_survival_panel(mice):
    st.markdown('<div class="detail-section-title">Death Record</div>', unsafe_allow_html=True)
    if not mice:
        st.info("Choose at least one cage with mice first.")
        return

    live_mice = [m for m in mice if m["status"] != "dead"]
    if live_mice:
        label_to_id, _ = short_mouse_label_maps(live_mice)
        with st.form("record_survival_form"):
            s1, s2, s3 = st.columns([2.1, 1.35, 1])
            mouse_label = s1.selectbox("Mouse", list(label_to_id.keys()), key="survival_mouse")
            death_method = s2.selectbox("Death method", DEATH_METHODS, key="survival_death_method")
            end_date = s3.date_input("Date", value=date.today(), key="survival_date")
            notes = st.text_input("Death notes", key="survival_notes")
            submitted = st.form_submit_button("Mark dead")
            if submitted:
                try:
                    db.mark_mouse_dead(
                        label_to_id[mouse_label],
                        str(end_date),
                        death_method,
                        notes.strip() or None,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    return
                st.success(f"Marked {mouse_label} as dead.")
                st.rerun()
    else:
        st.info("All selected mice are already in the death archive.")

    records = db.get_survival_records([m["id"] for m in mice])
    if records:
        with st.expander("Death records in selected cohort", expanded=False):
            table = [
                {
                    "Mouse": r["ear_tag"],
                    "Sex": sex_display(r["sex"]),
                    "Method": r["death_method"] or survival_outcome_label(r["outcome"]),
                    "Curve": death_curve_label(r),
                    "Date": r["end_date"],
                    "Notes": r["notes"] or "",
                }
                for r in records
            ]
            st.dataframe(table, width="stretch", hide_index=True)


def survival_outcome_label(outcome):
    return {
        "dead": "Dead",
        "euthanized": "Euthanized",
        "censored": "Censored",
    }.get(outcome or "", outcome or "Alive")


def death_curve_label(record):
    if record["death_method"] == "Natural death":
        return "event"
    if record["death_method"] == "Experimental harvest":
        return "censored"
    return "event" if record["outcome"] == "dead" else "censored"


def _death_archive_page():
    records = list(db.get_death_archive())
    search = st.text_input("Search death archive", placeholder="ID / cage / method / notes...", key="death_archive_search")
    if search.strip():
        q = search.strip().lower()
        filtered = []
        for record in records:
            haystack = " ".join(
                str(value or "")
                for value in [
                    record["ear_tag"],
                    record["previous_cage_location"],
                    record["death_method"],
                    record["death_notes"],
                    genotype_summary(record["id"]),
                ]
            ).lower()
            if q in haystack:
                filtered.append(record)
        records = filtered

    st.caption(f"{len(records)} dead mice archived")
    if not records:
        st.info("No dead mice in archive.")
        return

    table = [
        {
            "ID": r["ear_tag"],
            "Sex": sex_display(r["sex"]),
            "Age": mouse_age_label(r["birth_date"], parse_date(r["end_date"])),
            "Original cage": r["previous_cage_location"] or "—",
            "Death date": r["end_date"],
            "Death method": r["death_method"] or survival_outcome_label(r["outcome"]),
            "Curve": death_curve_label(r),
            "Genotype": genotype_summary(r["id"]),
            "Notes": r["death_notes"] or "",
        }
        for r in records
    ]
    st.dataframe(table, width="stretch", hide_index=True)

    restore_options = {
        f"{r['ear_tag']} · {r['end_date']} · {r['death_method'] or survival_outcome_label(r['outcome'])}": r["id"]
        for r in records
    }
    with st.form("restore_dead_mouse_form"):
        r1, r2 = st.columns([3, 1])
        target = r1.selectbox("Restore mouse", list(restore_options.keys()))
        restore = r2.form_submit_button("Restore")
        if restore:
            try:
                result = db.restore_dead_mouse(restore_options[target])
            except ValueError as exc:
                st.error(str(exc))
                return
            if result.get("warning"):
                st.warning(result["warning"])
            else:
                restored_to = result.get("cage_location") or "unassigned"
                st.success(f"Mouse restored to {restored_to}.")
            st.rerun()


def _render_weight_curve(mouse_ids):
    st.markdown('<div class="detail-section-title">Weight Curve</div>', unsafe_allow_html=True)
    if not mouse_ids:
        st.info("No mice selected.")
        return
    records = db.get_weight_records(mouse_ids)
    if not records:
        st.info("No weight records for the selected mice.")
        return

    rows = [
        {
            "Date": parse_date(r["measure_date"]),
            "Mouse": r["ear_tag"],
            "Weight (g)": r["weight_g"],
        }
        for r in records
        if parse_date(r["measure_date"])
    ]
    if not rows:
        st.info("No plottable weight dates.")
        return

    df = pd.DataFrame(rows).sort_values("Date")
    chart_df = df.pivot_table(index="Date", columns="Mouse", values="Weight (g)", aggfunc="last")
    st.line_chart(chart_df, height=330)


def _render_survival_curve(mice):
    st.markdown('<div class="detail-section-title">Survival Curve</div>', unsafe_allow_html=True)
    if not mice:
        st.info("No mice selected.")
        return

    survival_rows = db.get_survival_records([m["id"] for m in mice])
    survival_by_mouse = {row["mouse_id"]: row for row in survival_rows}
    durations = []
    events = []
    skipped = []
    today = date.today()

    for mouse in mice:
        birth = parse_date(mouse["birth_date"])
        if not birth:
            skipped.append(mouse["ear_tag"])
            continue
        endpoint = survival_by_mouse.get(mouse["id"])
        if endpoint:
            end = parse_date(endpoint["end_date"]) or today
            if endpoint["death_method"] == "Natural death":
                event = True
            elif endpoint["death_method"] == "Experimental harvest":
                event = False
            else:
                event = endpoint["outcome"] == "dead"
        else:
            end = today
            event = False
        durations.append(max(0, (end - birth).days))
        events.append(event)

    if not durations:
        st.info("Selected mice need birth dates for survival plotting.")
        return

    points = kaplan_meier_points(durations, events)
    chart = (
        alt.Chart(points)
        .mark_line(interpolate="step-after", strokeWidth=2.4, color="#527DA8")
        .encode(
            x=alt.X("Day:Q", title="Day", scale=alt.Scale(zero=True)),
            y=alt.Y(
                "Survival (%):Q",
                title="Survival (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            tooltip=[
                alt.Tooltip("Day:Q", format=".0f"),
                alt.Tooltip("Survival (%):Q", format=".1f"),
            ],
        )
        .properties(height=330)
    )
    st.altair_chart(chart, width="stretch")
    n = len(durations)
    event_count = sum(events)
    st.caption(f"{n} mice plotted · {event_count} endpoint event(s) · {n - event_count} censored/alive")
    if skipped:
        st.warning("Skipped mice without birth date: " + ", ".join(skipped))


def _bulk_import_form():
    mode = st.radio(
        "Import Mode",
        ["📊 Table Editor", "📝 Paste from Spreadsheet", "🔢 Generate Sequential Tags"],
        horizontal=True,
        label_visibility="collapsed",
    )
    render_bulk_import_notices()

    if mode == "📝 Paste from Spreadsheet":
        paste_format = st.radio(
            "Paste format",
            ["Excel genotype table", "Simple rows"],
            horizontal=True,
            key="paste_format",
        )
        data_text = st.text_area(
            "Paste data here",
            height=200,
            placeholder=(
                "id\tgender\tCdh5-CreER\tPex3c\tDOB\n"
                "14\t♀\t+\t+/+\t2026/6/1\n"
                "16\t♀\t+\t+/-\t2026/6/1"
                if paste_format == "Excel genotype table"
                else "M001\tM\t2025-01-15\tDAD001\tMOM001\twaiting_split\nM002\tF\t2025-01-15\tDAD001\tMOM001\twaiting_split"
            ),
        )

        delimiter = st.radio("Delimiter", ["Tab", "Comma"], horizontal=True)

        if paste_format == "Excel genotype table":
            breeding_cages = [
                c for c in db.get_all_breeding_cages(status_filter="active")
                if c["cage_type"] == "breeding"
            ]
            cage_options = {
                f"{c['cage_label']} (♂{c['male_tag'] or '?'} · ♀{len(female_tag_list(c))})": c
                for c in breeding_cages
            }
            selected_cage_label = st.selectbox(
                "Born in breeding cage",
                ["—"] + list(cage_options.keys()),
                key="excel_birth_cage",
            )
            selected_cage = cage_options.get(selected_cage_label)

            if not breeding_cages:
                st.warning("No active breeding cages found. Create or activate a breeding cage first.")

            if data_text.strip():
                parsed = parse_excel_genotype_table(data_text, delimiter)
                genes = parsed["genes"]
                auto_prefix = gene_id_prefix(genes)
                gene_sig = "|".join(genes)
                if st.session_state.get("excel_gene_prefix_sig") != gene_sig:
                    st.session_state.excel_tag_prefix = auto_prefix
                    st.session_state.excel_gene_prefix_sig = gene_sig

                tag_prefix = st.text_input("Suggested ID Prefix", key="excel_tag_prefix")
                rows, tag_errors = validate_excel_import_tags(parsed["rows"], tag_prefix)
                import_errors = list(parsed["errors"]) + tag_errors
                female_tags = female_tag_list(selected_cage) if selected_cage else []
                mother_tag = ", ".join(female_tags)
                father_tag = selected_cage["male_tag"] if selected_cage else None
                cage_location = selected_cage["cage_label"] if selected_cage else None

                if selected_cage:
                    st.markdown(
                        f"**Target:** {esc(cage_location)} · **Father:** {esc(father_tag or '—')} · "
                        f"**Candidate mothers:** {esc(mother_tag or '—')} · **Status:** waiting split"
                    )

                if genes:
                    st.caption("Detected genes: " + ", ".join(genes))

                if rows:
                    preview_rows = []
                    for row in rows:
                        preview_rows.append(
                            {
                                "Excel ID": row["source_id"],
                                "Ear Tag": row["tag"] or "—",
                                "Sex": sex_display(row["sex"]),
                                "Birth Date": row["birth_date"] or "?",
                                "Genotypes": "; ".join(
                                    f"{g} {a1}/{a2}" for g, a1, a2 in row["genotypes"]
                                ) or "—",
                            }
                        )
                    st.dataframe(preview_rows, width="stretch", hide_index=True)

                if import_errors:
                    st.error("Fix these issues before importing:")
                    for error in import_errors:
                        st.write(f"- {error}")

                can_import = bool(selected_cage and rows and not import_errors)
                if st.button("📥 Import Mice", key="excel_import", disabled=not can_import):
                    imported_tags = []
                    for row in rows:
                        mid = db.add_mouse(
                            ear_tag=row["tag"],
                            birth_date=row["birth_date"],
                            sex=row["sex"],
                            father_tag=father_tag or None,
                            mother_tag=mother_tag or None,
                            birth_cage_id=selected_cage["id"],
                            status="waiting_split",
                            cage_location=cage_location,
                        )
                        for gene, a1, a2 in row["genotypes"]:
                            db.set_genotype(mid, gene, a1, a2)
                        imported_tags.append(row["tag"])
                    queue_bulk_import_notice(import_result_message("Imported", imported_tags))
                    st.rerun()
                elif data_text.strip() and not selected_cage:
                    st.info("Choose the breeding cage these mice were born in before importing.")
            else:
                st.info("Paste an Excel table with columns like id, gender, gene columns, and DOB.")
        else:
            col1, col2, _ = st.columns([1, 1, 3])
            add_geno_bulk = col1.checkbox("Add genotypes after import", value=False)
            dry_run = col2.checkbox("Preview only (no save)", value=False)

            bulk_genes = []
            if add_geno_bulk:
                bulk_genes = compact_genotype_inputs(prefix="bulk_")

            if st.button("Import Mice") and data_text.strip():
                sep = "\t" if delimiter == "Tab" else ","
                lines = [l.strip() for l in data_text.strip().split("\n") if l.strip()]
                imported = 0
                imported_tags = []
                errors = []
                preview = []

                for line in lines:
                    parts = [p.strip() for p in line.split(sep)]
                    if len(parts) < 2:
                        errors.append(f"Skipped (too few fields): {line[:50]}")
                        continue

                    tag = parts[0]
                    sex = parts[1] if len(parts) > 1 else "U"
                    bd = parts[2] if len(parts) > 2 else str(date.today())
                    ftag = parts[3] if len(parts) > 3 else None
                    mtag = parts[4] if len(parts) > 4 else None
                    status = normalize_mouse_status(parts[5] if len(parts) > 5 else "waiting_split", default="waiting_split")
                    notes = parts[6] if len(parts) > 6 else None

                    if sex not in ("M", "F", "U"):
                        errors.append(f"Invalid sex '{sex}' for {tag}, using U")
                        sex = "U"

                    if dry_run:
                        geno_preview = ""
                        if bulk_genes:
                            geno_preview = " | " + "; ".join(f"{g} {a1}/{a2}" for g, a1, a2 in bulk_genes)
                        preview.append(
                            f"{tag} | {sex_display(sex)} | {bd} | ♂{ftag or '?'} | ♀{mtag or '?'} | {status}{geno_preview}"
                        )
                    else:
                        if db.get_mouse_by_tag(tag):
                            errors.append(f"Duplicate skipped: {tag}")
                            continue
                        mid = db.add_mouse(
                            ear_tag=tag, birth_date=bd, sex=sex,
                            father_tag=ftag, mother_tag=mtag,
                            status=status, notes=notes,
                        )
                        for g, a1, a2 in bulk_genes:
                            db.set_genotype(mid, g, a1, a2)
                        imported += 1
                        imported_tags.append(tag)

                if dry_run:
                    st.info(f"Preview — {len(preview)} mice will be imported:")
                    for p in preview:
                        st.write(p)
                else:
                    queue_bulk_import_notice(import_result_message("Imported", imported_tags))
                    if errors:
                        queue_bulk_import_notice("Warnings: " + "; ".join(errors), level="warning")
                    st.rerun()

    elif mode == "🔢 Generate Sequential Tags":
        c1, c2, c3 = st.columns(3)
        prefix = c1.text_input("Tag Prefix", placeholder="e.g. GeneA-GeneB")
        start_num = c2.number_input("Start Number", min_value=1, value=1)
        count = c3.number_input("Count", min_value=1, value=10)

        c4, c5, c6 = st.columns(3)
        seq_sex = c4.selectbox("Sex", ["M", "F", "Mix"], format_func=sex_option_label)
        seq_birth = c5.date_input("Birth Date", value=date.today())
        seq_status = c6.selectbox(
            "Status",
            ["waiting_split", "holding", "breeding"],
            index=0,
            format_func=lambda x: MOUSE_STATUS_LABELS[x],
        )

        c7, c8 = st.columns(2)
        seq_father = c7.text_input("Father Tag (all)")
        seq_mother = c8.text_input("Mother Tag (all)")

        seq_notes = st.text_area("Notes (applied to all)")

        col1, col2, _ = st.columns([1, 1, 3])
        add_geno_seq = col1.checkbox("Add genotypes after import", value=False)
        seq_dry_run = col2.checkbox("Preview only", value=False, key="seq_dry")

        seq_genes = []
        if add_geno_seq:
            seq_genes = compact_genotype_inputs(prefix="seq_")

        if st.button("Generate Mice"):
            tags = []
            for i in range(count):
                num = start_num + i
                if seq_sex == "Mix":
                    s = "M" if i % 2 == 0 else "F"
                else:
                    s = seq_sex
                tag = f"{prefix}-{num:03d}"
                tags.append((tag, s))

            if seq_dry_run:
                st.info(f"Preview — {count} mice will be created:")
                for t, s in tags:
                    geno_str = ""
                    if seq_genes:
                        geno_str = " | " + "; ".join(f"{g} {a1}/{a2}" for g, a1, a2 in seq_genes)
                    st.write(f"{t} | {sex_display(s)} | {seq_birth} | ♂{seq_father or '?'} | ♀{seq_mother or '?'}{geno_str}")
            else:
                created = 0
                created_tags = []
                for tag, s in tags:
                    if db.get_mouse_by_tag(tag):
                        continue
                    mid = db.add_mouse(
                        ear_tag=tag, birth_date=str(seq_birth), sex=s,
                        father_tag=seq_father.strip() or None,
                        mother_tag=seq_mother.strip() or None,
                        status=seq_status, notes=seq_notes.strip() or None,
                    )
                    for g, a1, a2 in seq_genes:
                        db.set_genotype(mid, g, a1, a2)
                    created += 1
                    created_tags.append(tag)
                queue_bulk_import_notice(import_result_message("Created", created_tags))
                st.rerun()

    else:  # 📊 Table Editor
        # ── Shared attributes ──
        all_cages = db.get_all_breeding_cages(status_filter="active")
        cage_options = {f"{c['cage_label']} (♂{c['male_tag'] or '?'})": c for c in all_cages if c["cage_type"] == "breeding"}
        cage_labels = list(cage_options.keys())

        if "te_count" not in st.session_state:
            st.session_state.te_count = 4
        count = st.session_state.te_count

        # ── Genes selection ──
        all_gene_choices = gene_choices()
        genes = st.multiselect("Genes (max 3)", all_gene_choices, default=COMMON_GENES[:2], key="te_genes")
        if len(genes) > 3:
            genes = genes[:3]

        auto_prefix = gene_id_prefix(genes)
        gene_sig = "|".join(genes)
        if st.session_state.get("te_gene_prefix_sig") != gene_sig:
            previous_prefix = st.session_state.get("te_auto_prefix", "M")
            current_start = int(st.session_state.get("te_start", 1))
            for i in range(count):
                key = f"te_tag_{i}"
                previous_tag = f"{previous_prefix}-{current_start + i:02d}" if previous_prefix else ""
                if not st.session_state.get(key) or st.session_state.get(key) == previous_tag:
                    st.session_state[key] = f"{auto_prefix}-{current_start + i:02d}"
            st.session_state.te_pfx = auto_prefix
            st.session_state.te_auto_prefix = auto_prefix
            st.session_state.te_gene_prefix_sig = gene_sig

        r1c1, r1c2, r1c3, r1c4 = st.columns([1, 1.35, 1, 0.75])
        birth_date = r1c1.date_input("Default Birth Date", value=date.today(), key="te_bd")
        selected_cage_label = r1c2.selectbox("Breeding Cage", ["—"] + cage_labels, key="te_cage_sel")
        tag_prefix = r1c3.text_input("Suggested ID Prefix", key="te_pfx")
        tag_start = r1c4.number_input("Start #", min_value=1, value=1, step=1, key="te_start")

        if selected_cage_label != "—":
            selected_cage = cage_options[selected_cage_label]
            birth_cage_id = selected_cage["id"]
            father_tag = selected_cage["male_tag"]
            cage_location = selected_cage["cage_label"]
            female_tags = (selected_cage["female_tags"] or "").split(", ")
            female_tags = [t for t in female_tags if t]

            r2c1, r2c2, r2c3 = st.columns(3)
            r2c1.markdown(f"**Father:** {father_tag or '—'}")
            r2c2.markdown(f"**Cage:** {cage_location}")
            if female_tags:
                mother_tag = r2c3.selectbox("Mother", female_tags, key="te_mother")
            else:
                mother_tag = None
                r2c3.markdown("**Mother:** —")
        else:
            birth_cage_id = None
            father_tag = None
            mother_tag = None
            cage_location = None

        # ── Row count +/− ──
        action_cols = st.columns([0.72, 1.05, 0.78, 0.95, 1.45, 1.15, 4.9], gap="small")
        bc_count, bc1, bc2, bc4, copy_attr_col, copy_geno_col, _ = action_cols
        count = st.session_state.te_count
        bc_count.markdown(f'<div class="toolbar-count">{count} mice</div>', unsafe_allow_html=True)
        if bc1.button("➖ Remove", key="te_minus"):
            st.session_state.te_count = max(1, st.session_state.te_count - 1)
            st.rerun()
        if bc2.button("➕ Add", key="te_plus"):
            st.session_state.te_count = min(12, st.session_state.te_count + 1)
            st.rerun()
        if bc4.button("↻ Fill IDs", key="te_fill_ids"):
            for i in range(count):
                st.session_state[f"te_tag_{i}"] = f"{tag_prefix.strip()}-{int(tag_start) + i:02d}"
            st.rerun()

        copy_attr_col.button(
            "📋 Copy Sex/Date",
            key="te_copy_sex_date",
            help="Copy row 1 sex and birth date to rows 2+.",
            on_click=copy_table_editor_sex_date,
            args=(count, birth_date),
        )

        copy_geno_col.button(
            "📋 Copy Geno",
            key="te_copy_genotypes",
            help="Copy row 1 genotype alleles to rows 2+.",
            on_click=copy_table_editor_genotypes,
            args=(count, len(genes)),
        )

        if count == 0:
            st.stop()

        # ── Table (rows = mice, cols = attributes) ──
        n_attr_cols = 3 + len(genes)  # Ear tag + sex + birth date + per-gene allele pairs
        hcols = st.columns([0.7, 2.2, 1.35, 1.35] + [2] * len(genes))
        hcols[0].caption("")
        hcols[1].caption("Ear Tag / ID")
        hcols[2].caption("Sex")
        hcols[3].caption("Birth Date")
        for gi, gene in enumerate(genes):
            hcols[4 + gi].caption(gene)

        ear_tags = []
        sexes = []
        birth_dates = []
        gene_alleles = {g: [] for g in genes}
        for i in range(count):
            suggested_tag = f"{tag_prefix.strip()}-{int(tag_start) + i:02d}" if tag_prefix.strip() else ""
            if f"te_tag_{i}" not in st.session_state:
                st.session_state[f"te_tag_{i}"] = suggested_tag
            if f"te_birth_{i}" not in st.session_state:
                st.session_state[f"te_birth_{i}"] = birth_date

            rcols = st.columns([0.7, 2.2, 1.35, 1.35] + [2] * len(genes))
            rcols[0].caption(f"#{i+1}")
            with rcols[1]:
                tag = st.text_input(
                    "Ear Tag / ID",
                    key=f"te_tag_{i}",
                    label_visibility="collapsed",
                    placeholder=suggested_tag,
                )
                ear_tags.append(tag.strip())
            with rcols[2]:
                s = st.selectbox(
                    "Sex",
                    ["M", "F"],
                    key=f"te_sex_{i}",
                    label_visibility="collapsed",
                    format_func=sex_option_label,
                )
                sexes.append(s)
            with rcols[3]:
                row_birth = st.date_input(
                    "Birth Date",
                    min_value=date(2000, 1, 1),
                    max_value=date.today(),
                    key=f"te_birth_{i}",
                    label_visibility="collapsed",
                )
                birth_dates.append(row_birth)
            for gi, gene in enumerate(genes):
                with rcols[4 + gi]:
                    aac1, aac2 = st.columns(2)
                    with aac1:
                        a1 = allele_input("A1", key=f"te_a1_{gi}_{i}", compact=True)
                    with aac2:
                        a2 = allele_input("A2", key=f"te_a2_{gi}_{i}", compact=True)
                    gene_alleles[gene].append((a1, a2))

        # ── Submit ──
        if st.button("📥 Import Mice", key="te_import"):
            missing_tags = [str(i + 1) for i, tag in enumerate(ear_tags) if not tag]
            duplicate_input_tags = sorted({tag for tag in ear_tags if tag and ear_tags.count(tag) > 1})
            existing_tags = db.find_existing_ear_tags(ear_tags)

            if missing_tags:
                st.error("Ear Tag / ID is required for row(s): " + ", ".join(missing_tags))
            elif duplicate_input_tags:
                st.error("Duplicate Ear Tag / ID in this table: " + ", ".join(duplicate_input_tags))
            elif existing_tags:
                st.error("Ear Tag / ID already exists: " + ", ".join(existing_tags))
            else:
                imported = 0
                imported_tags = []
                for i in range(count):
                    tag = ear_tags[i]
                    mid = db.add_mouse(
                        ear_tag=tag,
                        birth_date=str(birth_dates[i]),
                        sex=sexes[i],
                        father_tag=father_tag,
                        mother_tag=mother_tag,
                        birth_cage_id=birth_cage_id,
                        status="waiting_split",
                        cage_location=cage_location or None,
                    )
                    for gene in genes:
                        a1, a2 = gene_alleles[gene][i]
                        db.set_genotype(mid, gene, a1.strip() or "?", a2.strip() or "?")
                    imported += 1
                    imported_tags.append(tag)
                queue_bulk_import_notice(import_result_message("Imported", imported_tags))
                st.rerun()


def _filtered_mice_for_view():
    all_distinct_genes = db.get_distinct_genes()

    cf1, cf2, cf3, cf4 = st.columns(4)
    status_filter = cf1.selectbox(
        "Filter by Status",
        ["All"] + MOUSE_LIVE_STATUS_OPTIONS,
        format_func=lambda x: "All" if x == "All" else MOUSE_STATUS_LABELS[x],
    )
    search_query = cf2.text_input("Search (tag / notes / location)")
    sex_filter = cf3.selectbox("Filter by Sex", ["All", "M", "F", "U"], format_func=sex_option_label)
    gene_filter = cf4.multiselect("Filter by Genes (AND)", all_distinct_genes, key="mouse_gene_filter", placeholder="All genes...")

    if search_query:
        mice = db.search_mice(search_query)
    elif status_filter != "All":
        mice = db.get_all_mice(status_filter=status_filter)
    else:
        mice = [m for m in db.get_all_mice() if m["status"] != "dead"]

    if sex_filter != "All":
        mice = [m for m in mice if m["sex"] == sex_filter]

    if gene_filter:
        gene_set = set(gene_filter)
        filtered = []
        for m in mice:
            mouse_genes = {g["gene"] for g in db.get_mouse_genotypes(m["id"])}
            if gene_set <= mouse_genes:
                filtered.append(m)
        mice = filtered

    return mice


def _mouse_view_mode_toggle():
    if "mouse_view_mode" not in st.session_state:
        st.session_state.mouse_view_mode = "cards"

    mode_cols = st.columns([1, 1, 6])
    card_active = st.session_state.mouse_view_mode == "cards"
    table_active = st.session_state.mouse_view_mode == "table"
    if mode_cols[0].button(
        "Cards",
        key="mouse_view_cards",
        type="primary" if card_active else "secondary",
            width="stretch",
    ):
        st.session_state.mouse_view_mode = "cards"
        st.rerun()
    if mode_cols[1].button(
        "Table",
        key="mouse_view_table",
        type="primary" if table_active else "secondary",
            width="stretch",
    ):
        st.session_state.mouse_view_mode = "table"
        st.rerun()


def _mouse_list():
    mice = _filtered_mice_for_view()
    st.caption(f"{len(mice)} mice found")
    _mouse_view_mode_toggle()

    if "selected_mouse_id" not in st.session_state:
        st.session_state.selected_mouse_id = None

    valid_ids = {m["id"] for m in mice}
    if st.session_state.selected_mouse_id is not None and st.session_state.selected_mouse_id not in valid_ids:
        st.session_state.selected_mouse_id = None

    if not mice:
        st.info("No mice match the current filters.")
        return

    if st.session_state.mouse_view_mode == "table":
        _render_mouse_table_view(mice)
        return

    _render_mouse_card_view(mice)


def _render_mouse_card_view(mice):
    for row_start in range(0, len(mice), 4):
        row = mice[row_start:row_start + 4]
        cols = st.columns(4)
        for col, mouse in zip(cols, row):
            with col:
                _render_mouse_card(mouse)

        if st.session_state.selected_mouse_id is not None:
            selected_in_row = [
                m for m in row if m["id"] == st.session_state.selected_mouse_id
            ]
            if selected_in_row:
                _mouse_detail(selected_in_row[0])
                st.divider()


def _render_mouse_table_view(mice):
    notice = st.session_state.pop("mouse_table_notice", None)
    if notice:
        st.success(notice)

    current_id = st.session_state.get("selected_mouse_id")
    tag_to_mouse = {str(mouse["ear_tag"]): mouse for mouse in mice}
    current_tag = None
    for mouse in mice:
        if mouse["id"] == current_id:
            current_tag = str(mouse["ear_tag"])
            break

    rows = [
        {
            "Assign": False,
            "Open": mouse["id"] == current_id,
            "Color": gene_stripe_data_uri(mouse_gene_names(mouse["id"])),
            "ID": str(mouse["ear_tag"]),
            "Age": mouse_age_label(mouse["birth_date"]),
            "Sex": sex_display(mouse["sex"]),
            "Status": MOUSE_STATUS_LABELS.get(mouse["status"], mouse["status"]),
            "Cage": mouse["cage_location"] or "—",
            "Genotype": genotype_summary(mouse["id"]),
            "Father": mouse["father_tag"] or "—",
            "Mother": mouse["mother_tag"] or "—",
            "Notes": mouse["notes"] or "",
        }
        for mouse in mice
    ]
    assign_version = st.session_state.get("mouse_table_assign_version", 0)
    table_sig = f"{len(mice)}_{current_id or 'none'}_{assign_version}"
    edited = st.data_editor(
        pd.DataFrame(rows),
        key=f"mouse_table_view_{table_sig}",
            width="stretch",
        hide_index=True,
        disabled=["Color", "ID", "Age", "Sex", "Status", "Cage", "Genotype", "Father", "Mother", "Notes"],
        column_config={
            "Assign": st.column_config.CheckboxColumn("Assign", default=False, width="small"),
            "Open": st.column_config.CheckboxColumn("Open", default=False, width="small"),
            "Color": st.column_config.ImageColumn("Color", width="small"),
            "ID": st.column_config.TextColumn("ID", width="medium"),
            "Age": st.column_config.TextColumn("Age", width="small"),
            "Sex": st.column_config.TextColumn("Sex", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Cage": st.column_config.TextColumn("Cage", width="medium"),
            "Genotype": st.column_config.TextColumn("Genotype", width="large"),
            "Father": st.column_config.TextColumn("Father", width="medium"),
            "Mother": st.column_config.TextColumn("Mother", width="medium"),
            "Notes": st.column_config.TextColumn("Notes", width="medium"),
        },
    )

    open_tags = edited.loc[edited["Open"], "ID"].astype(str).tolist()
    next_tag = None
    if open_tags:
        changed_tags = [tag for tag in open_tags if tag != current_tag]
        next_tag = changed_tags[0] if changed_tags else open_tags[0]

    next_id = tag_to_mouse[next_tag]["id"] if next_tag in tag_to_mouse else None
    if next_id != current_id:
        st.session_state.selected_mouse_id = next_id
        st.rerun()

    assign_tags = edited.loc[edited["Assign"].fillna(False), "ID"].astype(str).tolist()
    _render_mouse_table_assign_controls(assign_tags, tag_to_mouse)

    if current_id is not None:
        selected = next((mouse for mouse in mice if mouse["id"] == current_id), None)
        if selected:
            st.divider()
            _mouse_detail(selected)


def _render_mouse_table_assign_controls(assign_tags, tag_to_mouse):
    selected_mice = [tag_to_mouse[tag] for tag in assign_tags if tag in tag_to_mouse]
    selected_live = [m for m in selected_mice if m["status"] != "dead"]
    skipped_dead = len(selected_mice) - len(selected_live)
    active_cages = db.get_all_breeding_cages(status_filter="active")

    if not selected_mice:
        st.caption("Select one or more mice in the Assign column to move them into a cage.")
        return
    if not active_cages:
        st.info("No active cages available.")
        return

    cage_options = {cage_assignment_option_label(cage): cage for cage in active_cages}
    a1, a2, a3 = st.columns([1.1, 3, 1.2])
    a1.markdown(f'<div class="toolbar-count">{len(selected_live)} selected</div>', unsafe_allow_html=True)
    target_label = a2.selectbox("Target cage", list(cage_options.keys()), key="mouse_table_target_cage")
    assign = a3.button(
        "Assign to cage",
        key="mouse_table_assign_to_cage",
        type="primary",
            width="stretch",
        disabled=not selected_live,
    )

    if skipped_dead:
        st.caption(f"{skipped_dead} dead mouse/mice skipped.")

    if assign:
        target_cage = cage_options[target_label]
        moved = assign_table_mice_to_cage([m["id"] for m in selected_live], target_cage)
        st.session_state.mouse_table_assign_version = st.session_state.get("mouse_table_assign_version", 0) + 1
        st.session_state.mouse_table_notice = f"Assigned {moved} mouse/mice to {target_cage['cage_label']}."
        st.rerun()


def _render_mouse_card(mouse):
    selected = st.session_state.get("selected_mouse_id") == mouse["id"]
    geno = genotype_summary(mouse["id"])
    genes = mouse_gene_names(mouse["id"])
    age = mouse_age_label(mouse["birth_date"])
    sym = sex_symbol(mouse["sex"])
    status_label = MOUSE_STATUS_LABELS.get(mouse["status"], mouse["status"])
    sex_class = {"M": "sex-m", "F": "sex-f"}.get(mouse["sex"], "sex-u")
    card_class = "mouse-card mouse-card-selected" if selected else "mouse-card"
    genotype_text = geno if geno != "—" else "No genotype recorded"
    parent_bits = []
    if mouse["father_tag"]:
        parent_bits.append(f"♂ {mouse['father_tag']}")
    if mouse["mother_tag"]:
        parent_bits.append(f"♀ {mouse['mother_tag']}")
    parent_line = " · ".join(parent_bits) if parent_bits else "No parents recorded"

    with st.container():
        st.markdown(
            f'<div class="{card_class}">'
            f'<div class="card-top">'
            f'<div style="display:flex;align-items:center;gap:0.45rem;min-width:0;">'
            f'<span class="sex-pill {sex_class}">{esc(sym)}</span>'
            f'<span class="card-title">{esc(mouse["ear_tag"])}</span>'
            f'</div>'
            f'<span class="status-pill tone-{esc(mouse["status"])}">{esc(status_label)}</span>'
            f'</div>'
            f'<div class="card-genotype">{esc(genotype_text)}</div>'
            f'{gene_stripe_html(genes, geno)}'
            f'<div class="card-meta">{esc(age)} · {esc(parent_line)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Close" if selected else "Open",
            key=f"sel_mouse_{mouse['id']}",
            width="stretch",
            type="primary" if selected else "secondary",
        ):
            st.session_state.selected_mouse_id = None if selected else mouse["id"]
            st.rerun()


def _mouse_genotype_editor(mouse, show_header=True):
    mouse_id = mouse["id"]
    genos = list(db.get_mouse_genotypes(mouse_id))

    if show_header:
        st.markdown('<div class="detail-section-title">Genotypes</div>', unsafe_allow_html=True)
        if not genos:
            st.info("No genotypes recorded for this mouse yet.")
        else:
            st.markdown(
                f'<div class="compact-muted">{esc(genotype_summary(mouse_id))}</div>',
                unsafe_allow_html=True,
            )
    elif not genos:
        st.info("No genotypes recorded for this mouse yet.")

    existing_gene_keys = {g["gene"].strip().lower() for g in genos}

    for g in genos:
        with st.form(f"mouse_geno_edit_{mouse_id}_{g['id']}"):
            gc1, gc2, gc3, gc4, gc5, gc6 = st.columns([2.2, 1.2, 1.2, 0.9, 1, 1])
            gene_options = gene_choices([g["gene"]]) + ["Other..."]
            gene_choice = gc1.selectbox(
                "Gene",
                gene_options,
                index=gene_options.index(g["gene"]) if g["gene"] in gene_options else 0,
                key=f"mg_gene_{mouse_id}_{g['id']}",
                label_visibility="collapsed",
            )
            new_gene = gene_choice
            if gene_choice == "Other...":
                new_gene = gc1.text_input(
                    "Custom gene",
                    value=g["gene"],
                    key=f"mg_gene_custom_{mouse_id}_{g['id']}",
                    label_visibility="collapsed",
                )
            with gc2:
                new_a1 = allele_input(
                    "Allele 1",
                    key=f"mg_a1_{mouse_id}_{g['id']}",
                    default=g["allele1"],
                    compact=True,
                )
            with gc3:
                new_a2 = allele_input(
                    "Allele 2",
                    key=f"mg_a2_{mouse_id}_{g['id']}",
                    default=g["allele2"],
                    compact=True,
                )
            gc4.write(zygosity(new_a1, new_a2))
            save = gc5.form_submit_button("Save")
            delete = gc6.form_submit_button("Delete", type="secondary")

            if save:
                new_gene = new_gene.strip()
                new_key = new_gene.lower()
                old_key = g["gene"].strip().lower()
                if not new_gene:
                    st.error("Gene name is required.")
                elif new_key != old_key and new_key in existing_gene_keys:
                    st.error(f"{mouse['ear_tag']} already has genotype data for {new_gene}.")
                else:
                    if new_key != old_key:
                        db.delete_genotype(g["id"])
                    db.set_genotype(mouse_id, new_gene, new_a1.strip() or "?", new_a2.strip() or "?")
                    st.success("Genotype updated.")
                    st.rerun()

            if delete:
                db.delete_genotype(g["id"])
                st.warning(f"Deleted {g['gene']} genotype.")
                st.rerun()

    st.markdown('<div class="compact-muted">Add gene to this mouse</div>', unsafe_allow_html=True)
    add_options = [g for g in gene_choices() if g.strip().lower() not in existing_gene_keys] + ["Other..."]
    with st.form(f"mouse_geno_add_{mouse_id}"):
        ac1, ac2, ac3, ac4 = st.columns([2.2, 1.2, 1.2, 1])
        add_gene_choice = ac1.selectbox(
            "Gene",
            add_options,
            key=f"mg_add_gene_{mouse_id}",
            label_visibility="collapsed",
        )
        add_gene = add_gene_choice
        if add_gene_choice == "Other...":
            add_gene = ac1.text_input(
                "Custom gene",
                key=f"mg_add_gene_custom_{mouse_id}",
                label_visibility="collapsed",
                placeholder="Gene name",
            )
        with ac2:
            add_a1 = allele_input("Allele 1", key=f"mg_add_a1_{mouse_id}", compact=True)
        with ac3:
            add_a2 = allele_input("Allele 2", key=f"mg_add_a2_{mouse_id}", compact=True)
        add = ac4.form_submit_button("Add")

        if add:
            add_gene = add_gene.strip()
            if not add_gene or add_gene == "Other...":
                st.error("Choose or type a gene name first.")
            elif add_gene.lower() in existing_gene_keys:
                st.error(f"{mouse['ear_tag']} already has genotype data for {add_gene}.")
            else:
                db.set_genotype(mouse_id, add_gene, add_a1.strip() or "?", add_a2.strip() or "?")
                st.success("Genotype added.")
                st.rerun()


def _mouse_detail(mouse):
    geno_summary = genotype_summary(mouse["id"])
    genes = mouse_gene_names(mouse["id"])
    detail_items = [
        ("Ear Tag", mouse["ear_tag"]),
        ("Age", mouse_age_label(mouse["birth_date"])),
        ("Sex", sex_display(mouse["sex"])),
        ("Status", status_badge(mouse["status"])),
        ("Birth Date", mouse["birth_date"] or "?"),
        ("Cage", mouse["cage_location"] or "?"),
        ("Father", mouse["father_tag"] or "—"),
        ("Mother", mouse["mother_tag"] or "—"),
        ("Notes", mouse["notes"] or "—"),
    ]
    detail_html = "".join(
        f'<div class="mouse-detail-item">'
        f'<div class="mouse-detail-label">{esc(label)}</div>'
        f'<div class="mouse-detail-value">{esc(value)}</div>'
        f'</div>'
        for label, value in detail_items
    )
    st.markdown(
        f"""
        <div class="mouse-detail-header">
            <div class="mouse-detail-title">{esc(mouse_display_title(mouse))}</div>
            {gene_stripe_html(genes, geno_summary)}
        </div>
        <div class="mouse-detail-grid">{detail_html}</div>
        """,
        unsafe_allow_html=True,
    )

    geno_label = genotype_summary(mouse["id"])
    if geno_label and geno_label != "—":
        if len(geno_label) > 72:
            geno_label = f"{geno_label[:69]}..."
        expander_label = f"Genotypes · {geno_label}"
    else:
        expander_label = "Genotypes"
    with st.expander(expander_label, expanded=False):
        _mouse_genotype_editor(mouse, show_header=False)

    with st.expander("📜 Pedigree Tree (up to 3 generations)"):
        tree = render_pedigree(mouse["ear_tag"])
        st.markdown(f"```\n{tree}\n```")

    with st.expander("Edit Mouse", expanded=False):
        delete_impact = db.get_mouse_delete_impact(mouse["id"])
        with st.form(f"edit_mouse_{mouse['id']}"):
            ec1, ec2, ec3 = st.columns(3)
            new_tag = ec1.text_input("Ear Tag", value=mouse["ear_tag"], key=f"et_{mouse['id']}")
            current_live_status = normalize_mouse_status(mouse["status"])
            if current_live_status not in MOUSE_LIVE_STATUS_OPTIONS:
                current_live_status = "holding"
            new_sex = ec2.selectbox(
                "Sex",
                ["M", "F", "U"],
                index=["M", "F", "U"].index(mouse["sex"]),
                key=f"sx_{mouse['id']}",
                format_func=sex_option_label,
            )
            new_status = ec3.selectbox(
                "Status",
                MOUSE_LIVE_STATUS_OPTIONS,
                index=MOUSE_LIVE_STATUS_OPTIONS.index(current_live_status),
                format_func=lambda x: MOUSE_STATUS_LABELS[x],
                key=f"st_{mouse['id']}",
            )
            ec4, ec5 = st.columns(2)
            new_birth = ec4.text_input("Birth Date", value=mouse["birth_date"] or "", key=f"bd_{mouse['id']}")
            new_location = ec4.text_input("Cage Location", value=mouse["cage_location"] or "", key=f"cl_{mouse['id']}")
            new_father = ec5.text_input("Father Tag", value=mouse["father_tag"] or "", key=f"ft_{mouse['id']}")
            new_mother = ec5.text_input("Mother Tag", value=mouse["mother_tag"] or "", key=f"mt_{mouse['id']}")
            new_notes = st.text_area("Notes", value=mouse["notes"] or "", key=f"nt_{mouse['id']}")

            st.caption(
                "Deleting also removes "
                f"{delete_impact['genotypes']} genotype, "
                f"{delete_impact['weights']} weight and "
                f"{delete_impact['survival']} endpoint record(s). "
                f"It is linked to {delete_impact['cage_links']} cage(s)."
            )
            confirm_delete = st.checkbox(
                "Confirm permanent deletion",
                value=False,
                key=f"confirm_delete_mouse_{mouse['id']}",
            )

            btn_col1, btn_col2, _ = st.columns([1, 1, 4])
            save = btn_col1.form_submit_button("💾 Save")
            delete = btn_col2.form_submit_button(
                "🗑️ Delete",
                type="secondary",
            )

            if save:
                db.update_mouse(
                    mouse["id"],
                    ear_tag=new_tag.strip(),
                    sex=new_sex,
                    status=new_status,
                    birth_date=new_birth.strip() or None,
                    father_tag=new_father.strip() or None,
                    mother_tag=new_mother.strip() or None,
                    cage_location=new_location.strip() or None,
                    notes=new_notes.strip() or None,
                )
                st.success("Updated.")
                st.rerun()

            if delete:
                if not confirm_delete:
                    st.error("Check the confirmation box before deleting this mouse.")
                    return
                db.safe_delete_mouse(mouse["id"])
                st.session_state.selected_mouse_id = None
                st.warning(f"Deleted mouse '{mouse['ear_tag']}'.")
                st.rerun()

        if mouse["status"] != "dead":
            st.divider()
            st.markdown("**Mark dead**")
            with st.form(f"edit_mouse_mark_dead_{mouse['id']}"):
                d1, d2 = st.columns([1, 1.35])
                death_date = d1.date_input(
                    "Death date",
                    value=date.today(),
                    key=f"edit_mouse_death_date_{mouse['id']}",
                )
                death_method = d2.selectbox(
                    "Death method",
                    DEATH_METHODS,
                    key=f"edit_mouse_death_method_{mouse['id']}",
                )
                death_notes = st.text_input(
                    "Death notes",
                    key=f"edit_mouse_death_notes_{mouse['id']}",
                )
                mark_dead = st.form_submit_button("Mark dead", type="secondary")
                if mark_dead:
                    try:
                        db.mark_mouse_dead(
                            mouse["id"],
                            str(death_date),
                            death_method,
                            death_notes.strip() or None,
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                        return
                    st.session_state.selected_mouse_id = None
                    st.warning(f"Marked {mouse['ear_tag']} as dead.")
                    st.rerun()
        else:
            st.caption("This mouse is already in Death Archive.")


def _mouse_detail_simple(mouse):
    """Compact mouse detail view for cage context (no edit form)."""
    st.markdown(f"**{mouse_display_title(mouse)}**")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Ear Tag:**", mouse["ear_tag"])
        st.write("**Age:**", mouse_age_label(mouse["birth_date"]))
        st.write("**Sex:**", sex_display(mouse["sex"]))
        st.write("**Birth Date:**", mouse["birth_date"] or "?")
        st.write("**Father (父本):**", mouse["father_tag"] or "—")
    with c2:
        st.write("**Mother (母本):**", mouse["mother_tag"] or "—")
        st.write("**Status:**", status_badge(mouse["status"]))
        st.write("**Cage Location:**", mouse["cage_location"] or "?")
        st.write("**Notes:**", mouse["notes"] or "—")

    st.divider()
    st.write("**Genotypes:**", genotype_summary(mouse["id"]))

    with st.expander("📜 Pedigree Tree (up to 3 generations)"):
        tree = render_pedigree(mouse["ear_tag"])
        st.markdown(f"```\n{tree}\n```")

# ── Breeding Cages ────────────────────────────────────────────────

def cages_page():
    render_page_header()
    inject_cage_styles()

    tab_cages, tab_add = st.tabs(["📋 View Cages", "➕ New Cage"])

    with tab_add:
        _add_cage_form()

    with tab_cages:
        _cage_list()


def _add_cage_form():
    cage_type = st.radio(
        "Cage Type",
        ["breeding", "holding"],
        horizontal=True,
        format_func=lambda x: "Breeding Cage" if x == "breeding" else "Holding Cage",
        key="new_cage_type",
    )

    with st.form("add_cage"):
        c1, c2 = st.columns(2)
        cage_label = c1.text_input("Cage Label / ID *")
        setup_date = c2.date_input("Setup Date", value=date.today())

        # Get unassigned mice (not already placed in another cage)
        all_mice = db.get_all_mice()
        unassigned = [m for m in all_mice if not (m["cage_location"] or "").strip()]
        st.caption(f"{len(unassigned)} unassigned mice available")

        selected_male_id = None
        selected_female_ids = []
        selected_occupant_ids = []
        if cage_type == "breeding":
            male_candidates = [m for m in unassigned if m["sex"] in ("M", "U")]
            female_candidates = [m for m in unassigned if m["sex"] in ("F", "U")]
            male_label_to_id, _ = mouse_label_maps(male_candidates)
            female_label_to_id, _ = mouse_label_maps(female_candidates)
            p1, p2 = st.columns(2)
            selected_male_label = p1.selectbox(
                "Male",
                ["—"] + list(male_label_to_id.keys()),
                key="new_cage_male",
            )
            selected_male_id = male_label_to_id.get(selected_male_label)
            female_options = [
                label for label, mouse_id in female_label_to_id.items()
                if mouse_id != selected_male_id
            ]
            selected_female_labels = p2.multiselect(
                "Females",
                female_options,
                key="new_cage_females",
                placeholder="Choose female mice...",
            )
            selected_female_ids = [female_label_to_id[label] for label in selected_female_labels]
        else:
            occupant_label_to_id, _ = mouse_label_maps(unassigned)
            selected_occupant_labels = st.multiselect(
                "Mice",
                list(occupant_label_to_id.keys()),
                key="new_cage_occupants",
                placeholder="Choose mice for this holding cage...",
            )
            selected_occupant_ids = [occupant_label_to_id[label] for label in selected_occupant_labels]

        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Create Cage")
        if submitted:
            if not cage_label.strip():
                st.error("Cage label is required.")
            else:
                existing = db.get_all_breeding_cages()
                if any(c["cage_label"] == cage_label.strip() for c in existing):
                    st.error(f"Cage '{cage_label.strip()}' already exists.")
                else:
                    cage_id = db.add_breeding_cage(
                        cage_label=cage_label.strip(),
                        cage_type=cage_type,
                        male_id=selected_male_id if cage_type == "breeding" else None,
                        setup_date=str(setup_date),
                        notes=notes.strip() or None,
                    )
                    mouse_ids = (
                        ([selected_male_id] if selected_male_id else []) + selected_female_ids
                        if cage_type == "breeding" else selected_occupant_ids
                    )
                    db.set_cage_females(cage_id, selected_female_ids if cage_type == "breeding" else selected_occupant_ids)
                    cage_status = "breeding" if cage_type == "breeding" else "holding"
                    for mouse_id in mouse_ids:
                        db.update_mouse(mouse_id, status=cage_status, cage_location=cage_label.strip())
                    st.success(f"Cage '{cage_label.strip()}' created.")
                    st.rerun()


def _cage_list():
    cf1, cf2, cf3, cf4 = st.columns([1, 1, 1.25, 2])
    status_filter = cf1.selectbox(
        "Filter by status", ["active", "separated", "ended", "All"],
        key="cage_filter",
    )
    type_filter = cf2.selectbox(
        "Filter by type", ["All", "breeding", "holding"],
        key="cage_type_filter",
    )
    gene_filter = cf3.multiselect(
        "Filter by Genes",
        db.get_distinct_genes(),
        key="cage_gene_filter",
        placeholder="All genes...",
    )
    search_query = cf4.text_input("Search cage", placeholder="Cage label / parent / notes...")

    cages = db.get_all_breeding_cages(
        status_filter=None if status_filter == "All" else status_filter
    )
    if type_filter != "All":
        cages = [c for c in cages if c["cage_type"] == type_filter]
    if gene_filter:
        required_genes = set(gene_filter)
        cages = [c for c in cages if required_genes.issubset(cage_gene_set(c))]
    if search_query.strip():
        q = search_query.strip().lower()
        cages = [
            c for c in cages
            if q in (c["cage_label"] or "").lower()
            or q in (c["male_tag"] or "").lower()
            or q in (c["female_tags"] or "").lower()
            or q in (c["notes"] or "").lower()
        ]

    split_due_count = len(due_litters()) + len(due_split_reminders())
    if split_due_count:
        st.warning(f"{split_due_count} split reminder(s) are due today or overdue.")
    else:
        st.success("No split reminders are due today.")

    if not cages:
        st.info("No cages match the current filters.")
        return

    if "selected_cage_id" not in st.session_state:
        st.session_state.selected_cage_id = None

    valid_ids = {c["id"] for c in cages}
    if st.session_state.selected_cage_id is not None and st.session_state.selected_cage_id not in valid_ids:
        st.session_state.selected_cage_id = None

    breeding_cages = [c for c in cages if c["cage_type"] == "breeding"]
    holding_cages = [c for c in cages if c["cage_type"] == "holding"]

    if type_filter in ("All", "breeding"):
        _render_cage_section("Breeding cages", breeding_cages)
    if type_filter in ("All", "holding"):
        _render_cage_section("Holding cages", holding_cages)


def cage_label_sort_key(cage):
    parts = re.split(r"(\d+)", str(cage["cage_label"] or "").lower())
    return [int(part) if part.isdigit() else part for part in parts]


def cage_group_label(genes):
    return " + ".join(genes) if genes else "No genotype"


def grouped_cages_by_gene(cages):
    groups = {}
    for cage in cages:
        key = tuple(cage_gene_names(cage))
        groups.setdefault(key, []).append(cage)

    grouped = [
        (genes, sorted(group_cages, key=cage_label_sort_key))
        for genes, group_cages in groups.items()
    ]
    return sorted(
        grouped,
        key=lambda item: (
            len(item[0]) == 0,
            -len(item[1]),
            cage_group_label(item[0]).lower(),
        ),
    )


def _render_cage_group_header(genes, cages):
    label = cage_group_label(genes)
    count = len(cages)
    count_label = f"{count} cage" if count == 1 else f"{count} cages"
    st.markdown(
        f'<div class="cage-group-header">'
        f'<div class="cage-group-title">'
        f'<span class="cage-group-stripe" style="{gene_stripe_style(genes)}" title="{esc(label)}"></span>'
        f'<span class="cage-group-name">{esc(label)}</span>'
        f'</div>'
        f'<span class="cage-group-count">{esc(count_label)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_cage_rows(cages):
    for row_start in range(0, len(cages), 3):
        row = cages[row_start:row_start + 3]
        cols = st.columns(3, gap="medium")
        for col, cage in zip(cols, row):
            with col:
                _render_cage_card(cage)

        if st.session_state.selected_cage_id is not None:
            selected_in_row = [
                c for c in row if c["id"] == st.session_state.selected_cage_id
            ]
            if selected_in_row:
                _render_cage_detail(selected_in_row[0])
                st.divider()


def _render_cage_section(title, cages):
    if not cages:
        return

    st.markdown(f'<div class="cage-section-title">{esc(title)}</div>', unsafe_allow_html=True)
    section_key = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    for group_index, (genes, group_cages) in enumerate(grouped_cages_by_gene(cages)):
        with st.container(key=f"cage_group_{section_key}_{group_index}"):
            _render_cage_group_header(genes, group_cages)
            _render_cage_rows(group_cages)


def _render_cage_card(cage):
    selected = st.session_state.get("selected_cage_id") == cage["id"]
    is_breeding = cage["cage_type"] == "breeding"
    litters = db.get_litters_for_cage(cage["id"]) if is_breeding else []
    active_litters = [litter for litter in litters if not litter["weaning_date"]]
    latest_litter = active_litters[0] if active_litters else (litters[0] if litters else None)
    active_reminders = db.get_split_reminders_for_cage(cage["id"], active_only=True) if is_breeding else []
    split_reminder = active_reminders[0] if active_reminders else None
    mice = cage_mice(cage)
    genes = cage_gene_names(cage)
    type_label = "Breeding" if is_breeding else "Holding"
    card_class = "cage-card cage-card-selected" if selected else "cage-card"
    type_tone = "inactive" if cage["status"] != "active" else ("breeding" if is_breeding else "holding")

    if is_breeding:
        female_tags = female_tag_list(cage)
        if cage["male_tag"] or female_tags:
            parent_html = (
                f'<div class="card-genotype">'
                f'<div class="card-genotype-line">♂ {esc(cage["male_tag"] or "not set")}</div>'
                f'<div class="card-genotype-line">♀ {esc(", ".join(female_tags) if female_tags else "not set")}</div>'
                f'</div>'
            )
        else:
            parent_html = (
                f'<div class="card-genotype">'
                f'<div class="card-genotype-line">Parents not set</div>'
                f'</div>'
            )
        if latest_litter and not latest_litter["weaning_date"]:
            litter_tone = litter_split_tone(latest_litter)
            litter_status = litter_split_status(latest_litter)
            litter_line = f"Latest litter {latest_litter['birth_date']} · {latest_litter['total_born'] or '?'} born"
        elif split_reminder:
            litter_tone = split_reminder_tone(split_reminder)
            litter_status = split_reminder_status(split_reminder)
            litter_line = f"Split reminder {split_reminder['due_date']}"
        else:
            litter_tone = "muted"
            litter_status = "No reminder"
            litter_line = "No split reminder"
        bottom_html = (
            f'<div class="card-meta">{esc(litter_line)}</div>'
            f'<div style="margin-top:0.45rem;">'
            f'<span class="status-pill tone-{esc(litter_tone)}">{esc(litter_status)}</span>'
            f'</div>'
        )
    else:
        parent_line = cage["notes"] or ""
        parent_html = (
            f'<div class="card-genotype">'
            f'<div class="card-genotype-line">{esc(parent_line)}</div>'
            f'</div>'
        )
        bottom_html = '<div class="card-bottom-spacer"></div>'

    with st.container():
        st.markdown(
            f'<div class="{card_class}">'
            f'<div class="card-top">'
            f'<span class="card-title">{esc(cage["cage_label"])}</span>'
            f'<span class="status-pill tone-{type_tone}">{esc(type_label)}</span>'
            f'</div>'
            f'<div class="card-meta">{esc(cage["status"])} · {len(mice)} mice</div>'
            f'{gene_stripe_html(genes, ", ".join(genes))}'
            f'{parent_html}'
            f'{bottom_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            f"Open {cage['cage_label']}",
            key=f"cage_click_{cage['id']}",
            width="stretch",
        ):
            st.session_state.selected_cage_id = None if selected else cage["id"]
            st.rerun()


def _render_cage_detail(cage):
    is_breeding = cage["cage_type"] == "breeding"
    type_badge = "Breeding" if is_breeding else "Holding"
    mice = cage_mice(cage)

    with st.container(border=True):
        title_col, close_col = st.columns([5, 1])
        title_col.subheader(f"{cage['cage_label']} details")
        if close_col.button("Close details", key=f"close_cage_{cage['id']}", width="stretch"):
            st.session_state.selected_cage_id = None
            st.rerun()

        c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.1, 2])
        c1.caption("Type")
        c1.markdown(f"**{type_badge}**")
        c2.caption("Setup")
        c2.markdown(f"**{cage['setup_date'] or '—'}**")
        c3.caption("Status")
        c3.markdown(f"**{cage['status']}**")
        if is_breeding:
            females = female_tag_list(cage)
            c4.caption("Parents")
            c4.markdown(
                f"**M:** {cage['male_tag'] or 'not set'} &nbsp; "
                f"**F:** {', '.join(females) if females else 'not set'}",
                unsafe_allow_html=True,
            )
        else:
            c4.caption("Notes")
            c4.markdown(f"**{cage['notes'] or '—'}**")

        if is_breeding:
            with st.expander("Record litter and number pups", expanded=False):
                _record_litter_form(cage, show_title=False)

            with st.expander("Split reminder", expanded=False):
                _render_split_reminder_panel(cage)

            with st.expander("Litter history", expanded=True):
                _render_litter_history(cage, show_title=False)

        with st.expander(f"Mice in this cage ({len(mice)})", expanded=False):
            _render_cage_mice(cage, show_title=False)

        with st.expander("Edit cage / parents", expanded=False):
            _edit_cage_form(cage)


def _render_split_reminder_panel(cage):
    reminders = db.get_split_reminders_for_cage(cage["id"])
    active = [reminder for reminder in reminders if not reminder["resolved"]]

    if active:
        for reminder in active:
            tone = split_reminder_tone(reminder)
            c1, c2, c3, c4 = st.columns([1.1, 2.6, 0.75, 0.75])
            c1.markdown(
                f"<span class='cage-status cage-status-{tone}'>{split_reminder_status(reminder)}</span>",
                unsafe_allow_html=True,
            )
            note = f"Due {reminder['due_date']}"
            if reminder["notes"]:
                note += f" · {reminder['notes']}"
            c2.markdown(f"**{note}**")
            if c3.button("Done", key=f"done_split_reminder_{reminder['id']}", width="stretch"):
                db.resolve_split_reminder(reminder["id"], str(date.today()))
                st.rerun()
            if c4.button("Delete", key=f"del_split_reminder_{reminder['id']}", width="stretch"):
                db.delete_split_reminder(reminder["id"])
                st.rerun()
    else:
        st.caption("No active split reminders.")

    with st.form(f"add_split_reminder_{cage['id']}"):
        r1, r2, r3, r4 = st.columns([1.1, 1.2, 2.5, 0.9])
        birth = r1.date_input(
            "Birth date",
            value=date.today(),
            key=f"split_rem_birth_{cage['id']}",
        )
        due = birth + timedelta(days=WEANING_DAYS)
        r2.markdown(f"**Due {due}**")
        notes = r3.text_input("Notes", key=f"split_rem_notes_{cage['id']}")
        submitted = r4.form_submit_button("Add")
        if submitted:
            db.add_split_reminder(cage["id"], str(due), notes.strip() or None)
            st.success("Split reminder added.")
            st.rerun()


def _record_litter_form(cage, show_title=True):
    if show_title:
        st.markdown("**Record litter and number pups**")
    females = female_tag_list(cage)
    default_prefix = cage["cage_label"].replace(" ", "-")

    # Auto-detect genes from parents
    parent_genes = []
    seen = set()
    for parent_tag in [cage["male_tag"]] + females:
        if not parent_tag:
            continue
        parent = db.get_mouse_by_tag(parent_tag)
        if parent:
            for g in db.get_mouse_genotypes(parent["id"]):
                gene = g["gene"]
                if gene not in seen:
                    seen.add(gene)
                    parent_genes.append(gene)

    # Use litter form key prefix
    lk = f"lit_{cage['id']}"

    r1c1, r1c2, r1c3 = st.columns([1, 1, 1])
    birth = r1c1.date_input("Birth date", value=date.today(), key=f"{lk}_birth")
    if len(females) > 1:
        mother_tag = r1c3.selectbox("Mother", ["—"] + females, key=f"{lk}_mother")
        mother_tag = None if mother_tag == "—" else mother_tag
    else:
        mother_tag = females[0] if females else None
        r1c3.text_input("Mother", value=mother_tag or "—", disabled=True)

    tag_prefix = r1c2.text_input("Tag prefix", value=default_prefix, key=f"{lk}_pfx")

    # Pup count control
    if f"{lk}_count" not in st.session_state:
        st.session_state[f"{lk}_count"] = 4
    count = st.session_state[f"{lk}_count"]

    bc1, bc2, bc3, bc4, _ = st.columns([1, 1, 1.6, 1.4, 4])
    if bc1.button("➖ Remove", key=f"{lk}_minus"):
        st.session_state[f"{lk}_count"] = max(1, count - 1)
        st.rerun()
    if bc2.button("➕ Add", key=f"{lk}_plus"):
        st.session_state[f"{lk}_count"] = min(20, count + 1)
        st.rerun()
    bc3.write(f"**{st.session_state[f'{lk}_count']} pups**")
    if bc4.button("📋 Copy Geno", key=f"{lk}_copy_geno", help="Copy first pup's genotypes to all"):
        if count > 1 and parent_genes:
            for gi in range(len(parent_genes)):
                a1_val = st.session_state.get(f"{lk}_a1_{gi}_0", "?")
                a2_val = st.session_state.get(f"{lk}_a2_{gi}_0", "?")
                for i in range(1, count):
                    st.session_state[f"{lk}_a1_{gi}_{i}"] = a1_val
                    st.session_state[f"{lk}_a2_{gi}_{i}"] = a2_val
        st.rerun()

    count = st.session_state[f"{lk}_count"]

    # Table header
    n_gene_cols = len(parent_genes)
    hcols = st.columns([1, 2.2, 1.45] + [2] * n_gene_cols)
    hcols[0].caption("")
    hcols[1].caption("Ear Tag / ID")
    hcols[2].caption("Sex")
    for gi, gene in enumerate(parent_genes):
        hcols[3 + gi].caption(gene)

    # Table rows
    ear_tags = []
    sexes = []
    gene_alleles = {g: [] for g in parent_genes}

    for i in range(count):
        start_num = 1
        suggested_tag = f"{tag_prefix.strip()}-{int(start_num) + i:02d}" if tag_prefix.strip() else ""
        if f"{lk}_tag_{i}" not in st.session_state:
            st.session_state[f"{lk}_tag_{i}"] = suggested_tag

        rcols = st.columns([1, 2.2, 1.45] + [2] * n_gene_cols)
        rcols[0].caption(f"#{i+1}")
        with rcols[1]:
            tag = st.text_input(
                "Ear Tag / ID", key=f"{lk}_tag_{i}",
                label_visibility="collapsed", placeholder=suggested_tag,
            )
            ear_tags.append(tag.strip())
        with rcols[2]:
            s = st.selectbox(
                "Sex",
                ["U", "M", "F"],
                key=f"{lk}_sex_{i}",
                label_visibility="collapsed",
                format_func=sex_option_label,
            )
            sexes.append(s)
        for gi, gene in enumerate(parent_genes):
            with rcols[3 + gi]:
                aac1, aac2 = st.columns(2)
                with aac1:
                    a1 = allele_input("A1", key=f"{lk}_a1_{gi}_{i}", compact=True)
                with aac2:
                    a2 = allele_input("A2", key=f"{lk}_a2_{gi}_{i}", compact=True)
                gene_alleles[gene].append((a1, a2))

    notes = st.text_area("Notes", key=f"{lk}_notes")

    # Submit
    if st.button("📝 Record Litter & Create Pups", key=f"{lk}_submit"):
        missing = [str(i + 1) for i, tag in enumerate(ear_tags) if not tag]
        dupes = sorted({t for t in ear_tags if t and ear_tags.count(t) > 1})
        existing = db.find_existing_ear_tags(ear_tags)

        if missing:
            st.error("Ear Tag / ID is required for row(s): " + ", ".join(missing))
        elif dupes:
            st.error("Duplicate Ear Tag / ID: " + ", ".join(dupes))
        elif existing:
            st.error("Ear Tag / ID already exists: " + ", ".join(existing))
        else:
            litter_id = db.add_litter(
                cage_id=cage["id"],
                birth_date=str(birth),
                total_born=count,
                notes=notes.strip() or None,
            )
            for i in range(count):
                tag = ear_tags[i]
                mid = db.add_mouse(
                    ear_tag=tag,
                    birth_date=str(birth),
                    sex=sexes[i],
                    father_tag=cage["male_tag"] or None,
                    mother_tag=mother_tag,
                    birth_cage_id=cage["id"],
                    litter_id=litter_id,
                    status="waiting_split",
                    cage_location=cage["cage_label"],
                    notes=f"From litter #{litter_id}",
                )
                for gene in parent_genes:
                    a1, a2 = gene_alleles[gene][i]
                    db.set_genotype(mid, gene, a1.strip() or "?", a2.strip() or "?")
            st.success(f"Recorded litter #{litter_id} with {count} pups.")
            st.rerun()


def _render_litter_history(cage, show_title=True):
    if show_title:
        st.markdown("**Litters**")
    litters = db.get_litters_for_cage(cage["id"])
    if not litters:
        st.caption("No litters recorded yet.")
        return

    for litter in litters:
        pups = db.get_mice_by_litter(litter["id"])
        tone = litter_split_tone(litter)
        with st.container(border=True):
            h1, h2, h3, h4 = st.columns([1.2, 1, 1.2, 1])
            h1.markdown(f"**Born:** {litter['birth_date']}")
            h2.markdown(f"**Count:** {litter['total_born'] or '?'}")
            h3.markdown(
                f"<span class='cage-status cage-status-{tone}'>{litter_split_status(litter)}</span>",
                unsafe_allow_html=True,
            )
            h4.markdown(f"**Pups:** {len(pups)}")
            if litter["notes"]:
                st.caption(litter["notes"])

            _render_pup_table(pups)
            if litter["weaning_date"]:
                st.success(
                    f"Split on {litter['weaning_date']} · "
                    f"{litter['weaned_count'] or len(pups)} pups"
                )
            elif pups:
                _split_litter_form(cage, litter, pups)
            else:
                st.caption("No numbered pups are linked to this litter yet.")

            _delete_litter_form(litter, pups)


def _render_pup_table(pups):
    if not pups:
        return
    rows = []
    for pup in pups:
        rows.append({
            "Tag": pup["ear_tag"],
            "Sex": sex_display(pup["sex"]),
            "Cage": pup["cage_location"] or "—",
            "Status": pup["status"],
            "Genotype": genotype_summary(pup["id"]),
        })
    st.dataframe(rows, width="stretch", hide_index=True)


def _delete_litter_form(litter, pups):
    with st.expander("Delete litter"):
        st.caption(
            "Confirm before removing this litter. By default, linked pups are kept and only unlinked from this litter."
        )
        with st.form(f"delete_litter_{litter['id']}"):
            confirm_delete = st.checkbox(
                "I understand, delete this litter",
                value=False,
                key=f"del_confirm_{litter['id']}",
            )
            delete_pups = st.checkbox(
                f"Also delete {len(pups)} linked pup(s)",
                value=False,
                disabled=not pups,
                key=f"del_pups_{litter['id']}",
            )
            submitted = st.form_submit_button("Delete litter", type="secondary")
            if submitted:
                if not confirm_delete:
                    st.error("Check the confirmation box before deleting.")
                    return
                db.delete_litter(litter["id"], delete_pups=delete_pups)
                if delete_pups:
                    st.warning(f"Deleted litter and {len(pups)} linked pup(s).")
                else:
                    st.warning("Deleted litter. Linked pups were kept.")
                st.rerun()


def _split_litter_form(cage, litter, pups):
    due = litter_due_date(litter) or date.today()
    default_split = date.today()
    if due > date.today():
        default_split = due

    with st.form(f"split_litter_{litter['id']}"):
        st.markdown("**Split into holding cages**")
        s1, s2, s3 = st.columns([1, 1.4, 1.4])
        split_date = s1.date_input("Split date", value=default_split, key=f"split_date_{litter['id']}")
        label_suffix = split_date.strftime("%m%d")
        male_label = s2.text_input(
            "Male holding cage",
            value=f"{cage['cage_label']}-M-{label_suffix}",
            key=f"split_male_{litter['id']}",
        )
        female_label = s3.text_input(
            "Female holding cage",
            value=f"{cage['cage_label']}-F-{label_suffix}",
            key=f"split_female_{litter['id']}",
        )

        st.caption("Confirm sex for each pup before splitting.")
        assignments = []
        for pup in pups:
            default = pup["sex"] if pup["sex"] in ("M", "F") else "—"
            options = ["—", "M", "F"]
            cols = st.columns([2, 1, 3])
            cols[0].markdown(f"**{pup['ear_tag']}**")
            sex = cols[1].selectbox(
                "Sex",
                options,
                index=options.index(default),
                key=f"split_sex_{litter['id']}_{pup['id']}",
                label_visibility="collapsed",
                format_func=sex_option_label,
            )
            cols[2].caption(genotype_summary(pup["id"]))
            assignments.append((pup["id"], sex))

        submitted = st.form_submit_button("Create holding cages and mark split")
        if submitted:
            if not male_label.strip() or not female_label.strip():
                st.error("Both holding cage labels are required.")
                return
            if male_label.strip() == female_label.strip():
                st.error("Male and female holding cages must have different labels.")
                return
            incomplete = [p["ear_tag"] for p, (_, sex) in zip(pups, assignments) if sex == "—"]
            if incomplete:
                st.error("Choose sex for: " + ", ".join(incomplete))
                return

            try:
                db.split_litter(
                    litter["id"],
                    assignments,
                    male_label.strip(),
                    female_label.strip(),
                    str(split_date),
                    weaned_count=len(pups),
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            st.success("Litter split into male/female holding cages.")
            st.rerun()


def _render_cage_mice(cage, show_title=True):
    mice = cage_mice(cage)
    if show_title:
        st.markdown(f"**Mice in this cage ({len(mice)})**")
    if not mice:
        st.caption("No mice assigned to this cage yet.")
        return

    for mouse in mice:
        with st.expander(mouse_display_title(mouse)):
            _mouse_detail_simple(mouse)
            _mark_dead_form(mouse, key_prefix=f"cage_{cage['id']}_{mouse['id']}")


def _mark_dead_form(mouse, key_prefix):
    with st.expander("Mark dead", expanded=False):
        with st.form(f"mark_dead_{key_prefix}"):
            d1, d2 = st.columns([1, 1.35])
            death_date = d1.date_input("Death date", value=date.today(), key=f"death_date_{key_prefix}")
            death_method = d2.selectbox("Death method", DEATH_METHODS, key=f"death_method_{key_prefix}")
            notes = st.text_input("Death notes", key=f"death_notes_{key_prefix}")
            submitted = st.form_submit_button("Mark dead", type="secondary")
            if submitted:
                try:
                    db.mark_mouse_dead(
                        mouse["id"],
                        str(death_date),
                        death_method,
                        notes.strip() or None,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    return
                st.warning(f"Marked {mouse['ear_tag']} as dead.")
                st.rerun()


def _edit_cage_form(cage):
    is_breeding = cage["cage_type"] == "breeding"
    cage_members = cage_mice(cage)
    delete_impact = db.get_cage_delete_impact(cage["id"])
    current_female_ids = [m["id"] for m in db.get_cage_females(cage["id"])]
    current_occupant_ids = [m["id"] for m in cage_members]
    status_options = ["active", "separated", "ended"]
    status_index = status_options.index(cage["status"]) if cage["status"] in status_options else 0

    with st.form(f"edit_cage_{cage['id']}"):
        ec1, ec2, ec3 = st.columns(3)
        new_label = ec1.text_input("Label", value=cage["cage_label"], key=f"cl_{cage['id']}")
        new_status = ec2.selectbox(
            "Status",
            status_options,
            index=status_index,
            key=f"cst_{cage['id']}",
        )
        new_sep = ec3.text_input("Separation Date", value=cage["separation_date"] or "", key=f"sep_{cage['id']}")
        new_notes = st.text_input("Notes", value=cage["notes"] or "", key=f"cno_{cage['id']}")

        if is_breeding:
            st.markdown("**Breeding parents**")
            male_candidates = [
                m for m in cage_members
                if m["sex"] in ("M", "U") or m["id"] == cage["male_id"]
            ]
            female_candidates = [
                m for m in cage_members
                if m["sex"] in ("F", "U") or m["id"] in current_female_ids
            ]
            male_label_to_id, male_id_to_label = mouse_label_maps(male_candidates)
            female_label_to_id, female_id_to_label = mouse_label_maps(female_candidates)
            male_options = ["—"] + list(male_label_to_id.keys())
            default_male_label = male_id_to_label.get(cage["male_id"], "—")
            male_index = male_options.index(default_male_label) if default_male_label in male_options else 0

            pc1, pc2 = st.columns(2)
            selected_male_label = pc1.selectbox(
                "Male",
                male_options,
                index=male_index,
                key=f"edit_male_{cage['id']}",
            )
            new_male_id = male_label_to_id.get(selected_male_label)
            female_options = [
                label for label, mouse_id in female_label_to_id.items()
                if mouse_id != new_male_id
            ]
            default_female_labels = [
                female_id_to_label[mid]
                for mid in current_female_ids
                if mid in female_id_to_label and female_id_to_label[mid] in female_options
            ]
            selected_female_labels = pc2.multiselect(
                "Females",
                female_options,
                default=default_female_labels,
                key=f"edit_females_{cage['id']}",
                placeholder="Choose breeding females...",
            )
            new_female_ids = [female_label_to_id[label] for label in selected_female_labels]
            new_member_ids = ([new_male_id] if new_male_id else []) + new_female_ids
        else:
            st.markdown("**Holding cage mice**")
            occupant_label_to_id, occupant_id_to_label = mouse_label_maps(cage_members)
            default_occupant_labels = [
                occupant_id_to_label[mid]
                for mid in current_occupant_ids
                if mid in occupant_id_to_label
            ]
            selected_occupant_labels = st.multiselect(
                "Mice",
                list(occupant_label_to_id.keys()),
                default=default_occupant_labels,
                key=f"edit_occupants_{cage['id']}",
                placeholder="Choose mice in this holding cage...",
            )
            new_male_id = None
            new_female_ids = []
            selected_member_ids = [occupant_label_to_id[label] for label in selected_occupant_labels]
            new_member_ids = list(dict.fromkeys(selected_member_ids))

        if delete_impact["can_delete"]:
            confirm_delete_cage = st.checkbox(
                "Confirm permanent cage deletion",
                value=False,
                key=f"confirm_delete_cage_{cage['id']}",
            )
        else:
            confirm_delete_cage = False
            st.caption(
                "This cage has current members or history and cannot be permanently deleted. "
                "Use End Cage to preserve its records."
            )

        c1, c2, c3, _ = st.columns([1, 1, 1, 3])
        save = c1.form_submit_button("💾 Save Cage")
        end_cage = c2.form_submit_button("End Cage", type="secondary")
        delete = c3.form_submit_button(
            "🗑️ Delete Cage",
            type="secondary",
            disabled=not delete_impact["can_delete"],
        )
        if save or end_cage:
            clean_label = new_label.strip()
            if not clean_label:
                st.error("Cage label is required.")
                return
            existing_labels = [
                c["cage_label"] for c in db.get_all_breeding_cages()
                if c["id"] != cage["id"]
            ]
            if clean_label in existing_labels:
                st.error(f"Cage '{clean_label}' already exists.")
                return

            assign_mice_to_cage(cage, new_member_ids, cage["cage_type"], clean_label)
            db.update_breeding_cage(
                cage["id"],
                cage_label=clean_label,
                male_id=new_male_id,
                status="ended" if end_cage else new_status,
                separation_date=new_sep.strip() or None,
                notes=new_notes.strip() or None,
            )
            db.set_cage_females(cage["id"], new_female_ids if is_breeding else new_member_ids)
            if end_cage or new_status == "ended":
                db.end_cage(cage["id"], new_sep.strip() or str(date.today()))
                st.success("Cage ended and current mice were released to unassigned holding.")
            else:
                st.success("Updated.")
            st.rerun()
        if delete:
            if not confirm_delete_cage:
                st.error("Check the confirmation box before deleting this cage.")
                return
            try:
                db.delete_cage(cage["id"])
            except ValueError as exc:
                st.error(str(exc))
                return
            st.session_state.selected_cage_id = None
            st.warning(f"Cage '{cage['cage_label']}' deleted.")
            st.rerun()

# ── Settings ───────────────────────────────────────────────────────

def settings_page():
    render_page_header()
    st.subheader("Gene Library")

    custom_genes = set(db.get_custom_genes())
    distinct_genes = set(db.get_distinct_genes())
    all_genes = sorted(custom_genes | distinct_genes, key=str.lower)
    saved_gene_colors = db.get_gene_colors()

    # Count mice per gene
    gene_mouse_counts = {}
    for gene in all_genes:
        mice = db.get_mice_for_gene(gene)
        gene_mouse_counts[gene] = len(mice)

    st.caption(f"{len(all_genes)} genes in library")

    # Add new gene
    with st.form("add_gene_form", clear_on_submit=True):
        used_colors = {gene_color(gene) for gene in all_genes}
        new_gene_default_color = next((color for color in GENE_COLORS if color not in used_colors), "#E4007C")
        c1, c2, c3 = st.columns([3, 1, 1])
        new_gene = c1.text_input("New gene name", placeholder="Type gene name...", key="new_gene_input")
        new_gene_color = c2.color_picker("Color", value=new_gene_default_color, key="new_gene_color")
        if c3.form_submit_button("➕ Add"):
            gene = new_gene.strip()
            if gene and gene not in custom_genes:
                db.add_custom_gene(gene)
                db.set_gene_color(gene, normalize_hex_color(new_gene_color) or default_gene_color(gene))
                st.success(f"Added '{gene}'")
                st.rerun()
            elif gene in custom_genes:
                st.warning(f"'{gene}' already exists.")

    st.divider()

    # Show all genes with delete buttons
    if not all_genes:
        st.info("No genes yet. Add one above.")
        return

    for row_start in range(0, len(all_genes), 2):
        row = all_genes[row_start:row_start + 2]
        cols = st.columns(2)
        for col, gene in zip(cols, row):
            with col:
                count = gene_mouse_counts.get(gene, 0)
                current_color = gene_color(gene)
                default_color = default_gene_color(gene)
                custom_color = normalize_hex_color(saved_gene_colors.get(gene))
                source = "Custom color" if custom_color else "Default color"

                with st.container(border=True):
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:0.55rem;">'
                        f'<span style="width:1.35rem;height:0.55rem;border-radius:999px;'
                        f'background:{current_color};border:1px solid #CBD5E1;display:inline-block;"></span>'
                        f'<span style="font-weight:700;font-size:0.92rem;">{esc(gene)}</span>'
                        f'</div>'
                        f'<div style="color:#64748b;font-size:0.75rem;margin-top:0.2rem;">'
                        f'{count} mice · {source} · default {default_color}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    with st.form(f"gene_color_form_{stable_gene_index(gene)}"):
                        picked_color = st.color_picker(
                            "Gene color",
                            value=current_color,
                            key=f"gene_color_picker_{stable_gene_index(gene)}",
                        )
                        b1, b2 = st.columns(2)
                        save_color = b1.form_submit_button("Save color")
                        reset_color = b2.form_submit_button("Reset")
                        if save_color:
                            db.set_gene_color(gene, normalize_hex_color(picked_color) or current_color)
                            st.success(f"Updated color for '{gene}'.")
                            st.rerun()
                        if reset_color:
                            db.delete_gene_color(gene)
                            st.success(f"Reset color for '{gene}'.")
                            st.rerun()
                    if gene in custom_genes:
                        if st.button("🗑️ Remove gene", key=f"del_gene_{stable_gene_index(gene)}"):
                            db.remove_custom_gene(gene)
                            st.success(f"'{gene}' removed.")
                            st.rerun()

    st.divider()
    st.subheader("💾 Export / 📥 Import Data")

    import io
    import csv as csv_module

    # ── Export ──
    st.caption("Download your data")
    ec1, ec2 = st.columns(2)

    with ec1:
        with open(db.path, "rb") as f:
            db_bytes = f.read()
        st.download_button(
            label="📦 Download Database (.db)",
            data=db_bytes,
            file_name="mouse_colony.db",
            mime="application/octet-stream",
            key="export_db",
        )

    with ec2:
        csv_buf = io.StringIO()
        writer = csv_module.writer(csv_buf)
        mice = db.get_all_mice()
        if mice:
            writer.writerow(["Ear Tag", "Sex", "Birth Date", "Father", "Mother", "Status", "Cage", "Notes", "Genotype"])
            for m in mice:
                geno = genotype_summary(m["id"])
                writer.writerow([
                    m["ear_tag"], m["sex"], m["birth_date"],
                    m["father_tag"] or "", m["mother_tag"] or "",
                    m["status"], m["cage_location"] or "", m["notes"] or "",
                    geno,
                ])
        st.download_button(
            label="📊 Download CSV",
            data=csv_buf.getvalue(),
            file_name="mouse_colony_export.csv",
            mime="text/csv",
            key="export_csv",
        )

    st.divider()
    st.caption("Restore from a previous export")

    # ── Import DB ──
    uploaded_db = st.file_uploader("Upload .db file to restore everything", type=["db"], key="import_db")
    if uploaded_db is not None:
        if st.button("⚠️ Replace current database with uploaded file", key="confirm_db_import"):
            backup_root = os.path.join(
                os.path.expanduser("~"), "mouse-colony-backups", "restores"
            )
            try:
                backup_path = db.restore_from_bytes(
                    uploaded_db.getvalue(), backup_dir=backup_root
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            st.success(
                "Database validated and restored. Previous database backed up to "
                f"{backup_path}."
            )
            st.rerun()

    # ── Import CSV ──
    uploaded_csv = st.file_uploader("Upload .csv file to import mice & cages", type=["csv"], key="import_csv")
    if uploaded_csv is not None:
        csv_text = uploaded_csv.read().decode("utf-8")
        reader = csv_module.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        st.caption(f"{len(rows)} mice found in CSV")
        if st.button(f"📥 Import {len(rows)} mice (cages auto-created)", key="confirm_csv_import"):
            imported_mice = 0
            skipped_mice = 0
            imported_cages = 0
            for row in rows:
                tag = (row.get("Ear Tag") or "").strip()
                if not tag or db.get_mouse_by_tag(tag):
                    skipped_mice += 1
                    continue
                sex = (row.get("Sex") or "U").strip()
                if sex not in ("M", "F", "U"):
                    sex = "U"
                cage_label = (row.get("Cage") or "").strip() or None

                # Auto-create cage if it doesn't exist
                if cage_label and not db.get_cage_by_label(cage_label):
                    status = normalize_mouse_status(row.get("Status", ""))
                    cage_type = "breeding" if status == "breeding" else "holding"
                    db.add_breeding_cage(
                        cage_label=cage_label,
                        cage_type=cage_type,
                        male_id=None,
                        setup_date=str(date.today()),
                    )
                    imported_cages += 1

                mid = db.add_mouse(
                    ear_tag=tag,
                    birth_date=(row.get("Birth Date") or "").strip() or None,
                    sex=sex,
                    father_tag=(row.get("Father") or "").strip() or None,
                    mother_tag=(row.get("Mother") or "").strip() or None,
                    status=normalize_mouse_status(row.get("Status", "")),
                    cage_location=cage_label,
                    notes=(row.get("Notes") or "").strip() or None,
                )

                # Auto-add mouse to cage_females
                if cage_label:
                    cage = db.get_cage_by_label(cage_label)
                    if cage:
                        db.set_cage_females(cage["id"], [mid] + [f["id"] for f in db.get_cage_females(cage["id"])])

                geno_str = (row.get("Genotype") or "").strip()
                if geno_str:
                    for part in geno_str.split(";"):
                        part = part.strip()
                        match = re.match(r"(.+?)\s+(\S+)/(\S+)", part)
                        if match:
                            db.set_genotype(mid, match.group(1).strip(), match.group(2), match.group(3))
                imported_mice += 1
            st.success(f"Imported {imported_mice} mice, {imported_cages} cages. Skipped {skipped_mice} duplicates.")
            st.rerun()

# ── Router ────────────────────────────────────────────────────────

if page == "dashboard":
    dashboard_page()
elif page == "add_import":
    mouse_registry_page()
elif page == "mice":
    view_edit_mice_page()
elif page == "cages":
    cages_page()
elif page == "settings":
    settings_page()
