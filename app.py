import streamlit as st
from db import DB
from datetime import date, timedelta
import re

st.set_page_config(page_title="Mouse Colony Manager", page_icon="🐭", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; padding-bottom: 0; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; }
    .stTabs [data-baseweb="tab"] { padding: 0.3rem 0.6rem; font-size: 0.9rem; }
    hr { margin: 0.35rem 0; }
    h3 { margin: 0.25rem 0 0.15rem 0; font-size: 1.1rem; }
    .stRadio > div { gap: 0.25rem; flex-wrap: wrap; margin-bottom: 0; }
    .stRadio label { margin: 0; padding: 0.2rem 0.5rem; }
    .stRadio { margin-bottom: -0.5rem; }
    .stMarkdown { margin-bottom: 0; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.25rem; }
    .stButton button { padding: 0.25rem 0.5rem; }
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
}
MOUSE_STATUS_OPTIONS = ["breeding", "holding", "waiting_split"]
MOUSE_STATUS_LABELS = {
    "breeding": "breeding",
    "holding": "holding",
    "waiting_split": "waiting split",
}
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


def mouse_age_label(birth_date, today=None):
    birth = parse_date(birth_date)
    if not birth:
        return "?d"
    days = ((today or date.today()) - birth).days
    return f"{days}d"


def mouse_display_title(mouse):
    geno = genotype_summary(mouse["id"])
    return (
        f"{mouse['ear_tag']}-{mouse_age_label(mouse['birth_date'])}-"
        f"{mouse['sex']}--{geno} - {MOUSE_STATUS_LABELS.get(mouse['status'], mouse['status'])}"
    )


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


def female_tag_list(cage):
    return [t for t in (cage["female_tags"] or "").split(", ") if t]


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


def due_litters(today=None):
    today = today or date.today()
    items = []
    for litter in db.get_all_litters():
        due = litter_due_date(litter)
        if not litter["weaning_date"] and due and due <= today:
            items.append((litter, due))
    return items


def gene_combo_stats():
    from collections import defaultdict

    grouped = defaultdict(list)
    for row in db.get_all_genotypes():
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


def cage_mice(cage):
    is_breeding = cage["cage_type"] == "breeding"
    born_here = db.get_mice_by_birth_cage(cage["id"])

    # Mice assigned via cage_females (works for both breeding and holding cages)
    assigned = []
    if cage["male_tag"]:
        male = db.get_mouse_by_tag(cage["male_tag"])
        if male:
            assigned.append(male)
    for tag in female_tag_list(cage):
        female = db.get_mouse_by_tag(tag)
        if female:
            assigned.append(female)

    # For holding cages, also find by cage_location (backward compat)
    by_location = []
    if not is_breeding:
        by_location = [m for m in db.get_all_mice() if m["cage_location"] == cage["cage_label"]]

    seen = set()
    unique = []
    for mouse in assigned + born_here + by_location:
        if mouse["id"] not in seen:
            seen.add(mouse["id"])
            unique.append(mouse)
    return unique


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
        sym = "♂" if m["sex"] == "M" else "♀" if m["sex"] == "F" else "?"
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
    sym = "♂" if mouse["sex"] == "M" else "♀" if mouse["sex"] == "F" else "?"
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

st.markdown("### 🐭 Mouse Colony Manager")
page = st.radio(
    "Navigation",
    ["📊 Dashboard", "🐭 Mouse Registry", "📋 View / Edit Mice", "🏠 Cages", "⚙️ Settings"],
    horizontal=True,
    label_visibility="collapsed",
    key="main_nav",
)
st.divider()

# ── Dashboard ─────────────────────────────────────────────────────

def dashboard_page():
    stats = db.get_stats()
    split_due = due_litters()
    gene_rows = gene_combo_stats()
    distinct_genes = db.get_distinct_genes()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Mice", stats["total_mice"])
    c2.metric("Gene Types", len(distinct_genes))
    c3.metric("Split Due", len(split_due))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("🧺 Split Reminders")
        if not split_due:
            st.success("No litters are due for splitting today.")
        else:
            today = date.today()
            for litter, due in split_due[:10]:
                days = (today - due).days
                timing = "Due today" if days == 0 else f"Overdue {days}d"
                st.warning(
                    f"**{litter['cage_label']}** — born {litter['birth_date']} — "
                    f"{litter['total_born'] or '?'} born — {timing}"
                )

    with right:
        st.subheader("🐣 Recent Litters")
        litters = db.get_all_litters()
        if not litters:
            st.info("No litters recorded yet.")
        else:
            for l in litters[:10]:
                st.write(
                    f"**{l['cage_label']}** — {l['birth_date']} — "
                    f"{l['total_born']} born, {l['weaned_count'] or 0} weaned"
                )

    st.divider()
    st.subheader("🧬 Gene Type Counts")
    if gene_rows:
        chips_html = '<div style="display:flex; flex-wrap:wrap; gap:6px;">'
        for row in gene_rows:
            chips_html += (
                f'<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px;'
                f'padding:4px 10px; display:flex; align-items:center; gap:6px;">'
                f'<span style="font-weight:600; color:#1e293b; font-size:0.88rem;">{row["Genes"]}</span>'
                f'<span style="background:#3b82f6; color:#fff; border-radius:999px;'
                f'padding:1px 7px; font-size:0.78rem; font-weight:700; min-width:20px; text-align:center;">'
                f'{row["Count"]}</span>'
                f'</div>'
            )
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)
    else:
        st.info("No mice with genotype records yet.")


