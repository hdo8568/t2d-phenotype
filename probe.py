##ata bvailability check on encouhnter and supplies to see which control conditios are actually tesatble in Coherent.

import pandas as pd
enc = pd.read_csv("encounters.csv")
print("encounter columns:", list(enc.columns))
for col in ("ENCOUNTERCLASS", "CLASS", "TYPE"):
    if col in enc.columns:
        print(f"\n{col}:"); print(enc[col].value_counts().to_string())

sup = pd.read_csv("supplies.csv")
print("\nsupplies columns:", list(sup.columns), "| rows:", len(sup))
if "DESCRIPTION" in sup.columns:
    print(sup["DESCRIPTION"].value_counts().head(15).to_string())


con = pd.read_csv("conditions.csv")
print(con.groupby(["CODE", "DESCRIPTION"])["PATIENT"].nunique()
      .sort_values(ascending=False).to_string())