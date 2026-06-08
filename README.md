# 🐭 Mouse Colony Manager

A Streamlit app for managing mouse colonies: track mice, genotypes, breeding cages, litters, and pedigrees.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/farebinetlin/mouse-colony-manager.git
cd mouse-colony-manager

# 2. Install
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

## First Use

1. Go to **⚙️ Settings** → add your gene names (one per line, e.g. `GeneA`, `GeneB`)
2. Go to **🐭 Mouse Registry** → add mice or bulk import
3. Go to **🏠 Cages** → create cages and assign mice
4. Check **📊 Dashboard** for an overview

## Optional: Load Demo Data

```bash
python test_data.py
```

This populates the app with sample mice, cages, and litters so you can explore the features.
