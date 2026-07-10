import pandas as pd
from lifelines import KaplanMeierFitter


def kaplan_meier_points(durations, events):
    """Return a finite Kaplan-Meier survival table for chart rendering."""
    if len(durations) != len(events):
        raise ValueError("Durations and events must have the same length.")
    if not durations:
        return pd.DataFrame(columns=["Day", "Survival (%)"])

    clean_durations = [max(0, int(value)) for value in durations]
    clean_events = [bool(value) for value in events]
    fitter = KaplanMeierFitter()
    fitter.fit(clean_durations, event_observed=clean_events)

    survival = fitter.survival_function_.reset_index()
    survival.columns = ["Day", "Survival"]
    survival["Day"] = survival["Day"].astype(float)
    survival["Survival (%)"] = survival["Survival"].astype(float) * 100.0
    return survival[["Day", "Survival (%)"]]
