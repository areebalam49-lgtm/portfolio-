"""IPO portfolio analysis.

Reads the CSV files, builds a SQLite database, runs the queries in queries.sql,
and writes the charts and portfolio_summary.md, all in the repository folder.

Usage:  python analysis.py
"""
import re
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = SQL = OUT = REP = CHARTS = ROOT   # all files live in the repository root
CHARTS.mkdir(parents=True, exist_ok=True)
REP.mkdir(exist_ok=True)

COLORS = {"Dhoot Transmission": "#7A1F2B", "Symbiotec Pharmalab": "#2F5D50",
          "Jio Platforms": "#C9A227", "Armee Infotech": "#4A6C8C"}
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def build_db() -> sqlite3.Connection:
    db = OUT / "portfolio.db"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript((SQL / "schema.sql").read_text())
    pd.read_csv(DATA / "applications.csv").to_sql("applications", con, if_exists="append", index=False)
    for f in sorted(DATA.glob("prices_*.csv")):
        pd.read_csv(f).to_sql("prices", con, if_exists="append", index=False)
    pd.read_csv(DATA / "etf_watchlist.csv").to_sql("etf_watchlist", con, if_exists="append", index=False)
    con.commit()
    return con


def run_queries(con) -> dict:
    text = (SQL / "queries.sql").read_text()
    blocks = re.split(r"\n(?=-- Q\d+\.)", text)[1:]
    results = {}
    for b in blocks:
        title = b.splitlines()[0].lstrip("- ").strip()
        results[title] = pd.read_sql_query(b, con)
    return results


def charts(h: pd.DataFrame, etf: pd.DataFrame) -> None:
    h = h.sort_values("invested", ascending=False)
    cols = [COLORS.get(c, "#888") for c in h["company"]]

    # 1. capital allocation
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(h["invested"], labels=h["company"], colors=cols, autopct="%1.1f%%", startangle=90,
           counterclock=False, wedgeprops=dict(edgecolor="white", linewidth=2),
           textprops=dict(fontsize=10))
    ax.set_title(f"Capital allocation (Rs {h['invested'].sum():,.0f})", fontweight="bold")
    fig.savefig(CHARTS / "1_capital_allocation.png"); plt.close(fig)

    # 2. return vs issue price
    r = h.assign(ret=100 * (h.market_price - h.issue_price) / h.issue_price).sort_values("ret")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(r["company"], r["ret"], color=[COLORS[c] for c in r["company"]])
    ax.axvline(0, color="black", lw=0.8)
    for b, v in zip(bars, r["ret"]):
        ax.text(v + (2 if v >= 0 else -2), b.get_y() + b.get_height() / 2, f"{v:+.1f}%",
                va="center", ha="left" if v >= 0 else "right", fontweight="bold")
    ax.set_xlim(r["ret"].min() - 20, r["ret"].max() + 20)
    ax.set_xlabel("Return vs issue price (%)")
    ax.set_title("Return on each holding", fontweight="bold")
    fig.savefig(CHARTS / "2_returns_by_holding.png"); plt.close(fig)

    # 3. profit contribution (waterfall-style)
    p = h.sort_values("profit", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    running = 0
    for comp, val in zip(p["company"], p["profit"]):
        ax.bar(comp, val, bottom=running if val >= 0 else running + val, color=COLORS[comp])
        ax.text(comp, running + val + (300 if val >= 0 else -300), f"{val:+,.0f}",
                ha="center", va="bottom" if val >= 0 else "top", fontsize=10)
        running += val
    ax.bar("Total", running, color="#333333")
    ax.text("Total", running + 300, f"{running:+,.0f}", ha="center", va="bottom", fontweight="bold")
    ax.set_ylabel("Profit (Rs)")
    ax.set_title("Where the profit came from", fontweight="bold")
    plt.setp(ax.get_xticklabels(), rotation=15)
    fig.savefig(CHARTS / "3_profit_contribution.png"); plt.close(fig)

    # 4. invested vs current value
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(h))
    ax.bar([i - 0.2 for i in x], h["invested"], 0.4, label="Invested", color="#BFB8AA")
    ax.bar([i + 0.2 for i in x], h["current_value"], 0.4, label="Current value", color=cols)
    ax.set_xticks(list(x)); ax.set_xticklabels(h["company"], rotation=15)
    ax.set_ylabel("Rs"); ax.legend(frameon=False)
    ax.set_title("Invested vs current value", fontweight="bold")
    fig.savefig(CHARTS / "4_invested_vs_value.png"); plt.close(fig)

    # 5. ETF watchlist: position in 52-week range
    fig, axes = plt.subplots(len(etf), 1, figsize=(8, 1.8 * len(etf)))
    for ax, (_, e) in zip(axes, etf.iterrows()):
        lo, hi, px = e.week52_low, e.week52_high, e.close
        ax.barh([0], [hi - lo], left=lo, color="#E6E0D4", height=0.5)
        ax.barh([0], [px - lo], left=lo, color="#2F5D50", height=0.5)
        ax.axvline(px, color="black", lw=2)
        ax.set_yticks([]); ax.spines["left"].set_visible(False)
        pos = 100 * (px - lo) / (hi - lo)
        ax.set_title(f"{e.ticker}: Rs {px:.2f} ({pos:.0f}% of 52-week range)", fontsize=10, loc="left")
        ax.set_xlim(lo, hi)
    fig.suptitle("ETF watchlist", fontweight="bold")
    fig.tight_layout()
    fig.savefig(CHARTS / "5_etf_watchlist.png"); plt.close(fig)


def report(res: dict, h: pd.DataFrame, outlook: pd.DataFrame) -> None:
    t = res[[k for k in res if k.startswith("Q3")][0]].iloc[0]
    s = res[[k for k in res if k.startswith("Q1")][0]].iloc[0]
    w = res[[k for k in res if k.startswith("Q5")][0]].iloc[0]
    hhi = res[[k for k in res if k.startswith("Q6")][0]].iloc[0, 0]
    price_date = h["price_date"].max()
    lines = [f"# Portfolio summary (prices as of {price_date})", "",
             f"- Applications: {int(s.applications)}, allotted: {int(s.allotted)} ({s.success_rate_pct:.0f}% success)",
             f"- Invested: Rs {t.invested_rs:,.0f}",
             f"- Current value: Rs {t.value_rs:,.0f}",
             f"- Unrealised profit: Rs {t.profit_rs:,.0f} ({t.portfolio_return_pct:+.1f}%)",
             f"- Win rate: {int(w.winners)} of {int(w.winners + w.losers)} holdings above issue price",
             f"- Concentration (HHI): {hhi} (0.25 = equal weights across 4 stocks)", ""]
    for title, df in res.items():
        lines += [f"## {title}", "", df.to_markdown(index=False), ""]
    lines += ["## Qualitative outlook (personal assessment, not a forecast)", "",
              outlook.to_markdown(index=False), ""]
    (REP / "portfolio_summary.md").write_text("\n".join(lines))


def main():
    con = build_db()
    res = run_queries(con)
    h = pd.read_sql_query("SELECT * FROM v_holdings", con)
    etf = pd.read_sql_query("SELECT * FROM etf_watchlist", con)
    outlook = pd.read_csv(DATA / "outlook.csv")
    charts(h, etf)
    report(res, h, outlook)
    con.close()
    print((REP / "portfolio_summary.md").read_text().split("\n## ")[0])


if __name__ == "__main__":
    main()