# ── Mouse Registry ────────────────────────────────────────────────

def mouse_registry_page():

    tab_bulk, tab_add = st.tabs(["📥 Bulk Import", "➕ Add Mouse"])

    with tab_bulk:
        _bulk_import_form()

    with tab_add:
        _add_mouse_form()


def view_edit_mice_page():
    _mouse_list()


def _add_mouse_form(prefill_tag="", prefill_birth=None, prefill_father="", prefill_mother=""):
    with st.form("add_mouse_form", clear_on_submit=True):
        st.subheader("Register New Mouse")
        c1, c2, c3 = st.columns(3)
        ear_tag = c1.text_input("Ear Tag / ID *", value=prefill_tag)
        sex = c2.selectbox("Sex", ["U", "M", "F"])
        birth_date = c3.date_input("Birth Date", value=prefill_birth or date.today())

        c4, c5 = st.columns(2)
        father_tag = c4.text_input("Father Tag (父本)", value=prefill_father)
        mother_tag = c5.text_input("Mother Tag (母本)", value=prefill_mother)

        c6, c7 = st.columns(2)
        status = c6.selectbox(
            "Status",
            MOUSE_STATUS_OPTIONS,
            index=MOUSE_STATUS_OPTIONS.index("holding"),
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


def _bulk_import_form():
    st.subheader("📥 Bulk Import Mice")

    mode = st.radio("Import Mode", ["📊 Table Editor", "📝 Paste from Spreadsheet", "🔢 Generate Sequential Tags"],
                    horizontal=True)

    if mode == "📝 Paste from Spreadsheet":
        st.caption(
            "Paste tab/comma-separated data. One mouse per line. "
            "Format: `EarTag  Sex  BirthDate  FatherTag  MotherTag  Status  Notes`"
        )
        st.caption(
            "Example: `M001\tM\t2025-01-15\tDAD001\tMOM001\twaiting_split\tGeneA fl/fl`"
        )

        data_text = st.text_area(
            "Paste data here",
            height=200,
            placeholder="M001\tM\t2025-01-15\tDAD001\tMOM001\twaiting_split\nM002\tF\t2025-01-15\tDAD001\tMOM001\twaiting_split",
        )

        delimiter = st.radio("Delimiter", ["Tab", "Comma"], horizontal=True)

        col1, col2, _ = st.columns([1, 1, 3])
        add_geno_bulk = col1.checkbox("Add genotypes after import", value=False)
        dry_run = col2.checkbox("Preview only (no save)", value=False)

        bulk_genes = []
        if add_geno_bulk:
            st.caption("Genotypes applied to all imported mice:")
            bulk_genes = compact_genotype_inputs(prefix="bulk_")

        if st.button("Import Mice") and data_text.strip():
            sep = "\t" if delimiter == "Tab" else ","
            lines = [l.strip() for l in data_text.strip().split("\n") if l.strip()]
            imported = 0
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
                        f"{tag} | {sex} | {bd} | ♂{ftag or '?'} | ♀{mtag or '?'} | {status}{geno_preview}"
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

            if dry_run:
                st.info(f"Preview — {len(preview)} mice will be imported:")
                for p in preview:
                    st.write(p)
            else:
                st.success(f"Imported {imported} mice.")
                if errors:
                    st.warning("Warnings: " + "; ".join(errors))
                st.rerun()

    elif mode == "🔢 Generate Sequential Tags":
        st.caption("Generate mice with sequential ear tags sharing the same parents.")

        c1, c2, c3 = st.columns(3)
        prefix = c1.text_input("Tag Prefix", placeholder="e.g. GeneA-GeneB")
        start_num = c2.number_input("Start Number", min_value=1, value=1)
        count = c3.number_input("Count", min_value=1, value=10)

        c4, c5, c6 = st.columns(3)
        seq_sex = c4.selectbox("Sex", ["M", "F", "Mix"])
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
            st.caption("Genotypes applied to all generated mice:")
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
                    st.write(f"{t} | {s} | {seq_birth} | ♂{seq_father or '?'} | ♀{seq_mother or '?'}{geno_str}")
            else:
                created = 0
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
                st.success(f"Created {created} mice ({prefix}-{start_num:03d} ~ {prefix}-{start_num + count - 1:03d}).")
                st.rerun()

    else:  # 📊 Table Editor
        st.caption("Each row is one mouse. Edit Ear Tag / ID directly when mice need different IDs.")

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
        birth_date = r1c1.date_input("Birth Date", value=date.today(), key="te_bd")
        selected_cage_label = r1c2.selectbox("Breeding Cage", ["—"] + cage_labels, key="te_cage_sel")
        tag_prefix = r1c3.text_input("Suggested ID Prefix", key="te_pfx")
        tag_start = r1c4.number_input("Start #", min_value=1, value=1, step=1, key="te_start")

        if selected_cage_label != "—":
            selected_cage = cage_options[selected_cage_label]
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
            father_tag = None
            mother_tag = None
            cage_location = None

        # ── Row count +/− ──
        bc1, bc2, bc3, bc4, bc5 = st.columns([1, 1, 1.6, 1.2, 1.4])
        if bc1.button("➖ Remove", key="te_minus"):
            st.session_state.te_count = max(1, st.session_state.te_count - 1)
            st.rerun()
        if bc2.button("➕ Add", key="te_plus"):
            st.session_state.te_count = min(12, st.session_state.te_count + 1)
            st.rerun()
        count = st.session_state.te_count
        bc3.write(f"**{count} mice**")
        if bc4.button("↻ Fill IDs", key="te_fill_ids"):
            for i in range(count):
                st.session_state[f"te_tag_{i}"] = f"{tag_prefix.strip()}-{int(tag_start) + i:02d}"
            st.rerun()
        if bc5.button("📋 Copy Geno", key="te_copy_geno", help="Copy first row's genotypes to all rows"):
            if count > 1 and genes:
                for gi in range(len(genes)):
                    a1_key = f"te_a1_{gi}_0"
                    a2_key = f"te_a2_{gi}_0"
                    a1_val = st.session_state.get(a1_key, "?")
                    a2_val = st.session_state.get(a2_key, "?")
                    a1_custom = st.session_state.get(f"{a1_key}_custom", "")
                    a2_custom = st.session_state.get(f"{a2_key}_custom", "")
                    for i in range(1, count):
                        st.session_state[f"te_a1_{gi}_{i}"] = a1_val
                        st.session_state[f"te_a2_{gi}_{i}"] = a2_val
                        if a1_custom:
                            st.session_state[f"te_a1_{gi}_{i}_custom"] = a1_custom
                        if a2_custom:
                            st.session_state[f"te_a2_{gi}_{i}_custom"] = a2_custom
            st.rerun()

        if count == 0:
            st.stop()

        # ── Table (rows = mice, cols = attributes) ──
        n_attr_cols = 2 + len(genes)  # Ear tag + Sex + per-gene allele pairs
        hcols = st.columns([1, 2.2, 1.2] + [2] * len(genes))
        hcols[0].caption("")
        hcols[1].caption("Ear Tag / ID")
        hcols[2].caption("Sex")
        for gi, gene in enumerate(genes):
            hcols[3 + gi].caption(gene)

        ear_tags = []
        sexes = []
        gene_alleles = {g: [] for g in genes}
        for i in range(count):
            suggested_tag = f"{tag_prefix.strip()}-{int(tag_start) + i:02d}" if tag_prefix.strip() else ""
            if f"te_tag_{i}" not in st.session_state:
                st.session_state[f"te_tag_{i}"] = suggested_tag

            rcols = st.columns([1, 2.2, 1.2] + [2] * len(genes))
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
                s = st.selectbox("Sex", ["M", "F"], key=f"te_sex_{i}", label_visibility="collapsed")
                sexes.append(s)
            for gi, gene in enumerate(genes):
                with rcols[3 + gi]:
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
                for i in range(count):
                    tag = ear_tags[i]
                    mid = db.add_mouse(
                        ear_tag=tag,
                        birth_date=str(birth_date),
                        sex=sexes[i],
                        father_tag=father_tag,
                        mother_tag=mother_tag,
                        status="waiting_split",
                        cage_location=cage_location or None,
                    )
                    for gene in genes:
                        a1, a2 = gene_alleles[gene][i]
                        db.set_genotype(mid, gene, a1.strip() or "?", a2.strip() or "?")
                    imported += 1
                st.success(f"Imported {imported} mice.")
                st.rerun()


def _mouse_list():
    all_distinct_genes = db.get_distinct_genes()

    cf1, cf2, cf3, cf4 = st.columns(4)
    status_filter = cf1.selectbox(
        "Filter by Status",
        ["All"] + MOUSE_STATUS_OPTIONS,
        format_func=lambda x: "All" if x == "All" else MOUSE_STATUS_LABELS[x],
    )
    search_query = cf2.text_input("Search (tag / notes / location)")
    sex_filter = cf3.selectbox("Filter by Sex", ["All", "M", "F", "U"])
    gene_filter = cf4.multiselect("Filter by Genes (AND)", all_distinct_genes, key="mouse_gene_filter", placeholder="All genes...")

    if search_query:
        mice = db.search_mice(search_query)
    elif status_filter != "All":
        mice = db.get_all_mice(status_filter=status_filter)
    else:
        mice = db.get_all_mice()

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

    st.caption(f"{len(mice)} mice found")

    if "selected_mouse_id" not in st.session_state:
        st.session_state.selected_mouse_id = None

    valid_ids = {m["id"] for m in mice}
    if st.session_state.selected_mouse_id is not None and st.session_state.selected_mouse_id not in valid_ids:
        st.session_state.selected_mouse_id = None

    if not mice:
        st.info("No mice match the current filters.")
        return

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


def _render_mouse_card(mouse):
    selected = st.session_state.get("selected_mouse_id") == mouse["id"]
    geno = genotype_summary(mouse["id"])
    age = mouse_age_label(mouse["birth_date"])
    sym = "♂" if mouse["sex"] == "M" else "♀" if mouse["sex"] == "F" else "?"
    status_label = MOUSE_STATUS_LABELS.get(mouse["status"], mouse["status"])
    status_emoji = STATUS_EMOJI.get(mouse["status"], "")

    sex_color = "#3b82f6" if mouse["sex"] == "M" else "#ec4899" if mouse["sex"] == "F" else "#9ca3af"
    status_color = {
        "breeding": "#3b82f6",
        "holding": "#10b981",
        "waiting_split": "#f59e0b",
    }.get(mouse["status"], "#9ca3af")

    with st.container(border=True):
        # Row 1: sex badge + tag + age
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
            f'<span>'
            f'<span style="display:inline-block;background:{sex_color};color:#fff;border-radius:3px;'
            f'padding:1px 6px;font-size:0.8rem;font-weight:700;margin-right:5px;">{sym}</span>'
            f'<span style="font-weight:700;font-size:1rem;">{mouse["ear_tag"]}</span>'
            f'</span>'
            f'<span style="color:#64748b;font-size:0.85rem;">{age}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        # Row 2: genotype (prominent, bold)
        if geno != "—":
            st.markdown(
                f'<div style="font-size:0.92rem;font-weight:700;color:#0f172a;margin:2px 0;">{geno}</div>',
                unsafe_allow_html=True,
            )
        # Row 3: status chip + edit button
        c1, c2 = st.columns([5, 1])
        c1.markdown(
            f'<span style="display:inline-block;background:{status_color}18;color:{status_color};'
            f'border-radius:3px;padding:1px 6px;font-size:0.78rem;font-weight:600;">'
            f'{status_emoji} {status_label}</span>',
            unsafe_allow_html=True,
        )
        if c2.button(
            "✏️" if not selected else "✖",
            key=f"sel_mouse_{mouse['id']}",
        ):
            st.session_state.selected_mouse_id = None if selected else mouse["id"]
            st.rerun()


def _mouse_genotype_editor(mouse):
    mouse_id = mouse["id"]
    genos = list(db.get_mouse_genotypes(mouse_id))

    st.markdown("**Genotypes**")
    if not genos:
        st.info("No genotypes recorded for this mouse yet.")
    else:
        st.caption(genotype_summary(mouse_id))

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

    st.caption("Add gene to this mouse")
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
    st.markdown(f"**{mouse_display_title(mouse)}**")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Ear Tag:**", mouse["ear_tag"])
        st.write("**Age:**", mouse_age_label(mouse["birth_date"]))
        st.write("**Sex:**", mouse["sex"])
        st.write("**Birth Date:**", mouse["birth_date"] or "?")
        st.write("**Father (父本):**", mouse["father_tag"] or "—")
        st.write("**Mother (母本):**", mouse["mother_tag"] or "—")
    with c2:
        st.write("**Status:**", status_badge(mouse["status"]))
        st.write("**Cage Location:**", mouse["cage_location"] or "?")
        st.write("**Notes:**", mouse["notes"] or "—")

    st.divider()
    _mouse_genotype_editor(mouse)

    with st.expander("📜 Pedigree Tree (up to 3 generations)"):
        tree = render_pedigree(mouse["ear_tag"])
        st.markdown(f"```\n{tree}\n```")

    st.divider()

    # Edit section
    with st.form(f"edit_mouse_{mouse['id']}"):
        st.caption("Edit Mouse")
        ec1, ec2, ec3 = st.columns(3)
        new_tag = ec1.text_input("Ear Tag", value=mouse["ear_tag"], key=f"et_{mouse['id']}")
        new_sex = ec2.selectbox("Sex", ["M", "F", "U"],
                                index=["M", "F", "U"].index(mouse["sex"]),
                                key=f"sx_{mouse['id']}")
        new_status = ec3.selectbox(
            "Status",
            MOUSE_STATUS_OPTIONS,
            index=MOUSE_STATUS_OPTIONS.index(normalize_mouse_status(mouse["status"])),
            format_func=lambda x: MOUSE_STATUS_LABELS[x],
            key=f"st_{mouse['id']}",
        )
        ec4, ec5 = st.columns(2)
        new_birth = ec4.text_input("Birth Date", value=mouse["birth_date"] or "", key=f"bd_{mouse['id']}")
        new_location = ec4.text_input("Cage Location", value=mouse["cage_location"] or "", key=f"cl_{mouse['id']}")
        new_father = ec5.text_input("Father Tag", value=mouse["father_tag"] or "", key=f"ft_{mouse['id']}")
        new_mother = ec5.text_input("Mother Tag", value=mouse["mother_tag"] or "", key=f"mt_{mouse['id']}")
        new_notes = st.text_area("Notes", value=mouse["notes"] or "", key=f"nt_{mouse['id']}")

        btn_col1, btn_col2, _ = st.columns([1, 1, 4])
        save = btn_col1.form_submit_button("💾 Save")
        delete = btn_col2.form_submit_button("🗑️ Delete", type="secondary")

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
            db.delete_mouse(mouse["id"])
            st.warning(f"Deleted mouse '{mouse['ear_tag']}'.")
            st.rerun()


def _mouse_detail_simple(mouse):
    """Compact mouse detail view for cage context (no edit form)."""
    st.markdown(f"**{mouse_display_title(mouse)}**")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Ear Tag:**", mouse["ear_tag"])
        st.write("**Age:**", mouse_age_label(mouse["birth_date"]))
        st.write("**Sex:**", mouse["sex"])
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
    inject_cage_styles()

    tab_cages, tab_add = st.tabs(["📋 View Cages", "➕ New Cage"])

    with tab_add:
        _add_cage_form()

    with tab_cages:
        _cage_list()


def _add_cage_form():
    with st.form("add_cage"):
        st.subheader("Add New Cage")

        cage_type = st.radio("Cage Type", ["breeding", "holding"], horizontal=True,
                             format_func=lambda x: "🔵 Breeding Cage" if x == "breeding" else "🟢 Holding Cage")

        c1, c2 = st.columns(2)
        cage_label = c1.text_input("Cage Label / ID *")
        setup_date = c2.date_input("Setup Date", value=date.today())

        # Get unassigned mice (not already placed in another cage)
        all_mice = db.get_all_mice()
        unassigned = [m for m in all_mice if not (m["cage_location"] or "").strip()]

        if unassigned:
            unassigned_tags = [m["ear_tag"] for m in unassigned]
            st.caption(f"🟢 {len(unassigned)} unassigned mice available")
        else:
            unassigned_tags = []
            st.info("No unassigned mice available. Create mice first or free them from existing cages.")

        selected_mice = st.multiselect(
            "Mice (optional)", unassigned_tags,
            key="mice_sel",
            placeholder="Choose mice for this cage...",
        )

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
                        male_id=None,
                        setup_date=str(setup_date),
                        notes=notes.strip() or None,
                    )
                    mouse_ids = [db.get_mouse_by_tag(t)["id"] for t in selected_mice]
                    if mouse_ids:
                        db.set_cage_females(cage_id, mouse_ids)
                    cage_status = "breeding" if cage_type == "breeding" else "holding"
                    for mouse_id in mouse_ids:
                        db.update_mouse(mouse_id, status=cage_status, cage_location=cage_label.strip())
                    st.success(f"Cage '{cage_label.strip()}' created.")
                    st.rerun()


