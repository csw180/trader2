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
            df['vma5'] = df['value'].rolling(window=5).mean()

            df['ma50'] = df['close'].rolling(window=50).mean()
            df['dispa50'] = (df['close'] - df['ma50']) / df['ma50']
            df['max_dispa50'] = df['dispa50'].rolling(window=50).max()

            conditionlist = [
                            ((df['low']+df['high'])/2 > df['ma5']) & \
                            ((df['low'].shift(1) + df['high'].shift(1))/2 <= df['ma5'].shift(1)) & \
                            ((df['low'].shift(2) + df['high'].shift(2))/2 <= df['ma5'].shift(2)) & \
                            ((df['low'].shift(3) + df['high'].shift(3))/2 <= df['ma5'].shift(3))   ,\
                            ((df['low']+df['high'])/2 < df['ma5']) &\
                            ((df['low'].shift(1) + df['high'].shift(1))/2 >= df['ma5'].shift(1)) &\
                            ((df['low'].shift(2) + df['high'].shift(2))/2 >= df['ma5'].shift(2)) &\
                            ((df['low'].shift(3) + df['high'].shift(3))/2 >= df['ma5'].shift(3)) \
                            ]        
            choicelist1 = ['up', 'down']
            choicelist2 = [df['low'].rolling(4).min(),df['high'].rolling(4).max()]

            df['way'] = np.select(conditionlist, choicelist1, default='')
            df['price'] = np.select(conditionlist, choicelist2, default='')
            df['price'] = df['price'].astype(float, errors='ignore')
            df['vma5'] = df['vma5'].astype(float, errors='ignore')
            df['dispa50'] = df['dispa50'].astype(float, errors='ignore')
            df['max_dispa50'] = df['max_dispa50'].astype(float, errors='ignore')

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
                if  len(refine_df.index) > 3 :    
                    refine_df['p_d1'] = refine_df['price'].shift(-1)
                    refine_df['p_d1_ser'] = refine_df['serial'].shift(-1)
                    refine_df['p_d2'] = refine_df['price'].shift(-2)
                    refine_df['p_d2_ser'] = refine_df['serial'].shift(-2)
                    refine_df['p_d3'] = refine_df['price'].shift(-3)               

                    refine_df['p_d1'] = refine_df['p_d1'].astype(float, errors ='ignore')
                    refine_df['p_d2'] = refine_df['p_d2'].astype(float, errors ='ignore')
                    refine_df['p_d3'] = refine_df['p_d3'].astype(float, errors ='ignore')

                    refine_df['p_d1_ser'] = refine_df['p_d1_ser'].astype(float, errors ='ignore')
                    refine_df['p_d2_ser'] = refine_df['p_d2_ser'].astype(float, errors ='ignore')
                    refine_df['price'] = refine_df['price'].astype(float, errors ='ignore')
                    refine_df['attack'] = refine_df.apply( 
                        lambda row : 'good' if (row['way'] == 'up') and \
                                               (row['price'] > (row['p_d2']*1.005)) and \
                                               (row['p_d1'] * 1.005 < row['p_d3']) else '' ,axis=1)
                else :
                    return f'Not enough Turning-Point {len(refine_df.index)}. May not > 3'
            else :
                return 'Nothing Turning-Point'

            # 기초 df 와 refine_df 를 join 한다.
            df = df.drop(['way','price','serial'],axis = 1)
            self.df = df.join(refine_df)

            # 최근 공략가능한 부분위주로 요약된 df 를 생성한다.
            todaystr = dt.datetime.now() - dt.timedelta(minutes=30)  #30분간만 대상
            df = self.df.copy()
            df = df[df.index >= todaystr]
            goodidx = df.index[df['attack']=='good'].tolist()

            if len(goodidx) > 0 :
                self.simp_df = df[df.index >= goodidx[-1]]
                # iloc index 0 : 5일선돌파봉, 1 : 돌파봉의 다음봉, 2 : 돌파봉의 다음다음봉
                if  len(self.simp_df.index) == 3 :
                    pd.set_option('display.max_columns', None)
                    print_(self.name,'-------- Simple DataFrame ---------')
                    print(self.simp_df,flush=True)
                    print_(self.name,'-----------------------------------')

                if  (len(self.simp_df.index) == 3) and \
                    (self.simp_df.iloc[0]['max_dispa50'] * 100 <= 5.0 ) and \
                    (self.simp_df.iloc[0]['open'] * 1.01 < self.simp_df.iloc[0]['ma50'] ) and \
                    (self.simp_df.iloc[1]['ma5_asc'] > 0) and \
                    (self.simp_df.iloc[2]['ma5_asc'] > 0) and \
                    (self.simp_df.iloc[0]['high'] < self.simp_df.iloc[1]['high']) and \
                    (self.simp_df.iloc[0]['low']  < self.simp_df.iloc[1]['low']) and \
                    (self.simp_df.iloc[2]['ma5'] < self.simp_df.iloc[2]['low']) :
                    ''' INDEX 0,1,2 순서대로 돌파봉 + 안착봉 + 매수봉, 조건문 순서대로 설명되어 있음
                            돌파봉 50이평의 50일간 최대이격도가 5% 미만 : 최근50봉은 최소한 50일선 밑에서 놀았다는 뜻
                            돌파봉 시가가 50이평선보다 최소 1%이상 낮은 위치에 있을것 (50이평선 맞고 내려오는 경우가 있어서 상승간격을 확보)
                            안착봉의 5이평이 우상향할것
                            매수봉의 5이평이 우상향할것
                            안착봉의 고점이 돌파봉 고점보다 높을것
                            안착봉의 저점이 돌파봉 저점보다 높을것
                            매수봉의 저가가 5이평을 회손하지 않을것
                    '''
                    from_serial, to_serial  = self.simp_df.iloc[0]['p_d2_ser'], self.simp_df.iloc[0]['p_d1_ser']
                    now_serial = self.simp_df.iloc[0]['serial']
                    print_(self.name,f'from_serial={from_serial}, to_serial={to_serial}, now_serial={now_serial}')
                    val_fromIdx, val_toIdx, val_nowIdx = self.df[self.df['serial']==from_serial].index.tolist(), \
                                    self.df[self.df['serial']==to_serial].index.tolist(), \
                                    self.df[self.df['serial']==now_serial].index.tolist()
                    print_(self.name,f'val_fromIdx={val_fromIdx[0]}, val_toIdx={val_toIdx[0]}, val_nowIdx={val_nowIdx[0]}')

                    k1 = self.df[(val_fromIdx[0] <= self.df.index) & (self.df.index < val_toIdx[0])]['value'].sum()
                    k2 = self.df[(val_toIdx[0] <= self.df.index) & (self.df.index <= val_nowIdx[0])]['value'].sum()
                    k3 = self.simp_df.iloc[0]['vma5']
                    d1,d2 = to_serial - from_serial, now_serial - to_serial + 1
                    v1 = k1/d1/k3*100.0
                    v2 = k2/d2/k3*100.0
                    print_(self.name,f'Value  Asc course:{k1:,.2f}/{d1}={v1:,.2f}% Desc course:{k2:,.2f}/{d2}={v2:,.2f}%')
                    if  d1 < 15 :
                        ''' 하락후 반등구간이 15봉 이내, 반등구간이 길어지면 이 전략의 정확도가 떨어진다.'''
                        self.target_price =  self.simp_df.iloc[2]['ma5']
                        self.losscut_price = self.simp_df.iloc[0]['price']
                    else :
                        return f'Ascending stick {d1} Maybe not < 15'
                else :
                    return f'Already or Yet! len(simp_df)={len(self.simp_df.index)} Maybe not 3'
            else :
                return 'Not found good Attack-Point'
        except TypeError as te :
            print_(self.name,'make_df: te={te}')
            self.df = None
            self.simp_df = None
            return 'TypeError'
        return 'success'

    def  process_trickery(self,trickery_list) :
        index_list = []
        data_dict = {}    # way, price 두개 요소
        data_dict['way'] = None
        data_dict['price'] = None
        data_dict['serial'] = None
        for row in trickery_list:
            if len(index_list) == 0 :
                index_list.append(row.Index)
                data_dict['way'] = row.way
                data_dict['price'] = row.price
                data_dict['serial'] = row.serial
                continue
            elif  ( (row.way == 'up') and (row.low < float(data_dict['price']) )) or \
                    ( (row.way == 'down') and (row.high > float(data_dict['price']) )) :
                index_list.clear()
                index_list.append(row.Index)
                data_dict['way'] = row.way
                data_dict['price'] = row.price
                data_dict['serial'] = row.serial
        return pd.DataFrame(data_dict, index=index_list)

