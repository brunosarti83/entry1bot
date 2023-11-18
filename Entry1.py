from datetime import datetime, timedelta
from time import sleep
import telegram
from telegram import send_telegram
import pandas as pd
import config_futures #importo el archivo de las claves, es el config.py que está en el mismo directorio
from binance.client import Client
from Binance_futures import *
from Binance_futures import precio
import sys, os

client = Client(config_futures.API_KEY, config_futures.API_SECRET)
xvelas = 20
daysback = 8
sl = 0.01
tp = 0.06
EMA = 200
activo = 'ETHUSDT'
interval = '2h'


def price(activo):
    prices = client.futures_symbol_ticker()
    for i in range(len(prices)):
        if activo == prices[i]['symbol']:
            price = prices[i]['price']
    return price
#defino una función para leer el json de la cartera
def read_cartera():

    import json         # import the json library
    with open("cartera.json", "r") as f:      # read the json file
        variables = json.load(f)
    
    posicion = variables["posicion"]
    cant_inic = variables["cant_inic"]    # To get the value currently stored
    cantidad = variables['cantidad']
    resto = variables['resto']
    profit_loss = variables['profit_loss']
    precio_apertura = variables['precio_apertura']
    stop_value = variables['stop_value']

    return  posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value
#defino una función para editar el json de la cartera
def modify_cartera(posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value):

    import json         # import the json library
    with open("cartera.json", "r") as f:      # write the json file
        variables = json.load(f)
        
        variables["cant_inic"] = cant_inic    # To get the value currently stored
        variables["posicion"] = posicion
        variables['cantidad'] = cantidad
        variables['resto'] = resto
        variables['profit_loss'] = profit_loss
        variables['precio_apertura'] = precio_apertura
        variables['stop_value'] = stop_value
    with open("cartera.json", "w") as f:      # write the json file  
        variables = json.dump(variables,f)
    return posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura,stop_value
#tomo las variables de la cartera archivo cartera.json que está en el mismo directorio


def candles(symbol,contractType = 'PERPETUAL', interval =interval ,startTime = None,endTime=None, limit=300): 
    candles=client.futures_klines(symbol='ETHUSDT',contractType = contractType,interval=interval,limit=limit)
    cols = ['openTime', 'Open', 'High', 'Low', 'Close', 'Volume', 'cTime', 'qVolume', 'trades', 'takerBase', 'takerQuote', 'Ignore']
    df = pd.DataFrame(candles, columns = cols)
    #convierto los strings a números
    df = df.apply(pd.to_numeric)
    #le mando índice de timestamp
    df.index = pd.to_datetime(df.openTime, unit = 'ms')
    #elimino columnas que no quiero
    df = df.drop(['openTime','cTime','takerBase','takerQuote','Ignore','qVolume','trades'],axis = 1)
    return df
send_telegram("Starting")