def _cage_list():
    cf1, cf2, cf3 = st.columns([1, 1, 2])
    status_filter = cf1.selectbox(
        "Filter by status", ["active", "separated", "ended", "All"],
        key="cage_filter",
    )
    type_filter = cf2.selectbox(
        "Filter by type", ["All", "breeding", "holding"],
        key="cage_type_filter",
    )
    search_query = cf3.text_input("Search cage", placeholder="Cage label / parent / notes...")

    cages = db.get_all_breeding_cages(
        status_filter=None if status_filter == "All" else status_filter
    )
    if type_filter != "All":
        cages = [c for c in cages if c["cage_type"] == type_filter]
    if search_query.strip():
        q = search_query.strip().lower()
        cages = [
            c for c in cages
            if q in (c["cage_label"] or "").lower()
            or q in (c["male_tag"] or "").lower()
            or q in (c["female_tags"] or "").lower()
            or q in (c["notes"] or "").lower()
        ]

    split_due_count = len(due_litters())
    if split_due_count:
        st.warning(f"{split_due_count} litter(s) need splitting today or are overdue.")
    else:
        st.success("No litters are due for splitting today.")

    if not cages:
        st.info("No cages match the current filters.")
        return

    if "selected_cage_id" not in st.session_state:
        st.session_state.selected_cage_id = None

    valid_ids = {c["id"] for c in cages}
    if st.session_state.selected_cage_id is not None and st.session_state.selected_cage_id not in valid_ids:
        st.session_state.selected_cage_id = None

    for row_start in range(0, len(cages), 3):
        row = cages[row_start:row_start + 3]
        cols = st.columns(3)
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


