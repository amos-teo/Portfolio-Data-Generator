import pandas as pd
import numpy as np
import math
import yfinance as yf
from datetime import date

input_base_ccy = 'USD'

'''Step1: Import Transaction Data into system'''
#Import file
xlsx = pd.ExcelFile('Transaction_Demo.xlsx')
#Import transactions tab
transactions = pd.read_excel(xlsx,'Transactions')
#Import asset class file
security_breakdown = pd.read_excel(xlsx,'Security Info')
#Clean trade date
transactions['trade_date'] = pd.to_datetime(transactions['trade_date'])
#Clean NA cells
transactions = transactions.fillna(0).sort_values('trade_date')


'''Step2: Import all relevant security and currency data'''

#Find unique tickers to search through yahoo finance, and exclude cash
security_list = transactions.ticker.unique()
security_list = [x for x in security_list if x != 'Cash']

#find currency to search through yahoo finance, and exclude USD
currency_list =  transactions.currency.unique()
currency_list = [x for x in currency_list if x != 'USD']

#Find out maximum and minimum dates
min_date = min(transactions['trade_date'])
max_date = date.today() + pd.DateOffset(days = 1)

#create security_master, currency_master to hold all security prices
security_master = pd.DataFrame()
currency_master = pd.DataFrame()
#loop through security list, go to yahoo finance and pull out security prices for the full date range
for ticker in security_list:
    #download data from yahoo finance
    download_df = yf.download(ticker,start = min_date + pd.DateOffset(days = -5),end = max_date,progress = False, actions = True).reset_index()
    #Clean date column, remove timezone
    download_df['Date'] = pd.to_datetime(download_df['Date']).dt.date
    #create a dataframe with the full date range
    fulldate_df = pd.DataFrame({'Date':pd.date_range(start = min_date + pd.DateOffset(days = -5) ,end = max_date + pd.DateOffset(days = -1) ) })
    fulldate_df['Date'] = pd.to_datetime(fulldate_df['Date']).dt.date
    #merge yahoo data into full date dataframe
    fulldate_df = fulldate_df.merge(download_df,how = 'left',left_on = 'Date',right_on = 'Date')
    #add ticker into dataframe before export
    fulldate_df['Ticker'] = ticker
    #Search for stock splits then edit prices before that day
    fulldate_df['Stock Splits'] = fulldate_df['Stock Splits'].fillna(0)
    #create new index column to be used to check position to adjust prices for stock split
    fulldate_df = fulldate_df.reset_index()
    #find index where there was a stock split, then scale all previous date prices according to ratio
    stocksplit_index = np.where(fulldate_df['Stock Splits'] > 0 )

    #Convert stock split index to list
    if fulldate_df['Stock Splits'].sum() >0:
        stocksplit_index = [int(x) for x in stocksplit_index]
    else:
        stocksplit_index = []

    #loop through all splits for that period
    while len(stocksplit_index) > 0 :
        for index in stocksplit_index:
            index = int(index)
            scale_factor = fulldate_df['Stock Splits'][index]
            fulldate_df['Adj Close'] = fulldate_df.apply(lambda x: x['Adj Close']*scale_factor if x['index'] < index else x['Adj Close'], axis = 1)
            stocksplit_index = stocksplit_index[1:]

    #drop all other columns except date,Adj Close, ticker
    fulldate_df = fulldate_df.reset_index()[['Date','Ticker','Adj Close','Stock Splits']]
    #update data onto security master dataframe
    security_master = pd.concat([security_master,fulldate_df],axis = 0)

#Loop through currency list, go to yahoo finance and pull out FX rates for the full date range
for currency in currency_list:
    #prepare currency pairing string for export
    currency_pairing = currency + input_base_ccy + '=X'
    #download data from yahoo finance
    download_df = yf.download(currency_pairing, start = min_date + pd.DateOffset(days = -5),end = max_date,progress = False).reset_index()
    #Clean date column, remove timezone
    download_df['Date'] = pd.to_datetime(download_df['Date']).dt.date
    #create a dataframe with the full date range
    fulldate_df = pd.DataFrame({'Date':pd.date_range(start = min_date + pd.DateOffset(days = -5) ,end = max_date+ pd.DateOffset(days = -1) ) })
    fulldate_df['Date'] = pd.to_datetime(fulldate_df['Date']).dt.date
    #merge yahoo data into full date dataframe
    fulldate_df = fulldate_df.merge(download_df,how = 'left',left_on = 'Date',right_on = 'Date')
    #add currency pairing into dataframe before export
    fulldate_df['Ticker'] = currency+input_base_ccy
    #drop all other columns except date, Adj Close, ticker
    fulldate_df = fulldate_df.reset_index()[['Date','Ticker','Adj Close']]
    #update data onto currency master dataframe
    currency_master = pd.concat([currency_master,fulldate_df],axis = 0)

