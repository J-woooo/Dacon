# -*- coding: utf-8 -*-
"""kingsolarbeam.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11Ts8q1HF7PfFeZPNgfGUL_iW8IKKE732
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
from numpy import concatenate
import pandas as pd
import tensorflow as tf
import keras
import math
import seaborn as sns
from scipy.optimize import curve_fit
from keras.models import Sequential
from keras.layers import Dense, LSTM, Dropout
from keras.layers import Flatten
from keras.layers import RepeatVector
from keras.layers import TimeDistributed
from keras.layers import ConvLSTM2D
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
# %matplotlib inline

solar_data = pd.read_csv('./data/train/train.csv',encoding='utf-8')

corrList = []
corr = lambda p : p['TARGET'].corr(p['GHI'])

def makeCorrList(df):
    result = corr(df)
    corrList.append(result)

for i in range(0,90):
    solar_data['GHI'] = solar_data['DNI']*math.cos(math.pi/180*i)+solar_data['DHI']
    makeCorrList(solar_data)

x = np.arange(0,90)
plt.plot(x,corrList)
plt.show()

print(corrList.index(max(corrList)), max(corrList))

solar_data['GHI'] = solar_data['DNI']*math.cos(math.pi/180*63)+solar_data['DHI']

def eval_dewpoint(T, RH):
    b = 17.62
    c = 243.12
    gamma = (b * T / (c + T)) + math.log(RH / 100.0)
    dewpoint = (c * gamma) / (b - gamma)
    return dewpoint

for i in range(len(solar_data)):
    solar_data.loc[i, ["DP"]] = eval_dewpoint(float(solar_data.loc[i, ["T"]]), solar_data.loc[i , ["RH"]])

solar_data = solar_data.reindex(columns=["Day", "Hour", "Minute", "GHI", "DHI", "DNI", "WS", "RH", "T", "DP", "TARGET"])

mask = (solar_data.Hour==12)&(solar_data.Minute==00)
# solar_data_filtered = solar_data.loc[mask,:]
# solar_data_filtered.drop(['Day', 'Hour','Minute'], axis='columns', inplace=True)
plt.figure(figsize=(7, 7))
# sns.heatmap(data=solar_data_filtered.corr(), annot=True,fmt='.2f', linewidths=.5, cmap='Blues')
sns.heatmap(data=solar_data.corr(), annot=True,fmt='.2f', linewidths=.5, cmap='Blues')
plt.rcParams['font.family'] = 'NanumGothic'

solar_data.drop(['Day', 'Hour','Minute'], axis='columns', inplace=True)

class CustomHistory(keras.callbacks.Callback):
    def init(self):
        self.train_loss = []
        self.val_loss = []
        
    def on_epoch_end(self, batch, logs={}):
        self.train_loss.append(logs.get('loss'))
        self.val_loss.append(logs.get('val_loss'))

def create_dataset(solar_data, index):
    dataX, dataY = [], []
    for i in range(0,48*7):
        dataX.append(list(np.array(solar_data.loc[index+i].tolist())))
    for i in range(48*7,48*7+48*2):
        dataY.append(solar_data.loc[index+i,'TARGET'])
    return np.array(dataX), np.array(dataY)

# 데이터셋 생성
input_data, output_data = [], []

last_index = 3*365*48-48*9
list_index = list(range(0,last_index,48))

# last_index = 3*365*48 - 432
# list_index = list(0:last_index,1))

for i in list_index:
    X, Y = create_dataset(solar_data,i)
    input_data.append(X)
    output_data.append(Y)

input_array = np.array(input_data)
output_array = np.reshape(np.array(output_data),(1086,96,1))

# 데이터셋 분배
train_x, test_x, train_y, test_y = train_test_split(input_array, output_array, test_size = 78/1086,shuffle = False)
train_x, val_x, train_y, val_y = train_test_split(train_x, train_y, test_size=48*3/1008,shuffle=False)

# x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1],1))
# train_x = train_x.reshape((train_x.shape[0], 7, 1, 48, 6))

# 돌려!

import keras.backend as K


submission = pd.read_csv('./data/sample_submission.csv')
submission.set_index('id',inplace=False)
test = []
for i in range(81):
    data = []
    tmp = pd.read_csv(f'./data/test/{i}.csv')
    tmp.drop(['Day', 'Hour','Minute'], axis='columns', inplace=True)
    for i in range(0,48*7):
        data.append(list(np.array(solar_data.loc[i].tolist())))
    test.append(data)
test = np.array(test)

def tilted_loss(q,y,f):
    e = (y-f)
    return K.mean(K.maximum(q*e, (q-1)*e), axis=-1)
callback = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=5)

n_batch = 8

for i, q in enumerate(np.arange(0.1, 1, 0.1)):
  print(q)
  model = Sequential()
  # for l in range(2):
  #     model.add(LSTM(32, batch_input_shape=(8, 336, 8), stateful=True, return_sequences=True))
  #     model.add(Dropout(0.3))
  model.add(LSTM(32, batch_input_shape=(n_batch, 336, 8), stateful=True))
  model.add(Dropout(0.3))
  model.add(Dense(96))
  model.compile(loss=lambda y,f: tilted_loss(q,y,f), optimizer='adagrad')
  # for j in range(200):
  #   # model.fit(train_x, train_y, epochs=1, batch_size=1, shuffle=False, callbacks=[custom_hist], validation_data=(val_x, val_y))
  #   model.fit(train_x, train_y, epochs=1, batch_size=1, shuffle=False, validation_data=(val_x, val_y))
  # #   model.reset_states()
  model.fit(train_x, train_y, epochs=100, batch_size=n_batch, shuffle=False, validation_data=(val_x, val_y), callbacks=[callback], verbose=2)
  predictions = []
  for k in range(81):
    prediction = model.predict(np.array([test[k]]), batch_size=1)
    predictions.append(prediction)
  predictions = np.reshape(np.concatenate(np.array(predictions), axis=0),(81*96))
  submission.iloc[:,i+1] = predictions
submission.to_csv(f'submission.csv', index=False)
print('finish')