def _render_cage_card(cage):
    selected = st.session_state.get("selected_cage_id") == cage["id"]
    is_breeding = cage["cage_type"] == "breeding"
    litters = db.get_litters_for_cage(cage["id"]) if is_breeding else []
    latest_litter = litters[0] if litters else None
    mice = cage_mice(cage)
    type_label = "Breeding" if is_breeding else "Holding"

    with st.container(border=True):
        st.markdown(f"#### {cage['cage_label']}")
        st.markdown(
            f"<div class='cage-meta'>{type_label} · {cage['status']} · {len(mice)} mice</div>",
            unsafe_allow_html=True,
        )

        if is_breeding:
            st.markdown(
                f"<span class='cage-status cage-status-breeding'>Breeding</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='cage-meta'>♂ {cage['male_tag'] or '—'} × ♀ {cage['female_tags'] or '—'}</div>",
                unsafe_allow_html=True,
            )
            if latest_litter:
                tone = litter_split_tone(latest_litter)
                st.markdown(
                    f"<span class='cage-status cage-status-{tone}'>{litter_split_status(latest_litter)}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Latest litter: {latest_litter['birth_date']} · "
                    f"{latest_litter['total_born'] or '?'} born"
                )
            else:
                st.markdown(
                    "<span class='cage-status cage-status-muted'>No litter recorded</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f"<span class='cage-status cage-status-done'>Holding cage</span>",
                unsafe_allow_html=True,
            )
            st.caption(cage["notes"] or "Ready for assigned mice")

        if st.button("Hide details" if selected else "Open details",
                     key=f"select_cage_{cage['id']}",
                     use_container_width=True,
                     type="primary" if selected else "secondary"):
            st.session_state.selected_cage_id = None if selected else cage["id"]
            st.rerun()


