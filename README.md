# Portfolio-Data-Generator
Code will generate necessary portfolio information to be used for allocation and performance analysis, all from a list of transactions and additional asset class data.

This code uses the yfinance package to pull out prices for public securities since inception. Thereafter, it will use those prices to calculate daily holdings.

Additional asset class and industry data is required in order to run asset allocation analysis.

The daily holdings will be used as the basis for performance calculations.

The demo ("Transaction_Demo") includes Cash, Public Equities and Funds where prices are available on Yahoo Finance.

The code can be used for transactions like Purchase, Sale, Money In or Out, Distributions or Contributions.

It will also require the user to map the transactions to matches the format provided. Use ticker from Yahoo Finance, eg. Tesla = TSLA, Apple = AAPL

You may also specify the index(es) you want to use in the analysis. The set-up so far can hold a mix of 2 indexes based on percentages which you specify. To set up the performance and standard deviation calculations on Tableau, please refer to the workbook linked below.

The 'Portfolio_Demo_Data.xslx' file contains the output which can be used for visualization and reporting.

Please check out some visualizations that can be produced using data generated.
https://public.tableau.com/app/profile/amos.teo/viz/PerformanceDemoUsingPython/PerformanceSummary
