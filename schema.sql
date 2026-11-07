-- IPO portfolio database (SQLite)
-- Built automatically by src/analysis.py from the CSV files in data/

DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS prices;
DROP TABLE IF EXISTS etf_watchlist;

CREATE TABLE applications (
    company          TEXT PRIMARY KEY,
    sector           TEXT NOT NULL,
    shares_applied   INTEGER NOT NULL,
    issue_price      REAL NOT NULL,
    amount_blocked   REAL NOT NULL,
    shares_allotted  INTEGER NOT NULL,
    status           TEXT NOT NULL,
    listing_date     DATE NOT NULL
);

CREATE TABLE prices (
    company       TEXT NOT NULL REFERENCES applications(company),
    price_date    DATE NOT NULL,
    market_price  REAL NOT NULL,
    source        TEXT,
    PRIMARY KEY (company, price_date)
);

CREATE TABLE etf_watchlist (
    etf             TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    "index"         TEXT NOT NULL,
    price_date      DATE NOT NULL,
    close           REAL NOT NULL,
    day_change_pct  REAL,
    week52_low      REAL,
    week52_high     REAL
);

-- Holdings with cost, value and profit, using the latest price for each stock
DROP VIEW IF EXISTS v_holdings;
CREATE VIEW v_holdings AS
SELECT  a.company,
        a.sector,
        a.shares_allotted                              AS shares,
        a.issue_price,
        a.shares_allotted * a.issue_price              AS invested,
        p.market_price,
        p.price_date,
        a.shares_allotted * p.market_price             AS current_value,
        a.shares_allotted * (p.market_price - a.issue_price) AS profit,
        a.listing_date,
        CAST(julianday(p.price_date) - julianday(a.listing_date) AS INTEGER) AS days_held
FROM    applications a
JOIN    prices p ON p.company = a.company
WHERE   a.shares_allotted > 0
  AND   p.price_date = (SELECT MAX(price_date) FROM prices p2 WHERE p2.company = a.company);
