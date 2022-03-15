import pyupbit
import datetime as dt
import json
import os

access = "Oug97pOTCd6xN12mREWTo9GTQcmkzhMtnoW2Wqyo"          # 본인 값으로 변경
secret = "6IUBTLNU02rSGQux5cIMW11W05WnoW5rRKxxSE6Z"          # 본인 값으로 변경
upbit = pyupbit.Upbit(access, secret)

dict_balances = {}

def print_(ticker,msg)  :
    if  ticker :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'#'+ticker+'# '+msg
    else :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+' '+msg
    print(ret, flush=True)

def init() :
    global dict_balances
    if  os.path.isfile('balances.json') :
        with open('balances.json') as f:
            dict_balances = json.load(f)
    else : 
        data1 = {'currency': 'KRW', 'balance': '1000000', 'avg_buy_price': '0'}
        dict_balances = {'KRW': data1}
        with open('balances.json', 'w') as f:
            json.dump(dict_balances, f)

def get_balance(ticker):
    """잔고 조회(한종목)"""
    try :
        t = dict_balances[ticker]
        return float(t['balance'])
    except KeyError as ke :
        return 0

def get_balances():
    """잔고 조회(보유종목전체)"""
    ret_list = []
    for k,v in dict_balances.items() :
        if k != 'KRW' :
            ret_list.append(v.copy())
    return ret_list

def get_avg_buy_price(ticker):
    """매수평균가"""
    try :
        t = dict_balances[ticker]
        return float(t['avg_buy_price'])
    except KeyError as ke :
        return 0

def  sell_limit_order(ticker,price,amount) :
    print_(ticker,f'sell_limit_order {price:,.4f}, {amount:,.4f}')
    try :
        t = dict_balances[ticker]
        balance =  float(t['balance'])
        t['balance'] = balance + amount
        if balance <= 0 :
            del dict_balances[ticker]
        with open('balances.json', 'w') as f:
            json.dump(dict_balances, f)
    except KeyError as ke :
        print_(ticker,f'sell_limit_order ticker not found {ke}')
    print_('',dict_balances)
    
def  buy_limit_order(ticker,price,amount) :
    print_(ticker,f'buy_limit_order {price:,.4f}, {amount:,.4f}')
    balance = 0.0
    avg_buy_price = 0.0
    try :
        t = dict_balances[ticker]
        balance =  float(t['balance'])
        avg_buy_price =  float(t['avg_buy_price'])
        t['balance'] = balance + amount
        t['avg_buy_price'] = (avg_buy_price + price) / balance
    except KeyError as ke :
        dict_tmp = {}
        dict_tmp['currency'] = ticker
        dict_tmp['balance'] = amount
        dict_tmp['avg_buy_price'] = price
        dict_balances[ticker] = dict_tmp
    with open('balances.json', 'w') as f:
        json.dump(dict_balances, f)
    print_('',dict_balances)

init()

if __name__ == "__main__":
    init()
    print(dict_balances)