#Fill cells with previous dates data if price not available
for i in range(len(security_master)):

    #for security master, while cell is na, take previous cell and replace. repeat till cell is not Nan.
    if i < len(security_master):
        offset = 1
        while pd.isna(security_master.iloc[i]['Adj Close'])  :
            security_master['Adj Close'].iloc[i] = security_master['Adj Close'].iloc[i-offset]
            offset += 1

    #for security master, while cell is na, take previous cell and replace. repeat till cell is not Nan.
    if i <len(currency_master):
        offset = 1
        while pd.isna(currency_master.iloc[i]['Adj Close'])  :
            currency_master['Adj Close'].iloc[i] = currency_master['Adj Close'].iloc[i-offset]
            offset += 1

security_master = security_master[security_master['Date'] >= min_date].sort_values(['Ticker','Date'])
currency_master = currency_master[currency_master['Date'] >= min_date].sort_values(['Ticker','Date'])

'''Step 3: Join all relevant price data into transaction list'''
#Convert date formats for security master and currency master
security_master['Date'] = security_master.Date.astype('datetime64[ns]')
currency_master['Date'] = currency_master.Date.astype('datetime64[ns]')

#Join prices for tickers and remove other columns
transactions = pd.merge(transactions,security_master[['Date','Ticker','Adj Close']] ,how = 'left', left_on = ['trade_date','ticker'],right_on = ['Date','Ticker'])
transactions = transactions.drop(columns = ['Ticker','Date']).rename(columns = {'Adj Close': 'latest_price' } )

#Join prices for currencies and remove other columns
currency_master['Currency'] = currency_master['Ticker'].apply(lambda x: x[:3])
transactions = pd.merge(transactions,currency_master[['Date','Currency','Adj Close']] ,how = 'left', left_on = ['trade_date','currency'],right_on = ['Date','Currency'])
transactions = transactions.drop(columns = ['Currency','Date']).rename(columns = {'Adj Close': 'FX_rate' } )

#Add FX Rate as 1 for base ccy
transactions['FX_rate'] = transactions.apply(lambda x: 1 if x['currency'] == input_base_ccy  else  x['FX_rate'],axis = 1 )

#Create column for settlement amount in base ccy
transactions['settlement_amount_base_ccy'] = transactions['settlement_amount_ccy']*transactions['FX_rate']

'''Step 4: Create daily holdings data'''
#Holdings dataframe
holdings = pd.DataFrame()
#loop through each date to generate daily holdings
for daily_date in pd.date_range(start = min_date ,end = max_date + pd.DateOffset(days = -1)):
    #convert daily date format
    #group securities ONLY by account and ticker, sum quantity column, then append to dataframe
    daily_securities = transactions[(transactions['trade_date'] <= daily_date) & (transactions['ticker'] != 'Cash')][['trade_date','account_name','ticker','currency','quantity']]
    daily_securities['date'] = daily_date
    #group securities and find sum of quantity
    daily_securities = daily_securities.groupby(['date','account_name','currency','ticker']).sum().reset_index()
    #upload daily securities into holdings dataframe
    holdings = pd.concat([holdings,daily_securities],axis= 0)

    #group cash by account and currency, sum settlement amount ccy column, and append to dataframe
    daily_cash = transactions[(transactions['trade_date'] <= daily_date)][['trade_date','account_name','ticker','currency','settlement_amount_ccy']]
    daily_cash['date'] = daily_date
    #change ticker to cash to upload into holdings
    daily_cash['ticker'] = 'Cash'
    #rename cash amount as quantity
    daily_cash = daily_cash.rename(columns = {'settlement_amount_ccy':'quantity'})
    #group cash and find sum of settlement amounts
    daily_cash = daily_cash.groupby(['date','account_name','currency','ticker']).sum().reset_index()
    #upload daily securities into holdings dataframe
    holdings = pd.concat([holdings,daily_cash],axis= 0)

#Convert date formats for holdings data
holdings['date'] = holdings.date.astype('datetime64[ns]')

