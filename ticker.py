import time
import pyupbit
import pandas as pd
import numpy as np
import datetime as dt
import pyupbit

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
        self.simp_df = None
        
    def __repr__(self):
        return f"<Ticker {self.name}>"

    def __str__(self):
        return f"<Ticker {self.name}>"

    def make_df(self) :
        try :
            # 기초 df (5분봉 100개)
            df = pyupbit.get_ohlcv(self.name, count=100, interval='minute5')
            if  len(df.index) < 100 :
                self.df = None
                return
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma5_asc'] = df['ma5'] - df['ma5'].shift(1)
            conditionlist = [
                            (df['close'] > df['ma5']) & \
                            (df['close'].shift(1) <= df['ma5'].shift(1)) & \
                            (df['close'].shift(2) <= df['ma5'].shift(2)) & \
                            (df['close'].shift(3) <= df['ma5'].shift(3))    ,\
                            (df['close'] < df['ma5']) &\
                            (df['close'].shift(1) >= df['ma5'].shift(1)) &\
                            (df['close'].shift(2) >= df['ma5'].shift(2)) &\
                            (df['close'].shift(3) >= df['ma5'].shift(3)) \
                            ]        
            choicelist1 = ['up', 'down']
            choicelist2 = [df['low'].rolling(5).min(),df['high'].rolling(5).max()]

            df['way'] = np.select(conditionlist, choicelist1, default='')
            df['price'] = np.select(conditionlist, choicelist2, default='')
            df['price'] = df['price'].astype(float, errors='ignore')

            # refine_df  N모형의 꼭지점을 가지는 df 생성
            refine_df = None

            df_copy = df.copy()
            df_copy = df_copy[df_copy['way'] > '']

            if len(df_copy.index) > 0 :
                df_copy = df_copy[::-1]

                refine_df = None
                prev_way = None
                trickery_list =[]
                for row in df_copy.itertuples():
                    if (prev_way is None ) | (prev_way == row.way) :
                        trickery_list.append(row)
                        prev_way = row.way
                    elif prev_way != row.way :
                        if refine_df is None :
                            refine_df = self.process_trickery(trickery_list).copy()
                        else :
                            refine_df = pd.concat([refine_df,self.process_trickery(trickery_list)])
                        trickery_list.clear()
                        trickery_list.append(row)
                        prev_way = row.way

                if  len(trickery_list) > 0 :
                    if refine_df is None :
                        refine_df = self.process_trickery(trickery_list).copy()
                    else :
                        refine_df = pd.concat([refine_df,self.process_trickery(trickery_list)])
                if  len(refine_df.index) > 2 :    
                    refine_df['p_d1'] = refine_df['price'].shift(-1)
                    refine_df['p_d2'] = refine_df['price'].shift(-2)

                    refine_df['p_d1'] = refine_df['p_d1'].astype(float, errors ='ignore')
                    refine_df['p_d2'] = refine_df['p_d2'].astype(float, errors ='ignore')
                    refine_df['price'] = refine_df['price'].astype(float, errors ='ignore')
                    refine_df['attack'] = refine_df.apply( 
                        lambda row : 'good' if (row['way'] == 'up') and (row['price'] > (row['p_d2']*1.003)) else '' ,axis=1)
                else :
                    refine_df = None

            if (df is None) or (refine_df is None) :
                self.df = None
                return False

            # 기초 df 와 refine_df 를 join 한다.
            df = df.drop(['way','price'],axis = 1)
            df['ser'] = pd.Series(np.arange(1,len(df.index)+1,1),index=df.index)
            self.df = df.join(refine_df)

            # 최근 공략가능한 부분위주로 요약된 df 를 생성한다.
            todaystr = dt.datetime.now() - dt.timedelta(minutes=30)  #30분간만 대상
            df = self.df.copy()
            df = df[df.index >= todaystr]
            goodidx = df.index[df['attack']=='good'].tolist()
            if len(goodidx) > 0 :
                self.simp_df = df[df.index >= goodidx[-1]]
                if  (len(self.simp_df.index) == 3) and  \
                    ( 1-( self.simp_df.iloc[0]['price']/self.simp_df.iloc[0]['p_d1']) > 0.015) and \
                    (self.simp_df.iloc[-1]['ma5_asc'] > 0) and \
                    (self.simp_df.iloc[-2]['ma5_asc'] > 0) and \
                    (self.simp_df.iloc[-1]['ma5'] <= self.simp_df.iloc[-1]['low']) and \
                    (self.simp_df.iloc[-2]['ma5'] <= self.simp_df.iloc[-2]['close']) :
                    self.target_price =  self.simp_df.iloc[-1]['ma5']
                else : 
                    self.target_price =  0  
            else :
                self.target_price =  0  

        except TypeError as te :
            print_(self.name,'make_df: te={te}')
            self.df = None
            self.simp_df = None

    def  process_trickery(self,trickery_list) :
        index_list = []
        data_dict = {}    # way, price 두개 요소
        data_dict['way'] = None
        data_dict['price'] = None
        for row in trickery_list:
            if len(index_list) == 0 :
                index_list.append(row.Index)
                data_dict['way'] = row.way
                data_dict['price'] = row.price
                continue
            elif  ( (row.way == 'up') and (row.low < float(data_dict['price']) )) or \
                    ( (row.way == 'down') and (row.high > float(data_dict['price']) )) :
                index_list.clear()
                index_list.append(row.Index)
                data_dict['way'] = row.way
                data_dict['price'] = row.price   
        return pd.DataFrame(data_dict, index=index_list)

if __name__ == "__main__":
    # t  = Ticker('KRW-KNC')
    t  = Ticker('KRW-BTG')
    pd.set_option('display.max_columns', None)
    t.make_df()
    print(t.df.tail(30))

    print(t.simp_df)
    print(t.target_price)
