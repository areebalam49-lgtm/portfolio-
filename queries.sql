-- Portfolio analysis queries. Run against outputs/portfolio.db

-- Q1. Application success rate
SELECT  COUNT(*)                                             AS applications,
        SUM(shares_allotted > 0)                             AS allotted,
        ROUND(100.0 * SUM(shares_allotted > 0) / COUNT(*), 1) AS success_rate_pct
FROM    applications;

-- Q2. Holding-level performance, best first
SELECT  company,
        shares,
        issue_price,
        market_price,
        ROUND(invested)                                       AS invested_rs,
        ROUND(current_value)                                  AS value_rs,
        ROUND(profit)                                         AS profit_rs,
        ROUND(100.0 * (market_price - issue_price) / issue_price, 1) AS return_pct,
        days_held
FROM    v_holdings
ORDER BY return_pct DESC;

-- Q3. Portfolio totals
SELECT  ROUND(SUM(invested))                                  AS invested_rs,
        ROUND(SUM(current_value))                             AS value_rs,
        ROUND(SUM(profit))                                    AS profit_rs,
        ROUND(100.0 * SUM(profit) / SUM(invested), 1)         AS portfolio_return_pct
FROM    v_holdings;

-- Q4. Each holding's share of capital and of total profit
SELECT  company,
        ROUND(100.0 * invested / (SELECT SUM(invested) FROM v_holdings), 1) AS capital_share_pct,
        ROUND(100.0 * profit   / (SELECT SUM(profit)   FROM v_holdings), 1) AS profit_contribution_pct
FROM    v_holdings
ORDER BY profit_contribution_pct DESC;

-- Q5. Win rate: how many holdings trade above issue price
SELECT  SUM(market_price > issue_price)                       AS winners,
        SUM(market_price <= issue_price)                      AS losers,
        ROUND(100.0 * AVG(market_price > issue_price), 1)     AS win_rate_pct
FROM    v_holdings;

-- Q6. Concentration (Herfindahl index of capital weights; 0.25 = perfectly equal across 4)
SELECT  ROUND(SUM((invested * 1.0 / t.total) * (invested * 1.0 / t.total)), 3) AS hhi
FROM    v_holdings, (SELECT SUM(invested) AS total FROM v_holdings) t;

-- Q7. ETF watchlist: where each ETF sits in its 52-week range
SELECT  ticker,
        close,
        ROUND(100.0 * (close - week52_low) / (week52_high - week52_low), 1) AS position_in_range_pct,
        ROUND(100.0 * (close - week52_high) / week52_high, 1)               AS from_52w_high_pct,
        ROUND(100.0 * (close - week52_low)  / week52_low, 1)                AS from_52w_low_pct
FROM    etf_watchlist;