###add daily prices into holdings data
#Join prices for tickers and remove other columns
holdings = pd.merge(holdings,security_master[['Date','Ticker','Adj Close']] ,how = 'left', left_on = ['date','ticker'],right_on = ['Date','Ticker'])
holdings = holdings.drop(columns = ['Ticker','Date']).rename(columns = {'Adj Close': 'latest_price' } )

#Join prices for currencies and remove other columns
holdings = pd.merge(holdings,currency_master[['Date','Currency','Adj Close']] ,how = 'left', left_on = ['date','currency'],right_on = ['Date','Currency'])
holdings = holdings.drop(columns = ['Currency','Date']).rename(columns = {'Adj Close': 'FX_rate' } )

#Add FX Rate as 1 for base ccy
holdings['FX_rate'] = holdings.apply(lambda x: 1 if x['currency'] == input_base_ccy  else  x['FX_rate'],axis = 1 )
#Add price = 1 for cash
holdings['latest_price'] = holdings.apply(lambda x: 1 if x['ticker'] == 'Cash'  else  x['latest_price'],axis = 1 )

#Add base ccy into holdings table
holdings['base_ccy'] = input_base_ccy

#add market value ccy and market value base ccy into holdings
holdings['market_value_ccy'] = holdings['quantity']*holdings['latest_price']
holdings['market_value_base_ccy'] = holdings['market_value_ccy'] * holdings['FX_rate']

'''Step 5: Calculate average price from transactions, join to Holdings'''

###Sum up transactions by trade date and account name. Get the sum of total purchase (settlement) and sales (quantity)
#Create new transaction dataframe to calculate average price, exclude all tickers where ticker is 'Cash'. Order transactions by account name, ticker, trade date, transaction type.
average_price_calc = transactions[transactions['ticker'] != 'Cash'].sort_values(['account_name','ticker','trade_date','transaction_type']).reset_index().drop(columns = ['index'])


###calculate average price from transactions
historical_cost_base_ccy = 0
historical_cost_ccy = 0
running_quantity = 0
#Create column called historical cost and running quantity
average_price_calc['historical_cost_base_ccy'] = 0
average_price_calc['historical_cost_ccy'] = 0
average_price_calc['running_quantity'] = 0

#Find Running Historical Cost; if account name or ticker is different from previous columns, restart cost and quantity calculations.
for i in range(len(average_price_calc)):
    #if position i is a new account or a new ticker, reset cost and quantity calculations.
    if i == 0:
        pass
    elif average_price_calc['account_name'].iloc[i] != average_price_calc['account_name'].iloc[i-1] or average_price_calc['ticker'].iloc[i] != average_price_calc['ticker'].iloc[i-1]:
        historical_cost_base_ccy = 0
        historical_cost_ccy = 0
        running_quantity = 0
    #Now we go through each transaction type to determine how we should deal with it.
    if average_price_calc['transaction_type'].iloc[i] == 'Purchase': #If purchase, add quantity, add settlement to historical cost
        running_quantity += average_price_calc['quantity'].iloc[i]  #change running numbers; add quantity
        historical_cost_base_ccy += average_price_calc['settlement_amount_base_ccy'].iloc[i] #change running numbers; add cost in base ccy
        historical_cost_ccy += average_price_calc['settlement_amount_ccy'].iloc[i] #change running numbers; add cost in ccy

    elif average_price_calc['transaction_type'].iloc[i] == 'Sale': #If sale, remove quantity, but scale down historical cost using (qty-x)/qty
        historical_cost_base_ccy = historical_cost_base_ccy * (running_quantity + average_price_calc['quantity'].iloc[i])/(running_quantity) #add quantity since quantity is already negative
        historical_cost_ccy = historical_cost_ccy * (running_quantity + average_price_calc['quantity'].iloc[i])/(running_quantity)  #add quantity since quantity is already negative
        running_quantity += average_price_calc['quantity'].iloc[i]  #add quantity since negative sign is already present

    elif average_price_calc['transaction_type'].iloc[i] == 'Stock Split': #If stock split, just add to running quantity, no cost changes
        running_quantity += average_price_calc['quantity'].iloc[i]  #add quantity since negative sign is already present

    #Update average price table with new tables
    average_price_calc['running_quantity'].iloc[i] = running_quantity
    average_price_calc['historical_cost_base_ccy'].iloc[i] = historical_cost_base_ccy
    average_price_calc['historical_cost_ccy'].iloc[i] = historical_cost_ccy


