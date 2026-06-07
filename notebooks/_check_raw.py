import sys, pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
total = t0 = t1 = 0
for c in pd.read_csv("data/raw/criteo-uplift.csv", chunksize=5_000_000):
    total += len(c)
    t0 += int((c["treatment"] == 0).sum())
    t1 += int((c["treatment"] == 1).sum())
print(f"Total rows: {total}, treatment=0: {t0}, treatment=1: {t1}")
print(f"Ratio control: {t0/total:.4f}, treatment: {t1/total:.4f}")
