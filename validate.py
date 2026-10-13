import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, text
from db import get_engine

engine = get_engine()


def load_checks(path="checks.sql"):
    """Split checks.sql into {check_name: query}."""
    raw = open(path).read()
    parts = re.split(r"^-- name:\s*(\w+)\s*$", raw, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip().rstrip(";") for i in range(1, len(parts), 2)}


KEY_COLS = ["reporter_code", "reporter_name", "period"]
REPORT_DIR = Path("reports")


def describe(row):
    """Turn the extra columns of a check result into one readable string."""
    bits = []
    for col in row.index:
        if col in KEY_COLS:
            continue
        v = row[col]
        bits.append(f"{col}={v:,.1f}" if isinstance(v, float) else f"{col}={v}")
    return ", ".join(bits)


def run_checks():
    frames = []
    for name, query in load_checks().items():
        df = pd.read_sql(text(query), engine)
        if df.empty:
            continue
        flags = df[KEY_COLS].copy()
        flags["detail"] = df.apply(describe, axis=1)
        flags.insert(0, "check_name", name)
        frames.append(flags)
    return pd.concat(frames, ignore_index=True)


def plot_flags(flags):
    data = pd.read_sql(text(
        "SELECT reporter_code, reporter_name, period, net_wgt_kg FROM trade_flows ORDER BY period"
    ), engine)
    data["month"] = pd.to_datetime(data["period"].astype(str), format="%Y%m")
    data["kt"] = data["net_wgt_kg"] / 1e6          # kg to thousand tonnes

    reporters = data[["reporter_code", "reporter_name"]].drop_duplicates().values.tolist()
    fig, axes = plt.subplots(len(reporters), 1, figsize=(10, 2.4 * len(reporters)), sharex=True)
    for ax, (code, name) in zip(axes, reporters):
        d = data[data.reporter_code == code]
        ax.plot(d["month"], d["kt"], marker="o", markersize=3, linewidth=1)
        flagged = flags.loc[flags.reporter_code == code, "period"].unique()
        f = d[d["period"].isin(flagged)]
        ax.scatter(f["month"], f["kt"], color="red", marker="x", s=60, zorder=3, label="flagged")
        ax.set_ylabel("kt")
        ax.set_title(f"{name}: monthly copper concentrate imports", fontsize=9, loc="left")
    axes[0].legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    out = REPORT_DIR / "flows_flagged.png"
    fig.savefig(out, dpi=150)
    return out


if __name__ == "__main__":
    REPORT_DIR.mkdir(exist_ok=True)
    flags = run_checks()

    flags.to_sql("dq_flags", engine, if_exists="replace", index=False)
    flags.to_csv(REPORT_DIR / "dq_flags.csv", index=False)

    print(f"{len(flags)} flags raised\n")
    print(flags.groupby("check_name").size().to_string(), "\n")

    multi = (flags.groupby(["reporter_name", "period"])["check_name"]
                  .nunique().reset_index(name="checks_failed"))
    multi = multi[multi.checks_failed >= 2].sort_values(["reporter_name", "period"])
    print("Months flagged by 2+ checks:")
    print(multi.to_string(index=False), "\n")

    print("Chart saved to", plot_flags(flags))