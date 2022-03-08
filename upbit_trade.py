import pyupbit
import datetime as dt

access = "Oug97pOTCd6xN12mREWTo9GTQcmkzhMtnoW2Wqyo"          # 본인 값으로 변경
secret = "6IUBTLNU02rSGQux5cIMW11W05WnoW5rRKxxSE6Z"          # 본인 값으로 변경
upbit = pyupbit.Upbit(access, secret)

def print_(ticker,msg)  :
    if  ticker :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'#'+ticker+'# '+msg
    else :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+' '+msg
    print(ret, flush=True)

def get_balance(ticker):
    """잔고 조회(한종목)"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_balances():
    """잔고 조회(보유종목전체)"""
    ret_list = []
    tmp_dict = {}
    balances = upbit.get_balances()
    for b in balances:
        tmp_dict.clear()
        if b['balance'] is not None and not (b['currency'] == 'KRW') :
            tmp_dict['currency'] = b['currency']
            tmp_dict['balance'] = b['balance']
            tmp_dict['avg_buy_price'] = b['avg_buy_price']
            ret_list.append(tmp_dict)
    return ret_list

def get_avg_buy_price(ticker):
    """매수평균가"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['avg_buy_price'] is not None:
                return float(b['avg_buy_price'])
            else:
                return 0
    return 0

def  sell_limit_order(ticker,price,amount) :
    ret = upbit.sell_limit_order(ticker, price, amount)
    print(ticker,f'sell_limit_order {price:.2f}, {amount:.2f}')
    print(ticker,f'sell_limit_order ret = {ret}')

def  buy_limit_order(ticker,price,amount) :
    ret = upbit.buy_limit_order(ticker, price, amount )
    print_(ticker,f'buy_limit_order {price:.2f}, {amount:.2f}')
    print_(ticker,f'buy_limit_order ret = {ret}')

if __name__ == "__main__":
    pass