import time
import pyupbit
import pandas as pd
import numpy as np
import datetime as dt
import pyupbit
import matplotlib.pyplot as plt

def print_(ticker,msg)  :
    if  ticker :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'#'+ticker+'# '+msg
    else :
        ret = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+' '+msg
    print(ret, flush=True)

class Ticker :
    def __init__(self, name) -> None:
        self.name =  name
        self.currency = name[name.find('-')+1:]
        self.fee = 0.0005   #업비트 거래소 매매거래 수수료
        self.df = None
        self.target_price =  0
        self.losscut_price = 0
        self.simp_df = None
        
    def __repr__(self):
        return f"<Ticker {self.name}>"

    def __str__(self):
        return f"<Ticker {self.name}>"

    def make_df(self) :
        try :
            # 기초 df (5분봉 150개)
            self.df = None
            self.target_price =  0  
            self.losscut_price = 0

            df = pyupbit.get_ohlcv(self.name, count=150, interval='minute5')
            if  len(df.index) < 150 :
                return 'Need 150 5minutes-stick'
            df['serial'] = pd.Series(np.arange(1,len(df.index)+1,1),index=df.index)
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()
            df['ma120'] = df['close'].rolling(window=120).mean()
            df['dispa60'] = (df['close'] - df['ma60']) / df['ma60']
            df['max_dispa60'] = df['dispa60'].rolling(window=60).max()
            df['baseline'] = (df['high'].rolling(window=26).max() + df['low'].rolling(window=26).min()) / 2

            conditionlist = [(df['ma10'] < df['ma5']) & \
                            (df['ma10'].shift(1) >= df['ma5'].shift(1)) & \
                            (df['ma10'].shift(2) >= df['ma5'].shift(2)) & \
                            (df['ma10'].shift(3) >= df['ma5'].shift(3))   ,\
                            (df['ma10'] > df['ma5']) & \
                            (df['ma10'].shift(1) <= df['ma5'].shift(1)) &\
                            (df['ma10'].shift(2) <= df['ma5'].shift(2)) &\
                            (df['ma10'].shift(3) <= df['ma5'].shift(3)) \
                            ]        
            choicelist1 = ['golden', 'dead']
            df['way'] = np.select(conditionlist, choicelist1, default='')
            df['dispa60'] = df['dispa60'].astype(float, errors='ignore')
            df['max_dispa60'] = df['max_dispa60'].astype(float, errors='ignore')

            # refine_df  N모형의 꼭지점을 가지는 df 생성
            df_copy = df[df['way'] > '']

            stack_inflection = []  # 변곡점  price, way
            stack_inflection_index = []  # 변곡점 index

            if len(df_copy.index) > 0 :
                for row in df_copy.itertuples():
                    if  len(stack_inflection_index) == 0 :
                        temp = {}
                        temp['pway'] = row.way   
                        temp['price'] = row.close
                        stack_inflection.append(temp)
                        stack_inflection_index.append(row.Index)
                    else :
                        top = stack_inflection.pop()
                        top_index = stack_inflection_index.pop()
                        if row.way == 'golden' :
                            price = df[(df.index > top_index) & (df.index <= row.Index) ]['low'].min()
                            price_date =  df[(df.index > top_index) & (df.index <= row.Index) & (df['low']==price) ].index.min()
                            if  top['pway'] == row.way :
                                if  top['price'] <= price :
                                    price = top['price']
                                    price_date = min(price_date,top_index)
                            else :
                                stack_inflection.append(top)                             
                                stack_inflection_index.append(top_index)    
                        else :
                            price = df[(df.index > top_index) & (df.index <= row.Index) ]['high'].max()
                            price_date =  df[(df.index > top_index) & (df.index <= row.Index) & (df['high']==price) ].index.min()
                            if  top['pway'] == row.way :
                                if  top['price'] >= price :
                                    price = top['price']
                                    price_date = min(price_date,top_index)
                            else :
                                stack_inflection.append(top)                             
                                stack_inflection_index.append(top_index)

                        temp = {}
                        temp['pway'] = row.way
                        temp['price'] = price     
                        stack_inflection.append(temp)
                        stack_inflection_index.append(price_date)

                # print(stack_inflection)
                # print(f'stack_inflection lne= {len(stack_inflection)}')
                # print(stack_inflection_index)
                # print(f'stack_inflection_index len={len(stack_inflection_index)}')
            else :
                return 'Nothing Turning-Point'

            df_refined = pd.DataFrame(stack_inflection, index=stack_inflection_index)
            if  len(df_refined.index) > 3 :    
                df_refined['p_d1'] = df_refined['price'].shift(1)
                df_refined['p_d2'] = df_refined['price'].shift(2)
                df_refined['p_d3'] = df_refined['price'].shift(3)               

                df_refined['p_d1'] = df_refined['p_d1'].astype(float, errors ='ignore')
                df_refined['p_d2'] = df_refined['p_d2'].astype(float, errors ='ignore')
                df_refined['p_d3'] = df_refined['p_d3'].astype(float, errors ='ignore')

                df_refined['price'] = df_refined['price'].astype(float, errors ='ignore')
                df_refined['attack'] = df_refined.apply( 
                    lambda row : 'good' if (row['pway'] == 'golden') and \
                                            (row['price'] > row['p_d2']) and \
                                            (row['p_d1'] * 1.01 < row['p_d3']) else '' ,axis=1)
            else :
                return f'Not enough Turning-Point {len(df_refined.index)}. May not > 3'

            print(df_refined)
            df = df.join(df_refined)
            self.df = df.copy()

            # 최근 공략가능한 부분위주로 요약된 df 를 생성한다.
            todaystr = dt.datetime.now() - dt.timedelta(minutes=90)  #90분간만 대상
            df = df[df.index >= todaystr]
            goodidx = df.index[df['attack']=='good'].tolist()

            if len(goodidx) > 0 :
                self.simp_df = self.df[self.df.index >= goodidx[-1]][::-1]
                pd.set_option('display.max_columns', None)
                print_(self.name,'-------- Simple DataFrame ---------')
                print(self.simp_df,flush=True)
                print_(self.name, f"[idx0:ma60 < ma120] {self.simp_df.iloc[0]['ma60']:,.4f} < {self.simp_df.iloc[0]['ma120']:,.4f}")
                print_(self.name, f"[idx0:p_d1*1.005 < idx0:ma60] {self.simp_df.iloc[0]['p_d1'] * 1.005:,.4f} < {self.simp_df.iloc[0]['ma60']:,.4f}")
                print_(self.name, f"[idx0:close >= idx0:baseline] {self.simp_df.iloc[0]['close']:,.4f}<{self.simp_df.iloc[0]['baseline']:,.2f}")
                print_(self.name, f"[idx1:close >= idx1:baseline] {self.simp_df.iloc[1]['close']:,.4f}<{self.simp_df.iloc[1]['baseline']:,.2f}")
                print_(self.name, f"[idx0:ma5 < idx0:baseline] {self.simp_df.iloc[0]['ma5']:,.2f}<{self.simp_df.iloc[0]['baseline']:,.2f}")
                print_(self.name,'-----------------------------------')

                if  (self.simp_df.iloc[0]['ma60'] < self.simp_df.iloc[0]['ma120'] ) and \
                    (self.simp_df.iloc[0]['p_d1'] * 1.005 < self.simp_df.iloc[0]['ma60'] ) and \
                    (self.simp_df.iloc[0]['close'] >= self.simp_df.iloc[0]['baseline']) and \
                    (self.simp_df.iloc[1]['close'] >= self.simp_df.iloc[1]['baseline'])  :
                    ''' INDEX 0,1,2 순서대로 돌파봉 + 안착봉 + 매수봉, 조건문 순서대로 설명되어 있음
                            돌파봉 50이평의 50일간 최대이격도가 5% 미만 : 최근50봉내에는 50이평을 5%이상 초과하는 고점은 존재 하지 않는다는 의미
                            돌파봉 시가가 50이평선보다 최소 1%이상 낮은 위치에 있을것 (50이평선 맞고 내려오는 경우가 있어서 상승간격을 확보)
                            안착봉의 5이평이 우상향할것
                            매수봉의 5이평이 우상향할것
                            안착봉의 고점이 돌파봉 고점보다 높을것
                            안착봉의 저점이 돌파봉 저점보다 높을것
                            매수봉의 저가가 5이평을 회손하지 않을것
                    '''
                    self.target_price =  self.simp_df.iloc[0]['baseline']
                    self.losscut_price = self.target_price * 0.985
            else :
                return 'Not found good Attack-Point'

        except TypeError as te :
            print_(self.name,'make_df: te={te}')
            self.df = None
            self.simp_df = None
            return 'TypeError'            
        return 'success'

if __name__ == "__main__":
    t  = Ticker('KRW-XRP')
    pd.set_option('display.max_columns', None)
    t.make_df()
    print(t.df.tail(40))
    # t.df.to_excel('a.xlsx')

    fillered_df = t.df[t.df['pway'] > '']
    plt.figure(figsize=(9,5))
    plt.plot(t.df.index, t.df['ma5'], label="MA5")
    plt.plot(t.df.index, t.df['ma10'], label="MA10")
    plt.plot(t.df.index, t.df['ma60'], label="MA60")
    plt.plot(fillered_df.index, fillered_df['price'], label="Price")
    plt.plot(t.df.index, t.df['close'], label="close")
    plt.legend(loc='best')
    plt.grid()
    plt.show()