def _render_cage_detail(cage):
    is_breeding = cage["cage_type"] == "breeding"
    type_badge = "🔵 Breeding" if is_breeding else "🟢 Holding"

    with st.container(border=True):
        title_col, close_col = st.columns([5, 1])
        title_col.subheader(f"{cage['cage_label']} details")
        if close_col.button("Close details", key=f"close_cage_{cage['id']}", use_container_width=True):
            st.session_state.selected_cage_id = None
            st.rerun()
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Type:** {type_badge}")
        c1.markdown(f"**Setup:** {cage['setup_date'] or '?'}")
        c2.markdown(f"**Status:** {cage['status']}")
        c2.markdown(f"**Separated:** {cage['separation_date'] or '—'}")
        if is_breeding:
            c3.markdown(f"**Male:** {cage['male_tag'] or '—'}")
            c3.markdown(f"**Females:** {cage['female_tags'] or '—'}")
        else:
            c3.markdown(f"**Notes:** {cage['notes'] or '—'}")

        if is_breeding:
            st.divider()
            _record_litter_form(cage)
            st.divider()
            _render_litter_history(cage)

        st.divider()
        _render_cage_mice(cage)

        with st.expander("Edit cage"):
            _edit_cage_form(cage)


def _record_litter_form(cage):
    st.markdown("**Record litter and number pups**")
    females = female_tag_list(cage)
    default_prefix = cage["cage_label"].replace(" ", "-")

    with st.form(f"record_litter_{cage['id']}"):
        r1c1, r1c2, r1c3 = st.columns([1, 1, 1])
        birth = r1c1.date_input("Birth date", value=date.today(), key=f"lit_birth_{cage['id']}")
        total_born = r1c2.number_input("Born", min_value=1, value=1, step=1, key=f"lit_born_{cage['id']}")
        if len(females) > 1:
            mother_tag = r1c3.selectbox("Mother", ["—"] + females, key=f"lit_mother_{cage['id']}")
            mother_tag = None if mother_tag == "—" else mother_tag
        else:
            mother_tag = females[0] if females else None
            r1c3.text_input("Mother", value=mother_tag or "—", disabled=True)

        r2c1, r2c2, r2c3 = st.columns([2, 1, 1])
        tag_prefix = r2c1.text_input("Tag prefix", value=default_prefix, key=f"lit_pfx_{cage['id']}")
        start_number = r2c2.number_input("Start number", min_value=1, value=1, step=1, key=f"lit_start_{cage['id']}")
        sex_mode = r2c3.selectbox(
            "Initial sex",
            ["U", "M", "F", "Alternating"],
            key=f"lit_sex_{cage['id']}",
        )
        notes = st.text_area("Notes", key=f"lit_notes_{cage['id']}")

        preview = generated_pup_tags(tag_prefix, start_number, total_born)
        duplicate_tags = db.find_existing_ear_tags(preview)
        if preview:
            st.caption(f"Preview: {preview_tags(preview)}")
        if duplicate_tags:
            st.warning("Duplicate tags already exist: " + ", ".join(duplicate_tags))

        submitted = st.form_submit_button("Record litter and create pup tags")
        if submitted:
            if not tag_prefix.strip():
                st.error("Tag prefix is required.")
                return
            if duplicate_tags:
                st.error("Fix duplicate tags before creating pups.")
                return

            litter_id = db.add_litter(
                cage_id=cage["id"],
                birth_date=str(birth),
                total_born=int(total_born),
                notes=notes.strip() or None,
            )
            for i, tag in enumerate(preview):
                if sex_mode == "Alternating":
                    sex = "M" if i % 2 == 0 else "F"
                elif sex_mode in ("M", "F"):
                    sex = sex_mode
                else:
                    sex = "U"
                db.add_mouse(
                    ear_tag=tag,
                    birth_date=str(birth),
                    sex=sex,
                    father_tag=cage["male_tag"] or None,
                    mother_tag=mother_tag,
                    birth_cage_id=cage["id"],
                    litter_id=litter_id,
                    status="waiting_split",
                    cage_location=cage["cage_label"],
                    notes=f"From litter #{litter_id}",
                )
            st.success(f"Recorded litter and created {len(preview)} pup tags.")
            st.rerun()


