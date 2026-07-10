# 🐭 Mouse Colony Manager

A Streamlit app for managing mouse colonies: track mice, genotypes, breeding cages, litters, and pedigrees.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
# → http://localhost:8501
```

## First Use

1. **Settings** → add your gene names
2. **Add / Import** → add mice or bulk import
3. **Cages** → create cages and assign mice
4. **Dashboard** → overview

Optional demo data:

```bash
python test_data.py
MOUSE_COLONY_DB=demo_mouse_colony.db streamlit run app.py
```

The demo script refuses to write to the real `mouse_colony.db` unless explicitly overridden.
