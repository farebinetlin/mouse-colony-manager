import streamlit as st
from db import DB
from datetime import date, timedelta

st.set_page_config(page_title="Mouse Colony Manager", page_icon="🐭", layout="wide")

db = DB()

# ── Helpers ───────────────────────────────────────────────────────

STATUS_EMOJI = {
    "active": "🟢", "breeding": "🔵", "genotyping": "🟡",
    "assigned": "🟠", "sacrificed": "⚫", "dead": "⚫",
}
COMMON_GENES = [
    "pdgfrβ-Cre", "Cdh5-CreER", "CAG-CreER",
    "Lamp1", "Pex3c", "Pex26d",
    "Ng2-DsRed", "Ai14",
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
        genes = COMMON_GENES
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


def zygosity(a1, a2):
    if a1 == "?" or a2 == "?":
        return "?"
    if a1 == a2:
        return "Homo"
    return "Het"


def status_badge(status):
    emoji = STATUS_EMOJI.get(status, "")
    return f"{emoji} {status}"


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


# ── Sidebar ───────────────────────────────────────────────────────

st.sidebar.title("🐭 Mouse Colony Manager")
page = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "🐭 Mouse Registry", "🧬 Genotypes",
     "🏠 Cages", "⚠️ Alerts"],
)

# ── Dashboard ─────────────────────────────────────────────────────

def dashboard_page():
    st.title("📊 Dashboard")
    stats = db.get_stats()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Mice", stats["total_mice"])
    c2.metric("Active Breeders", stats["active_breeders"])
    c3.metric("Awaiting Genotyping", stats["pending_genotyping"])
    c4.metric("Unknown Alleles", stats["unknown_genotypes"])
    c5.metric("Pending Alerts", stats["pending_alerts"])

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("⚠️ Pending Alerts")
        alerts = db.get_pending_alerts()
        if not alerts:
            st.success("No pending alerts.")
        else:
            for a in alerts[:10]:
                tag = a["ear_tag"] or f"Mouse #{a['mouse_id']}"
                st.warning(f"**{a['alert_type']}** — {tag} — due {a['due_date'] or '?'}")

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


# ── Mouse Registry ────────────────────────────────────────────────