def _render_litter_history(cage):
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
            "Sex": pup["sex"],
            "Cage": pup["cage_location"] or "—",
            "Status": pup["status"],
            "Genotype": genotype_summary(pup["id"]),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


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


def _render_cage_mice(cage):
    mice = cage_mice(cage)
    st.markdown(f"**Mice in this cage ({len(mice)})**")
    if not mice:
        st.caption("No mice assigned to this cage yet.")
        return

    for mouse in mice:
        with st.expander(mouse_display_title(mouse)):
            _mouse_detail_simple(mouse)


def _edit_cage_form(cage):
    with st.form(f"edit_cage_{cage['id']}"):
        ec1, ec2, ec3 = st.columns(3)
        new_label = ec1.text_input("Label", value=cage["cage_label"], key=f"cl_{cage['id']}")
        new_status = ec2.selectbox(
            "Status", ["active", "separated", "ended"],
            index=["active", "separated", "ended"].index(cage["status"]),
            key=f"cst_{cage['id']}",
        )
        new_sep = ec3.text_input("Separation Date", value=cage["separation_date"] or "", key=f"sep_{cage['id']}")
        new_notes = st.text_input("Notes", value=cage["notes"] or "", key=f"cno_{cage['id']}")
        if st.form_submit_button("💾 Save Cage"):
            db.update_breeding_cage(
                cage["id"],
                cage_label=new_label.strip(),
                status=new_status,
                separation_date=new_sep.strip() or None,
                notes=new_notes.strip() or None,
            )
            st.success("Updated.")
            st.rerun()

