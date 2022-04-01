import datetime as dt
import json
import os
import pyupbit

_UPBIT_ENABLE = False

dict_balances = {}
access = "Oug97pOTCd6xN12mREWTo9GTQcmkzhMtnoW2Wqyo"          # 본인 값으로 변경
secret = "6IUBTLNU02rSGQux5cIMW11W05WnoW5rRKxxSE6Z"          # 본인 값으로 변경
upbit = None

if  _UPBIT_ENABLE :
    upbit = pyupbit.Upbit(access, secret)

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
        history = []
        dict_balances = {'KRW': data1,'history':history}
        with open('balances.json', 'w') as f:
            json.dump(dict_balances, f)

def get_balance(currency):
    """잔고 조회(한종목)"""
    try :
        t = dict_balances[currency]
        return float(t['balance'])
    except KeyError as ke :
        return 0

def get_balances():
    """잔고 조회(보유종목전체)"""
    ret_list = []
    for k,v in dict_balances.items() :
        if (k != 'KRW')  and (k != 'history'):
            ret_list.append(v.copy())
    return ret_list

def get_tot_buy_price() :
    ret = 0 
    for k,v in dict_balances.items() :
        if (k != 'KRW')  and (k != 'history'):
            ret = ret + (v['balance']*v['avg_buy_price'])
    return ret

def get_avg_buy_price(currency):
    """매수평균가"""
    try :
        t = dict_balances[currency]
        return float(t['avg_buy_price'])
    except KeyError as ke :
        return 0

def  sell_limit_order(ticker,price,amount) :
    print_(ticker,f'sell_limit_order {price:,.4f}, {amount:,.4f}')
    currency = ticker[ticker.find('-')+1:]
    try :
        t = dict_balances[currency]
        balance =  float(t['balance'])
        t['balance'] = balance - amount

        if  _UPBIT_ENABLE :
            ret = upbit.sell_limit_order(ticker, price, amount)
            print_(ticker,f'upbit sell_limit_order {price:,.4f}, {amount:,.4f}')
            print_(ticker,f'upbit sell_limit_order ret = {ret}')

        historys = dict_balances['history']
        history = []
        history.append(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        history.append('SELL')
        history.append(currency)
        history.append(amount)
        history.append(price)
        historys.append(history)
        dict_balances['history'] = historys

        if (balance - amount) <= 0 :
            del dict_balances[currency]
        
        t = dict_balances['KRW']
        balance =  float(t['balance'])
        t['balance'] = balance + (price * amount)

        with open('balances.json', 'w') as f:
            json.dump(dict_balances, f)
    except KeyError as ke :
        print_(ticker,f'sell_limit_order ticker not found {ke}')
    
def  buy_limit_order(ticker,price,amount) :
    print_(ticker,f'buy_limit_order {price:,.4f}, {amount:,.4f}')
    currency = ticker[ticker.find('-')+1:]
    try :
        t = dict_balances[currency]
        balance =  float(t['balance'])
        avg_buy_price =  float(t['avg_buy_price'])
        t['balance'] = balance + amount
        t['avg_buy_price'] = (avg_buy_price + price) / balance
    except KeyError as ke :
        dict_tmp = {}
        dict_tmp['currency'] = currency
        dict_tmp['balance'] = amount
        dict_tmp['avg_buy_price'] = price
        dict_balances[currency] = dict_tmp
    
    if  _UPBIT_ENABLE :
        ret = upbit.buy_limit_order(ticker, price, amount )
        print_(ticker,f'upbit buy_limit_order {price:,.4f}, {amount:,.4f}')
        print_(ticker,f'upbit buy_limit_order ret = {ret}')

    historys = dict_balances['history']
    history = []
    history.append(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    history.append('BUY')
    history.append(currency)
    history.append(amount)
    history.append(price)
    historys.append(history)
    dict_balances['history'] = historys

    t = dict_balances['KRW']
    balance =  float(t['balance'])
    t['balance'] = balance - (price * amount)

    with open('balances.json', 'w') as f:
        json.dump(dict_balances, f)

init()

if __name__ == "__main__":
    init()
    tot = get_tot_buy_price()
    print('%d' % tot)