#Calculate running average price
average_price_calc['avg_price'] = average_price_calc['historical_cost_ccy'] / average_price_calc['running_quantity'] *-1

#Return only final transaction for each date --> account --> ticker.
holdings_price = average_price_calc
#Create new list which will hold indexes to keep to append to holdings dataframe
remove_price_list = []
#loop through holdings data. If next row has a different date/account/ticker, keep row. Else, remove row.
for i in range(len(holdings_price)):
    if i == len(holdings_price) -1: #if i is last row --> keep index
        pass
    else:
        #check if next row has a same date/account/ticker. If same then add index to remove list
        if holdings_price['trade_date'].iloc[i] == holdings_price['trade_date'].iloc[i+1] and holdings_price['account_name'].iloc[i] == holdings_price['account_name'].iloc[i+1] and holdings_price['ticker'].iloc[i] == holdings_price['ticker'].iloc[i+1]:
            remove_price_list += [i]

#Only keep last transaction for each day
holdings_price = holdings_price.drop(remove_price_list)

#Left join average price data to holdings data
holdings = pd.merge(holdings, holdings_price[['trade_date','account_name','ticker','historical_cost_base_ccy','historical_cost_ccy','avg_price']], how = 'left',left_on = ['date','account_name','ticker'],right_on = ['trade_date','account_name','ticker'])

#drop trade date from holdings
holdings = holdings.drop(columns = ['trade_date'])

#Sort holdings by ticker -> account -> date
holdings = holdings.sort_values(['account_name','ticker','date'])

###Fill up all other dates with average prices, using average price of previous date if no transaction is made for that day/account/ticker
#Loop through row by row. If current row has value, skip, else use previous row value
for i in range(len(holdings)):
    if np.isnan(holdings['historical_cost_ccy'].iloc[i]) == False: #If historical cost ccy is filled, move on to next row
        continue
    elif holdings['ticker'].iloc[i] not in security_list: #If ticker is not in security list, i.e. Cash, skip
        continue
    else: #Else, fill up today's cost data with yesterday's cost data
        holdings['historical_cost_ccy'].iloc[i] = holdings['historical_cost_ccy'].iloc[i-1]
        holdings['historical_cost_base_ccy'].iloc[i] = holdings['historical_cost_base_ccy'].iloc[i-1]
        holdings['avg_price'].iloc[i] = holdings['avg_price'].iloc[i-1]

#Sort holdings back to proper format i.e by date --> account  --> tickers
holdings = holdings.sort_values(['date','account_name','ticker'])

'''Step 6: Create daily performance calculations for individual accounts'''
#Performance calculation page to include date,account name,networth,money in/out, transfer in/out amounts & notional amounts
#For individual accounts ONLY
###We will need the following columns for each account: market value base ccy, money in/out base ccy, distribution amounts

#Sum up networth for each account daily
daily_performance = holdings[['date','account_name','market_value_base_ccy']].groupby(['date','account_name']).sum().reset_index()
#Sum up daily money inflow and outflow by account
flows_by_account  = transactions[transactions['transaction_type'].str.contains('Money')][['trade_date','account_name','settlement_amount_base_ccy']].groupby(['trade_date','account_name']).sum().reset_index().rename(columns = {'settlement_amount_base_ccy':'money_flow_base_ccy'})
#Left join to performance calculations
daily_performance = pd.merge(daily_performance,flows_by_account,how = 'left',left_on = ['date','account_name'], right_on = ['trade_date','account_name'])
#Clean up: Drop additional date column and fill na as 0
daily_performance = daily_performance.drop(columns = 'trade_date').fillna(0).sort_values(['account_name','date'])
#Add type of performance calculation eg by account, by entire portfolio etc
daily_performance['calculation_type'] = 'by_sub_account'
#Create profit and return column
daily_performance['profit_base_ccy'] = 0
daily_performance['returns'] = 0