# ── Settings ───────────────────────────────────────────────────────

def _load_demo_data():
    """Populate the database with sample mice, cages, and litters."""
    stats = db.get_stats()
    if stats["total_mice"] > 0:
        return  # already has data, don't duplicate

    # Founder mice
    m1 = db.add_mouse("F-M001", "2024-06-01", "M", status="breeding", cage_location="Founder")
    db.set_genotype(m1, "GeneA", "fl", "fl")
    db.set_genotype(m1, "GeneB", "Tg", "0")

    m2 = db.add_mouse("F-F001", "2024-06-15", "F", status="breeding", cage_location="Founder")
    db.set_genotype(m2, "GeneA", "fl", "fl")

    m3 = db.add_mouse("F-M002", "2024-07-01", "M", status="breeding", cage_location="Founder")
    db.set_genotype(m3, "GeneA", "fl", "+")
    db.set_genotype(m3, "GeneC", "Tg", "0")

    m4 = db.add_mouse("F-F002", "2024-07-15", "F", status="breeding", cage_location="Founder")
    db.set_genotype(m4, "GeneA", "fl", "fl")

    # Cages
    cage1 = db.add_breeding_cage("Breed-01", "breeding", m1, "2025-01-15", "First breeding pair")
    db.set_cage_females(cage1, [m2])
    db.update_mouse(m1, status="breeding", cage_location="Breed-01")
    db.update_mouse(m2, status="breeding", cage_location="Breed-01")

    cage2 = db.add_breeding_cage("Breed-02", "breeding", m3, "2025-01-20", "Second breeding pair")
    db.set_cage_females(cage2, [m4])
    db.update_mouse(m3, status="breeding", cage_location="Breed-02")
    db.update_mouse(m4, status="breeding", cage_location="Breed-02")

    hc1 = db.add_breeding_cage("Hold-01", "holding", None, "2025-03-01", "Weaned pups awaiting genotyping")
    hc2 = db.add_breeding_cage("Hold-02", "holding", None, "2025-03-15", "Genotyped mice ready for experiments")

    # Litters
    l1 = db.add_litter(cage1, "2025-02-05", 8, weaned_count=6, weaning_date="2025-02-26")
    l2 = db.add_litter(cage2, "2025-02-10", 6, weaned_count=5, weaning_date="2025-03-03")
    l3 = db.add_litter(cage1, "2025-03-15", 7)

    # Pups from litter 1
    for i, (tag, sex) in enumerate([
        ("B1-M1", "M"), ("B1-M2", "M"), ("B1-M3", "M"),
        ("B1-F1", "F"), ("B1-F2", "F"), ("B1-F3", "F"),
    ]):
        mid = db.add_mouse(tag, "2025-02-05", sex, father_tag="F-M001", mother_tag="F-F001",
                           birth_cage_id=cage1, litter_id=l1, status="holding", cage_location="Hold-01")
        db.set_genotype(mid, "GeneA", "fl", "fl")
        if sex == "F":
            db.set_genotype(mid, "GeneB", "Tg", "0")

    # Pups from litter 2
    for i, (tag, sex) in enumerate([
        ("B2-M1", "M"), ("B2-M2", "M"), ("B2-M3", "M"),
        ("B2-F1", "F"), ("B2-F2", "F"),
    ]):
        mid = db.add_mouse(tag, "2025-02-10", sex, father_tag="F-M002", mother_tag="F-F002",
                           birth_cage_id=cage2, litter_id=l2, status="holding", cage_location="Hold-01")
        db.set_genotype(mid, "GeneA", "fl", "fl")
        db.set_genotype(mid, "GeneC", "Tg", "0")

    # Pups from litter 3 (pending split)
    for i, (tag, sex) in enumerate([
        ("B1-M4", "M"), ("B1-M5", "M"), ("B1-M6", "M"), ("B1-M7", "M"),
        ("B1-F4", "F"), ("B1-F5", "F"), ("B1-F6", "F"),
    ]):
        mid = db.add_mouse(tag, "2025-03-15", sex, father_tag="F-M001", mother_tag="F-F001",
                           birth_cage_id=cage1, litter_id=l3, status="waiting_split", cage_location="Breed-01")
        db.set_genotype(mid, "GeneA", "fl", "fl")
        if sex == "F":
            db.set_genotype(mid, "GeneB", "Tg", "0")

    # Custom genes for the demo
    for gene in ["GeneA", "GeneB", "GeneC"]:
        db.add_custom_gene(gene)


