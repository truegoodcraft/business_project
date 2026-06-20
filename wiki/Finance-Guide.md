# Finance Guide

Finance gives an operational view of the business events recorded in BUS Core. It is not a complete accounting ledger or tax system.

## What It Shows

- Gross Sales, Returns, and Net Sales
- COGS and Gross Profit
- Expenses and Net Profit
- Manufacturing run and produced-item context
- A transaction feed including supported sales, refunds, expenses, manufacturing runs, and inferred purchases

COGS means the inventory cost assigned to sold goods. Gross Profit is sales after returns and COGS. Net Profit also accounts for expenses recorded in BUS Core. Results are only as complete as the events and costs you record.

## Why Sale Price Matters

When Stock Out uses reason **Sold**, the sale price supplies revenue for the cash event. If the product has a usual price, BUS Core pre-fills it and warns non-blockingly when the entered amount is lower. A missing or incorrect sale price makes profit reporting less useful.

## Date Ranges

Enter From and To dates or use **Last 30 days**, **This month**, **Last month**, **This quarter**, **Last quarter**, or **This year**. Select **Refresh** after choosing a custom range.

## CSV Export

Select **Export CSV** to download the Finance transaction export for the selected date range. Use it for review or transfer into your own bookkeeping process; it is not direct QuickBooks or Wave synchronization.

## Boundary

BUS Core does not replace double-entry accounting, bank reconciliation, payroll, tax filing, tax advice, or an accountant. Reconcile BUS Core's operational figures with your accounting system.

Next: [Backup and Restore](Backups-and-Data-Persistence.md).
