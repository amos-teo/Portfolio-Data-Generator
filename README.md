# Portfolio-Data-Generator
Python code will generate necessary portfolio information to be used for allocation and performance analysis, all from a transaction list and additional asset class data.

This code uses the yfinance package to pull out prices for the time period. Thereafter, it will use those prices to calculate daily holdings.

Additional asset class and industry data is required in order to run asset allocation analysis.

The daily holdings will be used as the basis for performance calculations.

The demo ("Transaction_Demo") includes Cash, Public Equities and Funds where prices are available on Yahoo Finance.

The code can be used for transactions like Purchase, Sale, Money In or Out, Distributions or Contributions.

It will also require the user to map the transactions that matches the format provided. Use ticker from Yahoo Finance, eg. Tesla = TSLA, Apple = AAPL

Please check out some visualizations that can be produced with available data.
https://public.tableau.com/app/profile/amos.teo/viz/PerformanceDemoUsingPython/PerformanceSummary