#Calculate profit as market value today - money flow today - market value yesterday
for i in range(len(daily_performance)):

    if i == 0  or daily_performance['account_name'].iloc[i] != daily_performance['account_name'].iloc[i-1]: #if it is the first day of the account, calculate profit and performance using current day numbers
        daily_performance['profit_base_ccy'].iloc[i] = daily_performance['market_value_base_ccy'].iloc[i] - daily_performance['money_flow_base_ccy'].iloc[i]
        daily_performance['returns'].iloc[i] =  daily_performance['market_value_base_ccy'].iloc[i] / daily_performance['money_flow_base_ccy'].iloc[i]
    else: #Else, calculate profit as market value today - market value yesterday - money flow today. returns will be 1+ profits / market value yesterday
        daily_performance['profit_base_ccy'].iloc[i] = daily_performance['market_value_base_ccy'].iloc[i] - daily_performance['market_value_base_ccy'].iloc[i-1] - daily_performance['money_flow_base_ccy'].iloc[i]
        daily_performance['returns'].iloc[i] = 1 +  (daily_performance['market_value_base_ccy'].iloc[i] - daily_performance['market_value_base_ccy'].iloc[i-1] - daily_performance['money_flow_base_ccy'].iloc[i]) / daily_performance['market_value_base_ccy'].iloc[i-1]

'''Step 7: Create daily performance calculations for the whole portfolio'''
#Use daily calculations for accounts, sum them up to form total portfolio calculations, then rerun returns
total_daily_performance = daily_performance[['date','market_value_base_ccy','money_flow_base_ccy','profit_base_ccy']].groupby(['date']).sum().reset_index()
#Add calculation type as text
total_daily_performance['calculation_type'] = 'by_entire_portfolio'
#Add name of total account
total_daily_performance['account_name'] = 'Entire Portfolio'
#Calculate returns again for entire portfolio
total_daily_performance['returns'] = 0
for i in range(len(total_daily_performance)):

    if i == 0 : #if it is the first day of the account, calculate profit and performance using current day numbers
        total_daily_performance['returns'].iloc[i] =  total_daily_performance['market_value_base_ccy'].iloc[i] / total_daily_performance['money_flow_base_ccy'].iloc[i]
    else: #Else, calculate profit as market value today - market value yesterday - money flow today. returns will be 1+ profits / market value yesterday
        total_daily_performance['returns'].iloc[i] = 1 +  (total_daily_performance['market_value_base_ccy'].iloc[i] - total_daily_performance['market_value_base_ccy'].iloc[i-1] - total_daily_performance['money_flow_base_ccy'].iloc[i]) / total_daily_performance['market_value_base_ccy'].iloc[i-1]

#concat back to performance dataframe for export
daily_performance = pd.concat([daily_performance,total_daily_performance] ,axis = 0)

'''Step 8: Calculate asset breakdown to break down funds'''
#We start from the holdings dataframe, drop irrelevant columns
holdings_breakdown = holdings.drop(columns = ['historical_cost_ccy','historical_cost_base_ccy','avg_price'])
#Outer join the security breakdown table to the holdings table.
holdings_breakdown = pd.merge(holdings_breakdown,security_breakdown, how = 'outer',left_on = ['ticker'],right_on = ['ticker'])
#Sort holdings breakdown by date,account, ticker
holdings_breakdown = holdings_breakdown.sort_values(['date','account_name','ticker'])
#Add asset class and gics sector and pct for cash as cash
holdings_breakdown['asset_class'] = holdings_breakdown.apply(lambda x: 'Cash' if x['ticker'] == 'Cash' else x['asset_class'], axis =1)
holdings_breakdown['gics_sector'] = holdings_breakdown.apply(lambda x: 'Cash' if x['ticker'] == 'Cash' else x['gics_sector'], axis = 1)
holdings_breakdown['pct'] = holdings_breakdown.apply(lambda x: 1 if x['ticker'] == 'Cash' else x['pct'], axis = 1)
#Calculate market value by industry using % breakdown for funds
holdings_breakdown['market_value_breakdown_base_ccy'] = holdings_breakdown['pct'] * holdings_breakdown['market_value_base_ccy']

#Calculate the actual market value based on the percentage breakdown


with pd.ExcelWriter('Portfolio_Demo_Data.xlsx') as writer:
    security_master.to_excel(writer,sheet_name = 'SECURITY MASTER',index = False)
    currency_master.to_excel(writer,sheet_name = 'CURRENCY MASTER',index = False)
    holdings.to_excel(writer,sheet_name = 'Holdings', index = False)
    transactions.to_excel(writer, sheet_name = 'Transactions', index = False)
    daily_performance.to_excel(writer, sheet_name = 'Performance', index = False)
    holdings_breakdown.to_excel(writer, sheet_name = 'Asset Breakdown', index =  False)