if __name__ == "__main__":
    t  = Ticker('KRW-ZIL')
    pd.set_option('display.max_columns', None)
    t.make_df()
    print(t.df.tail(40))
    # t.df.to_excel('a.xlsx')

    # val_fromIdx, val_toIdx = t.df[t.df['serial']==92].index.tolist(), \
    #     t.df[t.df['serial']==96].index.tolist()
    # # print(val_fromIdx[0].strftime('%m/%d/%Y, %r'),val_toIdx[0].strftime('%m/%d/%Y, %r'))
    # print(len(val_fromIdx),len(val_toIdx))
    # val_nowIdx = t.simp_df.iloc[0].index
    # k1 = t.df[(val_fromIdx <= t.df.index) & (t.df.index < val_toIdx)]['value'].sum()
    # k1 = t.df[val_fromIdx : val_toIdx]['value'].sum()

    # print(k1)

    # k2 = self.df[(val_toIdx <= self.df.index) & (self.df.index <= val_nowIdx)]['value'].sum()
    # k3 = self.simp_df.iloc[0]['vma5']
    # d1,d2 = self.simp_df.iloc[0]['p_d1_ser'] - self.simp_df.iloc[0]['p_d2_ser'],  \
    #         self.simp_df.iloc[0]['serial'] - self.simp_df.iloc[0]['p_d1_ser'] + 1
    # v1 = k1/d1/k3*100.0
    # v2 = k2/d2/k3*100.0

    # t.df.to_excel('a.xlsx')
    # x_df = t.df[t.df['way'] > '']
    # # 표 그리기
    # val_fromIdx, val_toIdx = t.simp_df.iloc[0]['p_d2_ser'], t.simp_df.iloc[0]['p_d1_ser']
    # k1 = t.df[(80 <= t.df['serial']) & (t.df['serial'] < 92)]['value'].sum()
    # print(k1)

    fillered_df = t.df[t.df['way'] > '']
    plt.figure(figsize=(9,5))
    plt.plot(t.df.index, t.df['ma5'], label="MA5")
    plt.plot(t.df.index, t.df['ma50'], label="MA50")
    plt.plot(fillered_df.index, fillered_df['price'], label="Price")
    plt.plot(t.df.index, t.df['close'], label="close")
    plt.legend(loc='best')
    plt.grid()
    plt.show()