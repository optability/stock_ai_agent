#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 28 22:06:35 2020

@author: Roshan Issac
"""
#Please comment below two variables after first run




import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pickle
import json
import requests
from csv import writer
from pathlib import Path
import datetime
import time,math
import jsonpickle
import alpaca_trade_api as tradeapi


#append row to a file
def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)
        
#overwrite row to a file
def overwrite_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'w+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)

#Reading configuration file

with open("config.json") as json_data_file:
    datajson = json.load(json_data_file)




#Alpaca API Endpoint

api = tradeapi.REST(datajson["alpacaapi"]["key_id"], datajson["alpacaapi"]["secret"], api_version=datajson["alpacaapi"]["version"]) # or use ENV Vars shown below


#Making a request
data = api.get_barset(symbols=datajson["stock_parameters"]["share_name"],timeframe=datajson["alpacaapi"]["timeframe"],limit=datajson["alpacaapi"]["limit"])


keys = ['c','h','l','o','t','v']
keys1 = ['closePrice','highPrice','lowPrice','openPrice','tradeTimeInLong','totalVolume']

stock_df = pd.DataFrame()
for key, value in data.items():
	serialized_data = jsonpickle.encode(value)
	data_dict = json.loads(serialized_data)
	new_value = [data_dict['_raw'][0].get(key) for key in keys]
	stock_dict = dict(zip(keys1,new_value))
	stock_dict['Stock']=key
	stock_df = stock_df.append(stock_dict, ignore_index=True)
	
#print(stock_df.head())

my_file = Path(str(datajson["files"]["logfile"]))
my_previous = Path(str(datajson["files"]["statusfile"]))
column_list = ['Stock','Timestamp','DateTime','Open Price','High','Low','Close','Ask','Bid','TotalVolume','Predicted Price','Trend','Trade_Status','TradePrice','Noofshares','profit','CurrentPool']
starting_pool=datajson["stock_parameters"]["starting_pool"]
profit=datajson["stock_parameters"]["profit"]
output=[]
previous_trade_status=0
last_trend ='null'
status=''
TradePrice=''

if my_file.is_file():
	print("File Exist")
	df = pd.read_csv(datajson["files"]["logfile"])
	for index, row in stock_df.iterrows():
		options = [row['Stock']]
		rslt_df = df[df['Stock'].isin(options)]
		last_trend=rslt_df['Trend'].iloc[-1]
		print("Stock ",row['Stock'])
		print("Last Trend",last_trend)
		date_time=datetime.datetime.fromtimestamp(row['tradeTimeInLong']).strftime('%Y-%m-%d %H:%M:%S')

		with open(datajson["model"]["modelpath"]+row['Stock']+'_model.pkl',"rb") as saved_processing:
			model,sc_X,sc_y = pickle.load(saved_processing)

		saved_processing.close()


		pred_price=sc_y.inverse_transform(model.predict(sc_X.transform([[row['openPrice'],row['highPrice'],row['lowPrice'],row['totalVolume']]])))
		pred_price=round(pred_price[0],2)
		if row['closePrice'] > row['openPrice'] and pred_price > row['openPrice'] :
			Trend="Uptrend"
		elif row['closePrice'] < row['openPrice'] and pred_price < row['openPrice']:
			Trend="Uptrend"
		else:
			Trend="Downtrend"
		#Trend='Uptrend'
		flag = bool(Trend == last_trend)
		no_of_shares=''  

		if my_previous.is_file():
			previous_df = pd.read_csv(datajson["files"]["statusfile"])
			prev_rslt_df = previous_df[previous_df['Stock'].isin(options)]
			#last_trend = previous_df['Trend']
			if prev_rslt_df.empty:
				print("No data for ",previous_df['Stock'])
			else:
				previous_trade_status = prev_rslt_df['Trade_Status']
				traded_price = prev_rslt_df['TradePrice'].astype(str)
				shares_holding = prev_rslt_df['Noofshares'].astype(str)
				existing_current_pool = prev_rslt_df['CurrentPool'].astype(str)
				existing_current_pool=existing_current_pool.values[0]

		if(Trend=='Downtrend' and flag==False and last_trend=='Uptrend'):
		    #no_of_shares= math.floor(starting_pool/row['bidPrice'])
		    status='SELL'
		    TradePrice = row['closePrice']
		    profit=float(shares_holding)*float((float(TradePrice)-float(traded_price)))
		    existing_current_pool = float(existing_current_pool) + float(profit)
		elif(Trend=='Uptrend' and flag==False and last_trend=='Downtrend'):
			TradePrice = row['closePrice']
			no_of_shares= math.floor(existing_current_pool/row['closePrice'])
			status='BUY'
		output=[row['Stock'],row['tradeTimeInLong'],date_time,row['openPrice'],row['highPrice'],row['lowPrice'],row['closePrice'],0,0,row['totalVolume'],pred_price,Trend,status,TradePrice,no_of_shares,profit,existing_current_pool]
		append_list_as_row(datajson["files"]["logfile"],output)
		if(status=='BUY' or status=='SELL'):
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Stock']=row['Stock']
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Timestamp']=row['tradeTimeInLong']
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'DateTime']=date_time
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Open Price']=row['openPrice']
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'High']=row['highPrice']
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Low']=row['lowPrice']
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Close']=row['closePrice']
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Ask']=0
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Bid']=0
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'TotalVolume']=row['totalVolume']
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Predicted Price']=pred_price
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Trend']=Trend
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Trade_Status']=status
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'TradePrice']=TradePrice
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'Noofshares']=no_of_shares
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'profit']=profit
			previous_df.loc[previous_df['Stock'] == row['Stock'], 'CurrentPool']=existing_current_pool
			previous_df.to_csv(datajson["files"]["statusfile"], encoding='utf-8', index=False)



else:
	print("File Dont Exist")
	log_flag=0
	status_flag=0
	for index, row in stock_df.iterrows():
		date_time=datetime.datetime.fromtimestamp(row['tradeTimeInLong']).strftime('%Y-%m-%d %H:%M:%S')
		#Loading model
		with open(datajson["model"]["modelpath"]+row['Stock']+'_model.pkl',"rb") as saved_processing:
			model,sc_X,sc_y = pickle.load(saved_processing)
		saved_processing.close()

		pred_price=sc_y.inverse_transform(model.predict(sc_X.transform([[row['openPrice'],row['highPrice'],row['lowPrice'],row['totalVolume']]])))
		pred_price=round(pred_price[0],2)
		if row['closePrice'] > row['openPrice'] and pred_price > row['openPrice'] :
			Trend="Uptrend"
		elif row['closePrice'] < row['openPrice'] and pred_price < row['openPrice']:
			Trend="Uptrend"
		else:
			Trend="Downtrend"

		#Trend="Uptrend"	
		if(Trend=='Downtrend'):
			no_of_shares= ''
			status=''
			profit=''
			TradePrice = ''
		elif(Trend=='Uptrend'):
			TradePrice = row['closePrice']			
			no_of_shares= math.floor(starting_pool/row['closePrice'])
			status='BUY'

		#output.append([row['tradeTimeInLong'],Date,Time,row['openPrice'],row['highPrice'],row['lowPrice'],row['closePrice'],row['closePrice']*1.03,row['closePrice']*0.98,row['totalVolume'],pred_price,Trend,row['closePrice']*0.98])
		output=[row['Stock'],row['tradeTimeInLong'],date_time,row['openPrice'],row['highPrice'],row['lowPrice'],row['closePrice'],0,0,row['totalVolume'],pred_price,Trend,status,TradePrice,no_of_shares,profit,starting_pool]
		if(log_flag==0):
			append_list_as_row(datajson["files"]["logfile"], column_list)
			append_list_as_row(datajson["files"]["logfile"], output)
		else:
			append_list_as_row(datajson["files"]["logfile"], output)

		if(status=='BUY' or status=='SELL'):
			if(status_flag==0):
				append_list_as_row(datajson['files']['statusfile'],column_list)
				append_list_as_row(datajson['files']['statusfile'],output)
			else:
				append_list_as_row(datajson['files']['statusfile'],output)
		log_flag=1
		status_flag=1