def settings_page():
    st.subheader("🧬 Manage Gene Library")

    # Collect all genes from all sources
    custom_genes = set(db.get_custom_genes())
    db_genes = set(db.get_distinct_genes())
    all_genes = sorted(custom_genes | db_genes)

    # Count mice per gene
    gene_mouse_counts = {}
    for gene in all_genes:
        mice = db.get_mice_for_gene(gene)
        gene_mouse_counts[gene] = len(mice)

    st.caption(f"{len(all_genes)} genes in library")

    # Add new gene
    with st.form("add_gene_form", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        new_gene = c1.text_input("New gene name", placeholder="Type gene name...", key="new_gene_input")
        if c2.form_submit_button("➕ Add"):
            gene = new_gene.strip()
            if gene and gene not in custom_genes:
                db.add_custom_gene(gene)
                st.success(f"Added '{gene}'")
                st.rerun()
            elif gene in custom_genes:
                st.warning(f"'{gene}' already exists.")

    st.divider()

    # Show all genes with delete buttons
    if not all_genes:
        st.info("No genes yet. Add one above.")
        return

    for row_start in range(0, len(all_genes), 3):
        row = all_genes[row_start:row_start + 3]
        cols = st.columns(3)
        for col, gene in zip(cols, row):
            with col:
                count = gene_mouse_counts.get(gene, 0)
                is_custom = gene in custom_genes
                in_use = gene in db_genes

                tag = "in use" if in_use else "custom" if is_custom else ""

                with st.container(border=True):
                    st.markdown(
                        f'<div style="font-weight:700;font-size:0.92rem;">{gene}</div>'
                        f'<div style="color:#64748b;font-size:0.75rem;">{tag} · {count} mice</div>',
                        unsafe_allow_html=True,
                    )

                    if is_custom:
                        if st.button("🗑️", key=f"del_gene_{gene}"):
                            db.remove_custom_gene(gene)
                            if in_use:
                                st.warning(f"'{gene}' removed from library (still used by {count} mice).")
                            else:
                                st.success(f"'{gene}' removed.")
                            st.rerun()
                    elif in_use:
                        st.caption("from records")

    st.divider()
    st.subheader("🧪 Demo Data")

    st.caption("Load sample mice, cages, and litters to explore the app.")
    if st.button("📥 Load Demo Data", key="load_demo"):
        _load_demo_data()
        st.success("Demo data loaded! Check the Dashboard and other pages.")
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
    uploaded_db = st.file_uploader("Upload .db file to restore", type=["db"], key="import_db")
    if uploaded_db is not None:
        if st.button("⚠️ Replace current database with uploaded file", key="confirm_db_import"):
            with open(db.path, "wb") as f:
                f.write(uploaded_db.read())
            st.success("Database replaced. Refreshing...")
            st.rerun()

    # ── Import CSV ──
    uploaded_csv = st.file_uploader("Upload .csv file to import mice", type=["csv"], key="import_csv")
    if uploaded_csv is not None:
        csv_text = uploaded_csv.read().decode("utf-8")
        reader = csv_module.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        st.caption(f"{len(rows)} mice found in CSV")
        if st.button(f"📥 Import {len(rows)} mice from CSV", key="confirm_csv_import"):
            imported = 0
            skipped = 0
            for row in rows:
                tag = (row.get("Ear Tag") or "").strip()
                if not tag or db.get_mouse_by_tag(tag):
                    skipped += 1
                    continue
                sex = (row.get("Sex") or "U").strip()
                if sex not in ("M", "F", "U"):
                    sex = "U"
                mid = db.add_mouse(
                    ear_tag=tag,
                    birth_date=(row.get("Birth Date") or "").strip() or None,
                    sex=sex,
                    father_tag=(row.get("Father") or "").strip() or None,
                    mother_tag=(row.get("Mother") or "").strip() or None,
                    status=normalize_mouse_status(row.get("Status", "")),
                    cage_location=(row.get("Cage") or "").strip() or None,
                    notes=(row.get("Notes") or "").strip() or None,
                )
                # Parse genotype
                geno_str = (row.get("Genotype") or "").strip()
                if geno_str:
                    for part in geno_str.split(";"):
                        part = part.strip()
                        match = re.match(r"(.+?)\s+(\S+)/(\S+)", part)
                        if match:
                            db.set_genotype(mid, match.group(1).strip(), match.group(2), match.group(3))
                imported += 1
            st.success(f"Imported {imported} mice. Skipped {skipped} duplicates.")
            st.rerun()

# ── Router ────────────────────────────────────────────────────────

if page == "📊 Dashboard":
    dashboard_page()
elif page == "🐭 Mouse Registry":
    mouse_registry_page()
elif page == "📋 View / Edit Mice":
    view_edit_mice_page()
elif page == "🏠 Cages":
    cages_page()
elif page == "⚙️ Settings":
    settings_page()
