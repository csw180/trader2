'''
5분봉 종가가 5이평을 올라서는 순간과 내려가는 순간을 추세전환
시점으로 이용하는 방식
'''
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
            df['ma5_asc'] = df['ma5'] - df['ma5'].shift(1)
            df['ma60'] = df['close'].rolling(window=60).mean()
            df['ma120'] = df['close'].rolling(window=120).mean()

            conditionlist = [(df['close'] > df['ma5']) & \
                            (df['close'].shift(1) <= df['ma5'].shift(1)) & \
                            (df['close'].shift(2) < df['ma5'].shift(2)) & \
                            (df['close'].shift(3) < df['ma5'].shift(3)) ,\
                            (df['close'] < df['ma5']) & \
                            (df['close'].shift(1) >= df['ma5'].shift(1)) &\
                            (df['close'].shift(2) > df['ma5'].shift(2)) &\
                            (df['close'].shift(3) > df['ma5'].shift(3)) \
                            ]        
            choicelist1 = ['up', 'down']
            choicelist2 = [df['low'].rolling(4).min(),df['high'].rolling(4).max()]

            df['way'] = np.select(conditionlist, choicelist1, default=None)
            df['price'] = np.select(conditionlist, choicelist2, default=None)
            df['price'] = df['price'].astype(float, errors='ignore')

            # refine_df  N모형의 꼭지점을 가지는 df 생성
            df_copy = df[df['way'].notnull()]

            stack_inflection = []  # 변곡점  price, way
            stack_inflection_index = []  # 변곡점 index
            if len(df_copy.index) > 0 :
                for row in df_copy.itertuples():
                    if  (len(stack_inflection_index) > 0) and (stack_inflection[-1]['way'] == row.way) :
                        stack_inflection.pop()
                        stack_inflection_index.pop()

                    temp = {}
                    temp['way'] = row.way
                    temp['price'] = row.price
                    stack_inflection.append(temp)
                    stack_inflection_index.append(row.Index) 
            else :
                return 'Nothing Turning-Point'
            df_refined = pd.DataFrame(stack_inflection, index=stack_inflection_index)
            print(df_refined)
            if  len(df_refined.index) > 3 :  
                df_refined['p_d1'] = df_refined['price'].shift(-1)
                df_refined['p_d2'] = df_refined['price'].shift(-2)
                df_refined['p_d3'] = df_refined['price'].shift(-3)               

                df_refined['p_d1'] = df_refined['p_d1'].astype(float, errors ='ignore')
                df_refined['p_d2'] = df_refined['p_d2'].astype(float, errors ='ignore')
                df_refined['p_d3'] = df_refined['p_d3'].astype(float, errors ='ignore')
                df_refined['price'] = df_refined['price'].astype(float, errors ='ignore')
                df_refined['attack'] = df_refined.apply( 
                    lambda row : 'good' if (row['way'] == 'up') and \
                                            (row['price'] > (row['p_d2']*1.005)) and \
                                            (row['p_d1'] * 1.005 < row['p_d3']) else None ,axis=1)
            else :
                return f'Not enough Turning-Point {len(df_refined.index)}. May not > 3'

            # 기초 df 와 refine_df 를 join 한다.
            df = df.drop(['way','price','serial'],axis = 1)
            df = df.join(df_refined)
            df['attack'] = df.apply(
                lambda row : 'good' if  (row['attack']=='good')  and  \
                                        (row['price'] * 1.005 < row['ma60']) and \
                                        (row['ma60']  < row['ma120']) else None, axis=1)
            self.df = df.copy()

            # 최근 공략가능한 부분위주로 요약된 df 를 생성한다.
            todaystr = dt.datetime.now() - dt.timedelta(minutes=30)  #30분간만 대상
            df = self.df.copy()
            df = df[df.index >= todaystr]
            goodidx = df.index[df['attack']=='good'].tolist()

            if len(goodidx) > 0 :
                self.simp_df = df[df.index >= goodidx[-1]][::-1]
                # iloc index 0 : 5일선돌파봉, 1 : 돌파봉의 다음봉, 2 : 돌파봉의 다음다음봉
                if  len(self.simp_df.index) == 3 :
                    pd.set_option('display.max_columns', None)
                    print_(self.name,'-------- Simple DataFrame ---------')
                    print(self.simp_df,flush=True)
                    print_(self.name, f"[idx1,idx2:ma5_asc] {self.simp_df.iloc[1]['ma5_asc']:,.4f},{self.simp_df.iloc[2]['ma5_asc']:,.4f}")
                    print_(self.name, f"[idx0:high < idx1:high] {self.simp_df.iloc[0]['high']:,.2f}<{self.simp_df.iloc[1]['high']:,.2f}")
                    print_(self.name, f"[idx0:low < idx1:low] {self.simp_df.iloc[0]['low']:,.2f}<{self.simp_df.iloc[1]['low']:,.2f}")
                    print_(self.name, f"[idx2:ma5 < idx2:low] {self.simp_df.iloc[2]['ma5']:,.4f}<{self.simp_df.iloc[2]['low']:,.2f}")
                    print_(self.name,'-----------------------------------')
                else :
                    return f'Already or Yet! len(simp_df)={len(self.simp_df.index)} Maybe not 3'

                if  (len(self.simp_df.index) == 3) and \
                    (self.simp_df.iloc[1]['ma5_asc'] > 0) and \
                    (self.simp_df.iloc[2]['ma5_asc'] > 0) and \
                    (self.simp_df.iloc[0]['high'] < self.simp_df.iloc[1]['high']) and \
                    (self.simp_df.iloc[0]['low']  < self.simp_df.iloc[1]['low']) and \
                    (self.simp_df.iloc[2]['ma5'] < self.simp_df.iloc[2]['low']) :
                        self.target_price =  self.simp_df.iloc[2]['ma5']
                        self.losscut_price = self.simp_df.iloc[0]['price']
                else :
                    return f'Detail condition not suitable'
            else :
                return 'Not found good Attack-Point'
        except TypeError as te :
            print_(self.name,'make_df: te={te}')
            self.df = None
            self.simp_df = None
            return 'TypeError'
        return 'success'

if __name__ == "__main__":
    t  = Ticker('KRW-NEAR')
    pd.set_option('display.max_columns', None)
    t.make_df()
    # print(t.df.tail(40))
    # t.df.to_excel('a.xlsx')

    fillered_df = t.df[t.df['way'].notnull()]
    print(fillered_df.tail(40))
    plt.figure(figsize=(9,5))
    plt.plot(t.df.index, t.df['ma5'], label="MA5")
    plt.plot(t.df.index, t.df['ma60'], label="MA60")
    plt.plot(fillered_df.index, fillered_df['price'], label="Price")
    plt.plot(t.df.index, t.df['close'], label="close")
    plt.legend(loc='best')
    plt.grid()
    plt.show()