def mouse_registry_page():
    st.title("🐭 Mouse Registry")

    tab_bulk, tab_add, tab_list = st.tabs(["📥 Bulk Import", "➕ Add Mouse", "📋 View / Edit Mice"])

    with tab_bulk:
        _bulk_import_form()

    with tab_add:
        _add_mouse_form()

    with tab_list:
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
            ["active", "breeding", "genotyping", "assigned", "sacrificed", "dead"],
            index=2,
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
            "Example: `M001\tM\t2025-01-15\tDAD001\tMOM001\tgenotyping\tQars fl/fl`"
        )

        data_text = st.text_area(
            "Paste data here",
            height=200,
            placeholder="M001\tM\t2025-01-15\tDAD001\tMOM001\tgenotyping\nM002\tF\t2025-01-15\tDAD001\tMOM001\tgenotyping",
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
                status = parts[5] if len(parts) > 5 else "genotyping"
                notes = parts[6] if len(parts) > 6 else None

                if sex not in ("M", "F", "U"):
                    errors.append(f"Invalid sex '{sex}' for {tag}, using U")
                    sex = "U"
                if status not in ("active", "breeding", "genotyping", "assigned", "sacrificed", "dead"):
                    status = "genotyping"

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
        prefix = c1.text_input("Tag Prefix", placeholder="e.g. Vglut1-Qars")
        start_num = c2.number_input("Start Number", min_value=1, value=1)
        count = c3.number_input("Count", min_value=1, value=10)

        c4, c5, c6 = st.columns(3)
        seq_sex = c4.selectbox("Sex", ["M", "F", "Mix"])
        seq_birth = c5.date_input("Birth Date", value=date.today())
        seq_status = c6.selectbox(
            "Status", ["genotyping", "active", "breeding", "assigned", "sacrificed", "dead"],
            index=0,
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
        st.caption("Each row is one mouse. Shared attributes apply to all.")

        # ── Shared attributes ──
        all_cages = db.get_all_breeding_cages(status_filter="active")
        cage_options = {f"{c['cage_label']} (♂{c['male_tag'] or '?'})": c for c in all_cages if c["cage_type"] == "breeding"}
        cage_labels = list(cage_options.keys())

        r1c1, r1c2, r1c3 = st.columns(3)
        birth_date = r1c1.date_input("Birth Date", value=date.today(), key="te_bd")
        selected_cage_label = r1c2.selectbox("Breeding Cage", ["—"] + cage_labels, key="te_cage_sel")
        tag_prefix = r1c3.text_input("Tag Prefix", value="M", key="te_pfx")

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

        # ── Genes selection ──
        genes = st.multiselect("Genes (max 3)", COMMON_GENES, default=COMMON_GENES[:2], key="te_genes")
        if len(genes) > 3:
            genes = genes[:3]

        # ── Row count +/− ──
        if "te_count" not in st.session_state:
            st.session_state.te_count = 4

        bc1, bc2, bc3, _ = st.columns([1, 1, 2, 4])
        if bc1.button("➖ Remove", key="te_minus"):
            st.session_state.te_count = max(1, st.session_state.te_count - 1)
            st.rerun()
        if bc2.button("➕ Add", key="te_plus"):
            st.session_state.te_count = min(12, st.session_state.te_count + 1)
            st.rerun()
        count = st.session_state.te_count
        bc3.write(f"**{count} mice**")

        if count == 0:
            st.stop()

        # ── Table (rows = mice, cols = attributes) ──
        n_attr_cols = 1 + len(genes)  # Sex + per-gene allele pairs
        hcols = st.columns([1] + [2] * n_attr_cols)
        hcols[0].caption("")
        hcols[1].caption("Sex")
        for gi, gene in enumerate(genes):
            hcols[2 + gi].caption(gene)

        sexes = []
        gene_alleles = {g: [] for g in genes}
        for i in range(count):
            rcols = st.columns([1] + [2] * n_attr_cols)
            rcols[0].caption(f"#{i+1}")
            with rcols[1]:
                s = st.selectbox("Sex", ["M", "F"], key=f"te_sex_{i}", label_visibility="collapsed")
                sexes.append(s)
            for gi, gene in enumerate(genes):
                with rcols[2 + gi]:
                    aac1, aac2 = st.columns(2)
                    with aac1:
                        a1 = allele_input("A1", key=f"te_a1_{gi}_{i}", compact=True)
                    with aac2:
                        a2 = allele_input("A2", key=f"te_a2_{gi}_{i}", compact=True)
                    gene_alleles[gene].append((a1, a2))

        # ── Submit ──
        if st.button("📥 Import Mice", key="te_import"):
            if not tag_prefix.strip():
                st.error("Tag prefix is required.")
            else:
                imported = 0
                for i in range(count):
                    tag = f"{tag_prefix.strip()}-{i+1:02d}"
                    if db.get_mouse_by_tag(tag):
                        continue
                    mid = db.add_mouse(
                        ear_tag=tag,
                        birth_date=str(birth_date),
                        sex=sexes[i],
                        father_tag=father_tag,
                        mother_tag=mother_tag,
                        status="genotyping",
                        cage_location=cage_location or None,
                    )
                    for gene in genes:
                        a1, a2 = gene_alleles[gene][i]
                        db.set_genotype(mid, gene, a1.strip() or "?", a2.strip() or "?")
                    imported += 1
                st.success(f"Imported {imported} mice.")
                st.rerun()


def _mouse_list():
    st.subheader("Mouse Registry")

    all_distinct_genes = db.get_distinct_genes()

    cf1, cf2, cf3, cf4 = st.columns(4)
    status_filter = cf1.selectbox(
        "Filter by Status",
        ["All", "active", "breeding", "genotyping", "assigned", "sacrificed", "dead"],
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

    for mouse in mice:
        geno = genotype_summary(mouse["id"])
        parents = f"♂{mouse['father_tag'] or '?'}×♀{mouse['mother_tag'] or '?'}"
        with st.expander(
            f"{status_badge(mouse['status'])} **{mouse['ear_tag']}** — "
            f"{mouse['sex']} — {parents} — {geno[:50]}{'...' if len(geno) > 50 else ''}"
        ):
            _mouse_detail(mouse)


def _mouse_detail(mouse):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Ear Tag:**", mouse["ear_tag"])
        st.write("**Sex:**", mouse["sex"])
        st.write("**Birth Date:**", mouse["birth_date"] or "?")
        st.write("**Father (父本):**", mouse["father_tag"] or "—")
        st.write("**Mother (母本):**", mouse["mother_tag"] or "—")
    with c2:
        st.write("**Status:**", status_badge(mouse["status"]))
        st.write("**Cage Location:**", mouse["cage_location"] or "?")
        st.write("**Notes:**", mouse["notes"] or "—")

    st.divider()
    st.write("**Genotypes:**", genotype_summary(mouse["id"]))

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
            ["active", "breeding", "genotyping", "assigned", "sacrificed", "dead"],
            index=["active", "breeding", "genotyping", "assigned", "sacrificed", "dead"].index(mouse["status"]),
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
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Ear Tag:**", mouse["ear_tag"])
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


# ── Genotypes ─────────────────────────────────────────────────────

def genotypes_page():
    st.title("🧬 Genotype Management")

    all_geno = db.get_all_genotypes()
    all_genes = db.get_distinct_genes()

    left, right = st.columns([1, 2])

    with left:
        if all_genes:
            st.metric("Distinct Genes", len(all_genes))
            st.metric("Mice with Genotypes", len({r["mouse_id"] for r in all_geno}))

        st.divider()
        st.subheader("🔍 Filter by Gene")
        filter_gene = st.multiselect(
            "Mice must have ALL selected genes",
            all_genes,
            key="geno_filter",
            placeholder="Choose genes (AND)...",
        )
        if filter_gene:
            st.caption("Showing only mice that have **all** selected genes.")

    with right:
        st.subheader("📋 All Genotypes")

        if not all_geno:
            st.info("No genotype data yet. Register mice with genotypes in **Mouse Registry**, or use **➕ Add gene** inside any mouse expander below.")
            return

        from collections import defaultdict

        # Group by mouse first
        full_grouped = defaultdict(list)
        for r in all_geno:
            full_grouped[r["mouse_id"]].append(r)

        # Apply AND filter: mouse must have ALL selected genes
        if filter_gene:
            filter_set = set(filter_gene)
            grouped = {}
            for mid, genos in full_grouped.items():
                mouse_genes = {g["gene"] for g in genos}
                if filter_set <= mouse_genes:  # subset check
                    grouped[mid] = genos
        else:
            grouped = full_grouped

        st.caption(f"{len(grouped)} mice shown")

        for mid, genos in list(grouped.items()):
            tag = genos[0]["ear_tag"]
            sex = genos[0]["sex"]
            g_parts = [f"{g['gene']} {g['allele1']}/{g['allele2']}" for g in genos]
            g_summary = "; ".join(g_parts)

            with st.expander(
                f"**{tag}** ({sex}) {status_badge(genos[0]['status'])} — {g_summary[:60]}{'...' if len(g_summary) > 60 else ''}"
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Ear Tag:**", genos[0]["ear_tag"])
                    st.write("**Sex:**", sex)
                    st.write("**Birth:**", genos[0]["birth_date"] or "?")
                    st.write("**Parents:**", f"♂{genos[0]['father_tag'] or '?'} × ♀{genos[0]['mother_tag'] or '?'}")
                with c2:
                    st.write("**Status:**", status_badge(genos[0]["status"]))
                    st.write("**Cage:**", genos[0]["cage_location"] or "?")
                    st.write("**Notes:**", genos[0]["notes"] or "—")

                st.divider()
                st.write("**Genotypes:**")
                for g in genos:
                    gc1, gc2, gc3, gc4 = st.columns([2, 2, 1, 1])
                    gc1.write(f"**{g['gene']}**")
                    gc2.write(f"{g['allele1']} / {g['allele2']}")
                    gc3.write(zygosity(g['allele1'], g['allele2']))

                    # Quick allele edit per gene
                    with gc4.popover("✏️"):
                        with st.form(f"qedit_{g['id']}"):
                            na1 = allele_input("Allele 1", key=f"na1_{g['id']}", default=g["allele1"])
                            na2 = allele_input("Allele 2", key=f"na2_{g['id']}", default=g["allele2"])
                            if st.form_submit_button("Save"):
                                db.set_genotype(g["mouse_id"], g["gene"], na1.strip() or "?", na2.strip() or "?")
                                st.rerun()

                    if gc4.button("🗑️", key=f"popdel_{g['id']}"):
                        db.delete_genotype(g["id"])
                        st.rerun()

                # Add another gene to this mouse
                with st.expander("➕ Add gene to this mouse"):
                    existing_genes = {g["gene"] for g in genos}
                    available = [g for g in (all_genes + COMMON_GENES) if g not in existing_genes]
                    if not available:
                        st.caption("All known genes already assigned.")
                    else:
                        with st.form(f"addgene_{mid}"):
                            ng = st.selectbox("Gene", available, key=f"addg_{mid}")
                            na1 = allele_input("Allele 1", key=f"addga1_{mid}")
                            na2 = allele_input("Allele 2", key=f"addga2_{mid}")
                            if st.form_submit_button("Add"):
                                db.set_genotype(mid, ng, na1.strip() or "?", na2.strip() or "?")
                                st.rerun()


# ── Breeding Cages ────────────────────────────────────────────────

def cages_page():
    st.title("🏠 Cages")

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

        mice = db.get_all_mice()
        mouse_tags = ["—"] + [m["ear_tag"] for m in mice]

        if cage_type == "breeding":
            male_tag = st.selectbox("Male", mouse_tags, key="male_sel")
            female_tags = st.multiselect(
                "Females (up to 4)", mouse_tags[1:],  # exclude "—"
                key="female_sel",
                placeholder="Choose 1-4 females...",
            )
            if len(female_tags) > 4:
                st.error("Maximum 4 females allowed.")
        else:
            male_tag = "—"
            female_tags = []
            st.caption("Holding cage — no breeding pair assigned. Use 'Cage Location' on each mouse to assign them to this cage.")

        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Create Cage")
        if submitted:
            if not cage_label.strip():
                st.error("Cage label is required.")
            elif cage_type == "breeding" and not female_tags:
                st.error("At least one female is required for a breeding cage.")
            elif len(female_tags) > 4:
                st.error("Maximum 4 females allowed.")
            else:
                existing = db.get_all_breeding_cages()
                if any(c["cage_label"] == cage_label.strip() for c in existing):
                    st.error(f"Cage '{cage_label.strip()}' already exists.")
                else:
                    male_id = db.get_mouse_by_tag(male_tag)["id"] if male_tag != "—" else None
                    cage_id = db.add_breeding_cage(
                        cage_label=cage_label.strip(),
                        cage_type=cage_type,
                        male_id=male_id,
                        setup_date=str(setup_date),
                        notes=notes.strip() or None,
                    )
                    female_ids = [db.get_mouse_by_tag(t)["id"] for t in female_tags if t != "—"]
                    if female_ids:
                        db.set_cage_females(cage_id, female_ids)
                    st.success(f"Cage '{cage_label.strip()}' created.")
                    st.rerun()


def _cage_list():
    cf1, cf2 = st.columns(2)
    status_filter = cf1.selectbox(
        "Filter by status", ["active", "separated", "ended", "All"],
        key="cage_filter",
    )
    type_filter = cf2.selectbox(
        "Filter by type", ["All", "breeding", "holding"],
        key="cage_type_filter",
    )
    cages = db.get_all_breeding_cages(
        status_filter=None if status_filter == "All" else status_filter
    )
    if type_filter != "All":
        cages = [c for c in cages if c["cage_type"] == type_filter]

    for cage in cages:
        is_breeding = cage["cage_type"] == "breeding"
        type_badge = "🔵 Breeding" if is_breeding else "🟢 Holding"
        cage_mice = db.get_mice_by_birth_cage(cage["id"])

        # Collect assigned parents
        parents = []
        if is_breeding:
            if cage["male_tag"]:
                m = db.get_mouse_by_tag(cage["male_tag"])
                if m:
                    parents.append(m)
            female_tags = (cage["female_tags"] or "").split(", ")
            for ft in female_tags:
                if ft:
                    f = db.get_mouse_by_tag(ft)
                    if f:
                        parents.append(f)

        holding_mice = []
        if not is_breeding:
            holding_mice = [m for m in db.get_all_mice() if m["cage_location"] == cage["cage_label"]]
        all_cage_mice = parents + cage_mice + holding_mice
        # Deduplicate (a mouse could be both born here and a parent)
        seen = set()
        all_cage_mice_dedup = []
        for m in all_cage_mice:
            if m["id"] not in seen:
                seen.add(m["id"])
                all_cage_mice_dedup.append(m)
        all_cage_mice = all_cage_mice_dedup
        total_mice = len(all_cage_mice)

        if is_breeding:
            female_str = cage['female_tags'] or '?'
            title = (
                f"{type_badge} **{cage['cage_label']}** — "
                f"♂ {cage['male_tag'] or '?'} × ♀ {{{female_str}}} — "
                f"{cage['status']} — {total_mice} mice"
            )
        else:
            title = (
                f"{type_badge} **{cage['cage_label']}** — "
                f"{cage['status']} — {total_mice} mice"
            )

        with st.expander(title):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Type:** {type_badge}")
            c1.markdown(f"**Setup:** {cage['setup_date'] or '?'}")
            if is_breeding:
                c2.markdown(f"**Male:** {cage['male_tag'] or '—'}")
                c2.markdown(f"**Females:** {cage['female_tags'] or '—'}")
            c2.markdown(f"**Separated:** {cage['separation_date'] or '—'}")
            c3.markdown(f"**Status:** {cage['status']}")
            c3.markdown(f"**Notes:** {cage['notes'] or '—'}")

            # Edit cage
            with st.form(f"edit_cage_{cage['id']}"):
                st.caption("Edit Cage")
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

            # ── Mice in this cage ──
            st.divider()
            st.write(f"**🐭 Mice in This Cage ({len(all_cage_mice)}):**")
            if not all_cage_mice:
                st.caption("No mice assigned to this cage yet.")
            else:
                hdr_a, hdr_b, hdr_c, hdr_d, hdr_e = st.columns([2, 1, 1, 3, 1])
                hdr_a.caption("**Tag**")
                hdr_b.caption("**Sex**")
                hdr_c.caption("**Birth**")
                hdr_d.caption("**Genotype**")
                hdr_e.caption("**Status**")
                for cm in all_cage_mice:
                    cm_geno = genotype_summary(cm["id"])
                    parents = f"♂{cm['father_tag'] or '?'}×♀{cm['mother_tag'] or '?'}"
                    with st.expander(
                        f"{status_badge(cm['status'])} **{cm['ear_tag']}** — "
                        f"{cm['sex']} — {parents} — "
                        f"{cm_geno[:40]}{'...' if len(cm_geno) > 40 else ''}"
                    ):
                        _mouse_detail_simple(cm)


# ── Alerts ────────────────────────────────────────────────────────

def alerts_page():
    st.title("⚠️ Alerts")

    left, right = st.columns([1, 2])

    with left:
        st.subheader("Create Alert")
        with st.form("add_alert"):
            mice = db.get_all_mice()
            mouse_opts = {m["ear_tag"]: m["id"] for m in mice}
            alert_mouse = st.selectbox("Mouse (optional)", ["—"] + list(mouse_opts.keys()))
            alert_type = st.selectbox(
                "Type",
                ["Weaning Due", "Genotyping Due", "Cage Check", "Sacrifice", "Other"],
            )
            alert_date = st.date_input("Due Date", value=date.today())
            alert_notes = st.text_area("Notes")
            if st.form_submit_button("Create Alert"):
                mid = mouse_opts.get(alert_mouse) if alert_mouse != "—" else None
                db.add_alert(
                    mouse_id=mid,
                    alert_type=alert_type,
                    due_date=str(alert_date),
                    notes=alert_notes.strip() or None,
                )
                st.success("Alert created.")
                st.rerun()

    with right:
        st.subheader("All Alerts")
        alerts = db.get_all_alerts()
        if not alerts:
            st.info("No alerts.")
            return

        for a in alerts:
            resolved = "✅" if a["resolved"] else "⚠️"
            tag = a["ear_tag"] or "—"
            st.write(
                f"{resolved} **{a['alert_type']}** — "
                f"{tag} — due {a['due_date'] or '?'} — {a['notes'] or ''}"
            )
            if not a["resolved"]:
                if st.button("Mark Resolved", key=f"res_{a['id']}"):
                    db.resolve_alert(a["id"])
                    st.rerun()


# ── Router ────────────────────────────────────────────────────────

if page == "📊 Dashboard":
    dashboard_page()
elif page == "🐭 Mouse Registry":
    mouse_registry_page()
elif page == "🧬 Genotypes":
    genotypes_page()
elif page == "🏠 Cages":
    cages_page()
elif page == "⚠️ Alerts":
    alerts_page()
