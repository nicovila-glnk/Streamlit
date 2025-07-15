import pandas as pd
import streamlit as st

def load_maps():
    # read all your mapping CSVs from data/
    sex_map = pd.read_csv("data/sex.csv",   dtype=str).set_index("Key")["Value"].to_dict()
    age_map = pd.read_csv("data/age.csv",   dtype=str).set_index("Key")["Value"].to_dict()
    region_map = pd.read_csv("data/ben_reg.csv", dtype=str).set_index("Key")["Value"].to_dict()
    presc_map = pd.read_csv("data/prescribers.csv", dtype=str).set_index("Key")["Value"].to_dict()
    cpi_map = pd.read_csv("data/cpi.csv",        dtype=str).set_index("Key")["Value"].to_dict()
    return sex_map, age_map, region_map, presc_map, cpi_map

def load_unified(path: str, key_col: str):
    """
    Load unified brand or generic CSV, map codes → labels, identify prescribers.
    Returns: df, display_column_name, prescriber_list
    """
    df = pd.read_csv(path, dtype=str)
    # coerce numeric
    df["total_boites"] = (
        pd.to_numeric(df["total_boites"], errors="coerce")
          .fillna(0)
          .astype(int)
    )
    key_cols = ["BEN_REG", "sexe", "age", "CIP13", "GEN_NUM", "total_boites"]
    prescriber_cols = [c for c in df.columns if c not in key_cols]
    df[prescriber_cols] = (
        df[prescriber_cols]
          .apply(pd.to_numeric, errors="coerce")
          .fillna(0)
          .astype(int)
    )

    sex_map, age_map, region_map, presc_map, cpi_map = load_maps()

    # map demographics
    df["Region"] = df["BEN_REG"].map(region_map).fillna(df["BEN_REG"])
    df["Sex"]    = df["sexe"].   map(sex_map).   fillna(df["sexe"])
    df["Age"]    = df["age"].    map(age_map).   fillna(df["age"])

    # product label
    if key_col == "GEN_NUM":
        df["Generic"] = df["GEN_NUM"]
        display = "Generic"
    else:
        df["Medication"] = df["CIP13"].map(cpi_map).fillna(df["CIP13"])
        display = "Medication"

    # drop raw codes
    df = df.drop(columns=["BEN_REG","sexe","age","CIP13","GEN_NUM"], errors="ignore")

    # rename prescriber cols
    core = {"Region", "Sex", "Age", display, "total_boites"}
    raw_pres = [c for c in df.columns if c not in core]
    df = df.rename(columns={c: presc_map.get(c, c) for c in raw_pres})
    prescribers = [presc_map.get(c, c) for c in raw_pres]

    return df, display, prescribers
