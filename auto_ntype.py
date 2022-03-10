import time
import pyupbit
import pandas as pd
import datetime as dt
from ticker import Ticker
import upbit_trade

def print_(ticker,msg)  :
    if  ticker :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'#'+ticker+'# '+msg
    else :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+' '+msg
    print(ret, flush=True)

# 거래량 상위 10개 종목 선별
def best_volume_tickers() : 
    all_tickers = pyupbit.get_tickers(fiat="KRW")
    all_tickers_prices = pyupbit.get_current_price(all_tickers)
    all_tickers_value = {}

    # 각 종목의 거래대금을 조사한다.
    for k, v in all_tickers_prices.items() :
        if  v < 90000 :   # 단가가 9만원 미만인 것만...
            df = pyupbit.get_ohlcv(k, count=3, interval='minute60')  #60분봉 3개의 거래대금
            time.sleep(0.5)
            if len(df.index) > 0 :
                all_tickers_value[k] = df['value'].sum()

    # 거래대금 top 10 에 해당하는 종목만 걸러낸다
    sorted_list = sorted(all_tickers_value.items(), key=lambda x : x[1], reverse=True)[:10]
    top_tickers = [e[0] for e in sorted_list]
    tickers = []
    for  t in  top_tickers :
        tickers.append(Ticker(t))
    return tickers

print_('',f"Autotrader(Ntype) init.. ")
tickers = best_volume_tickers()
print_('',f"best_volume_tickers finished.. count={len(tickers)} tickers={tickers}")

current_time = dt.datetime.now()
next_time = current_time + dt.timedelta(hours=6)

loop_cnt = 0
print_loop = 20
# 자동매매 시작
while  True :
    loop_cnt +=1
    try : 
        current_time = dt.datetime.now()
        if  current_time > next_time :  # 주기적으로 거래량top10 종목들 재갱신
            next_time = current_time + dt.timedelta(hours=6)
            tickers = best_volume_tickers()
            print_('',f"best_volume_tickers finished.. count={len(tickers)} tickers={tickers}")
            continue

        if  loop_cnt >= print_loop + 1 :   # 운영모드로 가면 충분히 크게 바꿀것..
            loop_cnt = 0

        for t in  tickers :  
            # 이미 잔고가 있는 종목은 목표가에 왔는지 확인하고 즉시 매도 처리 한다.
            btc=upbit_trade.get_balance(t.currency)
            if  btc > 0 :
                current_price = float(pyupbit.get_orderbook(ticker=t.name)["orderbook_units"][0]["bid_price"])
                avg_buy_price = upbit_trade.get_avg_buy_price(t.currency)
                if  loop_cnt >= print_loop :
                    print_(t.name,f'sell_balance(btc):{btc}, avg:p-cut:l-cut = {avg_buy_price:.2f}:{avg_buy_price*1.015:.2f}:{avg_buy_price*0.985:.2f}, curr_price= {current_price:.2f}')
                if  ( current_price > avg_buy_price * 1.015 ) or \
                    ( current_price < avg_buy_price * 0.985 ) :
                    upbit_trade.sell_limit_order(t.name, current_price, btc )
                continue

            t.make_df()
            if t.target_price > 0 :
                pd.set_option('display.max_columns', None)
                print_(t.name,'-------- Simple DataFrame ---------')
                print(t.simp_df,flush=True)
                print_(t.name,'-----------------------------------')
            
            if t.target_price > 0 :
                trys = 40
                while trys > 0 :
                    trys -= 1
                    current_price = float(pyupbit.get_orderbook(ticker=t.name)["orderbook_units"][0]["ask_price"]) 
                    print_(t.name,f'buy_{trys}: Target:TP*1.005={t.target_price:.2f}:{t.target_price*1.005:.2f}, curr_price={current_price:.2f}')
                    if t.target_price * 1.005 > current_price:
                        krw = upbit_trade.get_balance("KRW")
                        print_(t.name,f'buy_get_balance(KRW): {krw:.2f} limit:{(100000 if krw >= 100000 else krw):.2f}')
                        if krw > 5000:
                            upbit_trade.buy_limit_order(t.name, current_price, ((100000 if krw >= 100000 else krw) * 0.999)//current_price )
                            continue
                    time.sleep(1)
            time.sleep(1)

    except Exception as e:
        print_('',f'{e}')
        time.sleep(1)