while True:
    try: #tomo los datos de la cartera
        posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value = read_cartera() 
            
        now = datetime.utcnow()
        num = now.hour
        if (num % 2) == 0:
            hour = 2 
        else:
            hour = 1

        to = (now + timedelta(hours = hour)).replace(minute=0, second=0)
        sleep((to-now).seconds+1)
        
        #ahora ejecuto el script al cierre de la vela de 2h
        precio = price(activo)
        send_telegram('Precio '+str(activo[:3])+': '+str(round(float(precio),2))+' USDT')
        data = candles(activo)
        data['rrange'] = data['High']-data['Low']
        data['ref_rrange'] = data['rrange'].rolling(xvelas).mean()+ 2*data['rrange'].rolling(xvelas).std()
        data['max_close'] = data['Close'].rolling(daysback).max()
        data['min_close'] = data['Close'].rolling(daysback).min()
        data['EMA'] = data['Close'].ewm(span = EMA, adjust = False).mean()

        #determina la fecha_hora_cierre de la vela en cuestión
        ahora = datetime.utcnow()
        h = ahora.hour
        d = ahora.day
        m = ahora.month
        y = ahora.year
        if h == 0:
            h_aj = 22
        else:
            h_aj = h-2
        fh_cierre = pd.DataFrame(data.iloc[-2]).transpose().last_valid_index().replace(hour = h_aj)
        if (ahora - fh_cierre) > timedelta(hours = 3):
            fh_cierre = fh_cierre.replace(day = d, month = m, year = y)


        
        #exporto data a un csv para log
        try:    
            data.to_csv(r'data_log.csv', index = True, header=True)
            #send_telegram('CSV exportado')
        except:
            send_telegram('CSV no se pudo exportar')
        send_telegram(str(fh_cierre))
        
        #corro el trigger de señales    
        if posicion == 'COMPRADO':
            if (data.loc[fh_cierre,'rrange'] > data.loc[fh_cierre,'ref_rrange'] and data.loc[fh_cierre,'Close']==data.loc[fh_cierre,'min_close']) or (data.loc[fh_cierre,'Close'] < stop_value) or (data.loc[fh_cierre,'Close'] > float(precio_apertura)*(1+tp)):
                send_telegram('CERRAR LONG')
                #print('CERRAR LONG DE' +str(cantidad) + ' USDT de ETHUSDT PERPETUAL')#EJECUTAR CIERRE DEL LONG
                close_long_output, qtty, avg_price = close_long(activo,cantidad,precio_apertura)
                posicion = 'LIQUIDO'
                precio_cierre=float(avg_price)
                resultado = round(((precio_cierre/float(precio_apertura)) -1)*100,2) 
                cantidad = float(qtty) + float(resto)
                send_telegram('P/L OPERACIÓN: ' + str(resultado) + '%') 
                resto = 0
                stop_value = 0
                precio_apertura = 0
                profit_loss = round((float(cantidad)/float(cant_inic)-1)*100,2)
                posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value = modify_cartera(posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value)      
                #send_telegram de cartera:
                cartera_msg = 'POSICIÓN: ' +str(posicion) + '\nCANT. INICIAL: ' + str(cant_inic)+' USDT \nCANT. ACTUAL: ' +str(round(cantidad,2))+' USDT\nRESTO: '+str(round(resto,2))+' USDT\nPROFIT/LOSS: '+str(round(profit_loss,2))+'%'
                send_telegram(cartera_msg)
                #cant = cantidad operada, sacar de la operación
            else:
                profit_loss_abs, profit_loss = position(activo)
                profit_loss_acum = round(100*(((float(precio_apertura) * float(cantidad) + float(resto))/float(cant_inic))*(1+(float(profit_loss)/100))-1),2)
                send_telegram('P/L OPERACIÓN (PARCIAL): ' + str(profit_loss) + '%')
                cartera_msg = 'POSICIÓN: ' +str(posicion) + '\nCANT. INICIAL: ' + str(cant_inic)+' USDT \nCANT. ACTUAL: ' +str(round(cantidad,2))+' '+str(activo[:-4])+'\nRESTO: '+str(round(resto,2))+' USDT\nPROFIT/LOSS ACUM: '+str(round(profit_loss_acum,2))+'%\nPRECIO APERTURA: '+str(precio_apertura)+' USDT\nSTOP LOSS: '+str(stop_value)+' USDT'
                send_telegram(cartera_msg)

        elif posicion == 'VENDIDO':
            if (data.loc[fh_cierre,'rrange']>data.loc[fh_cierre,'ref_rrange'] and data.loc[fh_cierre,'Close']==data.loc[fh_cierre,'max_close']) or (data.loc[fh_cierre,'Close'] > stop_value) or (data.loc[fh_cierre,'Close'] < float(precio_apertura)*(1-tp)):
                send_telegram('CERRAR SHORT')
                send_telegram('activo: ' + activo)
                send_telegram('cantidad: ' + str(cantidad))
                send_telegram('precio_apertura: ' + str(precio_apertura))
                close_short_output, qtty, avg_price = close_short(activo,cantidad,precio_apertura)
                posicion = 'LIQUIDO'
                precio_cierre=float(avg_price)
                resultado = round(-(precio_cierre/float(precio_apertura) -1)*100,2)
                cantidad = float(qtty) + float(resto)
                send_telegram('P/L OPERACIÓN: ' + str(resultado) + '%')
                resto = 0
                stop_value = 0
                precio_apertura = 0
                profit_loss = round((float(cantidad)/float(cant_inic)-1)*100,2)
                posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value = modify_cartera(posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value)      
                #send_telegram de cartera:
                cartera_msg = 'POSICIÓN: ' +str(posicion) + '\nCANT. INICIAL: ' + str(cant_inic)+' USDT \nCANT. ACTUAL: ' +str(round(cantidad,2))+' USDT\nRESTO: '+str(round(resto,2))+' USDT\nPROFIT/LOSS: '+str(round(profit_loss,2))+'%'
                send_telegram(cartera_msg)    
            else:
                profit_loss_abs, profit_loss = position(activo)
                profit_loss_acum = round(100*(((float(precio_apertura) * float(cantidad) + float(resto))/float(cant_inic))*(1+(float(profit_loss)/100))-1),2)
                send_telegram('P/L OPERACIÓN (PARCIAL): ' + str(profit_loss) + '%')
                cartera_msg = 'POSICIÓN: ' +str(posicion) + '\nCANT. INICIAL: ' + str(cant_inic)+' USDT \nCANT. ACTUAL: ' +str(round(cantidad,2))+' '+str(activo[:-4])+'\nRESTO: '+str(round(resto,2))+' USDT\nPROFIT/LOSS ACUM: '+str(round(profit_loss_acum,2))+'%\nPRECIO APERTURA: '+str(precio_apertura)+' USDT\nSTOP LOSS: '+str(stop_value)+' USDT'
                send_telegram(cartera_msg)

        if posicion == 'LIQUIDO':
            if  data.loc[fh_cierre,'rrange']>data.loc[fh_cierre,'ref_rrange'] and data.loc[fh_cierre,'Close']==data.loc[fh_cierre,'max_close'] and data.loc[fh_cierre,'Close']>= data.loc[fh_cierre,'EMA']:
                send_telegram('ABRIR LONG')
                long_order, qtty, avg_price = open_long(activo,cantidad)
                posicion = 'COMPRADO'
                resto = float(cantidad) - (float(qtty)*float(avg_price))-float(long_order['cumQuote'])*0.0004
                cantidad = qtty
                precio_apertura = float(avg_price)
                stop_value = precio_apertura*(1-sl)
                msg = 'OPERADO LONG DE ' +str(cantidad) + ' USDT de ' + str(activo)+' PERPETUAL \nCant Operado: ' +str(qtty)+' '+str(activo[:-4])+'\nPrecio Operado: '+str(avg_price)+' USDT\nStop Loss: '+str(stop_value)+' USDT'
                send_telegram(msg)        
                posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value = modify_cartera(posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value)
                cartera_msg = 'POSICIÓN: ' +str(posicion) + '\nCANT. INICIAL: ' + str(cant_inic)+' USDT\nCANT. ACTUAL: ' +str(round(cantidad,2))+' '+ str(activo[:-4])+'\nRESTO: '+str(round(resto,2))+' USDT\nPROFIT/LOSS: '+str(round(profit_loss,2))+'%'
                send_telegram(cartera_msg)       
            elif data.loc[fh_cierre,'rrange']>data.loc[fh_cierre,'ref_rrange'] and data.loc[fh_cierre,'Close']==data.loc[fh_cierre,'min_close'] and data.loc[fh_cierre,'Close'] < data.loc[fh_cierre,'EMA']:
                send_telegram('ABRIR SHORT')
                short_order, qtty, avg_price = open_short(activo,cantidad)
                posicion = 'VENDIDO'
                resto = float(cantidad) - (float(float(qtty))*float(avg_price)) -float(short_order['cumQuote'])*0.0004
                cantidad = qtty
                precio_apertura = float(avg_price)
                stop_value = precio_apertura*(1+sl)
                msg = 'OPERADO SHORT DE ' +str(cantidad) + ' USDT de ' + str(activo)+' PERPETUAL \nCant Operado: ' +str(qtty)+' '+str(activo[:-4])+'\nPrecio Operado: '+str(avg_price)+' USDT\nStop Loss: '+str(stop_value)+' USDT'
                send_telegram(msg)
                posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value = modify_cartera(posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value)
                cartera_msg = 'POSICIÓN: ' +str(posicion) + '\nCANT. INICIAL: ' + str(cant_inic)+' USDT \nCANT. ACTUAL: ' +str(round(cantidad,2))+' '+ str(activo[:-4])+'\nRESTO: '+str(round(resto,2))+' USDT\nPROFIT/LOSS: '+str(round(profit_loss,2))+'%'
                send_telegram(cartera_msg)        
            else:
                send_telegram('SIN SEÑALES')
                #leo datos de cartera
                posicion, cant_inic, cantidad, resto, profit_loss, precio_apertura, stop_value = read_cartera()      
                #send_telegram de cartera:
                cartera_msg = 'POSICIÓN: ' +str(posicion) + '\nCANT. INICIAL: ' + str(cant_inic)+' USDT \nCANT. ACTUAL: ' +str(round(cantidad,2))+' USDT\nRESTO: '+str(round(resto,2))+' USDT\nPROFIT/LOSS ACUM: '+str(round(profit_loss,2))+'%'
                send_telegram(cartera_msg)
    
    except Exception as e:
        send_telegram('Exception occurred while code execution: ' + repr(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        send_telegram(exc_type, fname, exc_tb.tb_lineno)





