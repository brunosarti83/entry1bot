from binance.enums import *
import config_futures
from binance.client import Client
import math
import time
from telegram import send_telegram
import telegram

client = Client(config_futures.API_KEY, config_futures.API_SECRET)

def precio(activo):
    prices = client.futures_symbol_ticker()
    for i in range(len(prices)):
        if activo == prices[i]['symbol']:
            precio = prices[i]['price']
    return precio

#función para truncar decimales, de manera de ajustar a la cantidad múltiplo mínima de ETHUSDT PERPETUAL, que es 0.01
def truncate(number, digits) -> float:
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

def open_long(activo,cantidad): #compra en futuros
    
    def precio(activo):
        prices = client.futures_symbol_ticker()
        for i in range(len(prices)):
            if activo == prices[i]['symbol']:
                precio = prices[i]['price']
        return precio
       
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    precio = precio(activo)
    cant_ajust = truncate(cantidad/float(precio),3)
    while True:
        try:
            long_order = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'BUY', type = 'MARKET', quantity = float(cant_ajust)) #acá lo pongo quoteOrderQty porque le digo los BTC que tengo (supongo que compro ETHBTC)
        except:
            cant_ajust = cant_ajust*0.9995
            continue
        break
        
    orderId = str(long_order['orderId'])
    while True:
        try:
            time.sleep(1)
            filled_order = client.futures_get_order(symbol = activo, orderId = orderId)
        except:
            send_telegram('Esperando order status')
            continue
        break
    qtty = float(filled_order['executedQty'])
    avg_price = float(filled_order['avgPrice'])
    return filled_order, qtty, avg_price

def close_long(activo,cantidad,precio_aper): #cierro long en futuros
    cant_aper = float(cantidad)*float(precio_aper)
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    close_long_output = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'SELL', type = 'MARKET', quantity = cantidad) #acá lo pongo quoteOrderQty porque le digo los BTC que tengo (supongo que compro ETHBTC)
    orderId = close_long_output['orderId']
    while True:
        try:
            time.sleep(1)
            filled_order = client.futures_get_order(symbol = activo, orderId = orderId)
        except:
            send_telegram('Esperando order status')
            continue
        break
    qtty = float(cant_aper) + (float(filled_order['cumQuote']) - float(cant_aper))-float(filled_order['cumQuote'])*0.0004
    avg_price = float(filled_order['avgPrice'])
    return filled_order, qtty, avg_price

def open_short(activo,cantidad): #short en futuros
    def precio(activo):
        prices = client.futures_symbol_ticker()
        for i in range(len(prices)):
            if activo == prices[i]['symbol']:
                precio = prices[i]['price']
        return precio
       
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    precio = precio(activo)
    cant_ajust = truncate(cantidad/float(precio),3)
    while True:
        try:
            short_order = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'SELL', type = 'MARKET', quantity = float(cant_ajust)) #acá lo pongo quoteOrderQty porque le digo los BTC que tengo (supongo que compro ETHBTC)
        except:
            cant_ajust = cant_ajust*0.9995
            continue
        break
       
    orderId = str(short_order['orderId'])
    while True:
        try:
            time.sleep(1)
            filled_order = client.futures_get_order(symbol = activo, orderId = orderId)
        except:
            send_telegram('Esperando order status')
            continue
        break
        
    filled_order = client.futures_get_order(symbol = activo, orderId = orderId)
    qtty = float(filled_order['origQty'])
    avg_price = float(filled_order['avgPrice'])
    return filled_order, qtty, avg_price

def close_short(activo,cantidad,precio_aper): #cierro short en futuros
    cant_aper = float(cantidad)*float(precio_aper)
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    contador = 0
    while True:    
        contador += 1
        send_telegram(contador)
        close_short_output = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'BUY', type = 'MARKET', quantity = cantidad)
        if close_short_output  != None:
            break
        if contador == 21:
            break
        time.sleep(1)    
    orderId = str(close_short_output['orderId'])
    while True:
        try:
            time.sleep(1)
            filled_order = client.futures_get_order(symbol = activo, orderId = orderId)
        except:
            send_telegram('Esperando order status')
            continue
        break
    
    qtty = float(cant_aper) + (float(cant_aper) - float(filled_order['cumQuote']))-float(filled_order['cumQuote'])*0.0004
    avg_price = filled_order['avgPrice']
    return filled_order, qtty, avg_price

def balance():
    balance_total = client.futures_account_balance()[1]['balance']
    balance_transferible = client.futures_account_balance()[1]['withdrawAvailable']
    return balance_total, balance_transferible


def position(activo):
    
    position = client.futures_position_information()
    for i in range(len(position)):
        if activo == position[i]['symbol']:
            pos_activo = position[i]
    #para los short hay que multiplicar x -1 el resultado
    if float(pos_activo['positionAmt']) >= 0:
        profit_loss = 100*float(pos_activo['unRealizedProfit'])/(float(pos_activo['entryPrice'])*float(pos_activo['positionAmt']))
    else:
        profit_loss = -100*float(pos_activo['unRealizedProfit'])/(float(pos_activo['entryPrice'])*float(pos_activo['positionAmt']))
    profit_loss = round(profit_loss,2)
    profit_loss_abs = str(round(float(pos_activo['unRealizedProfit']),2))+' USDT'
    return profit_loss_abs, profit_loss
    

#tot, trans = balance()
#print(trans)
#precio = 3170
#order, cantidad = open_short('ETHUSDT',50)
#positions = positions('ETHUSDT')
#print(positions)
#print(cantidad)
#close = close_short('ETHUSDT',0.01)
#print(close)
