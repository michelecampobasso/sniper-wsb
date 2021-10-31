import os
import re
import time
import json
import requests
import threading
import traceback
import subprocess
import mmap
from json_manage import *
from binance_key import *
from config import *
from datetime import datetime, timedelta
import dateutil.parser as dparser
from inotify_simple import INotify, flags

import inotify

coins_file = "/tmp/new_coins"

executed_trades_file = 'executed_trades.json'
executed_sales_file = 'executed_sales.json'
pair_dict = {}
executed_queque = []

cnf = load_config('config.yml')
client = load_binance_creds(r'auth.yml')

telegram_status = True
telegram_keys = []

if os.path.exists('telegram.yml'):
    telegram_keys = load_config('telegram.yml')
else: 
    telegram_status = False

tsl_mode = cnf['TRADE_OPTIONS']['ENABLE_TSL']

if tsl_mode:
    sl = cnf['TRADE_OPTIONS']['TSL']
    tp = cnf['TRADE_OPTIONS']['TTP']

else:
    tp = cnf['TRADE_OPTIONS']['TP']
    sl = cnf['TRADE_OPTIONS']['SL']


pairing = cnf['TRADE_OPTIONS']['PAIRING']
amount = cnf['TRADE_OPTIONS']['QUANTITY']
frequency = cnf['TRADE_OPTIONS']['RUN_EVERY']

test_mode = cnf['TRADE_OPTIONS']['TEST']
delay_mode = cnf['TRADE_OPTIONS']['CONSIDER_DELAY']
percentage = cnf['TRADE_OPTIONS']['PERCENTAGE']

regex = '\S{2,6}?/'+ pairing

def tail():
    p = subprocess.Popen(['tail','-n','1',coins_file], stdout=subprocess.PIPE)
    soutput, sinput = p.communicate()
    return soutput

def telegram_bot_sendtext(bot_message):
    send_text = 'https://api.telegram.org/bot' + str(telegram_keys['telegram_key']) + '/sendMessage?chat_id=' + str(telegram_keys['chat_id']) + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    return response.json()['result']['message_id']

def telegram_delete_message(message_id):
    send_text = 'https://api.telegram.org/bot' + str(telegram_keys['telegram_key']) + '/deleteMessage?chat_id=' + str(telegram_keys['chat_id']) + '&message_id=' + str(message_id)
    requests.get(send_text)

class send_without_spamming():
    
    def __init__(self):
        self.id = 0000
        self.first = True
    
    def send(self, message):
        if telegram_status:
            if self.first:
                self.first = False
                self.id = telegram_bot_sendtext(message)
            else:
                telegram_delete_message(self.id)
                self.id = telegram_bot_sendtext(message)
        else:
            print(message)
        
    def kill(self, pair):
        if telegram_status:
            telegram_delete_message(self.id)
            del pair_dict[pair] 


def kill_spam(pair):
    try:
        pair_dict[pair].kill(pair)
    except Exception:
        pass   


def send_spam(pair, message):
    try:
        pair_dict[pair].send(message)
    except Exception:
        pair_dict[pair] = send_without_spamming()
        pair_dict[pair].send(message)


def send_msg(message):
    print(message)
    if telegram_status:
        threading.Thread(target=telegram_bot_sendtext, args=(message,)).start()


def ping_binance():
    sum = 0
    for i in range(3):
        time_before = datetime.timestamp(datetime.now())
        client.ping()
        time_after = datetime.timestamp(datetime.now())
        sum += (time_after - time_before)
    return (sum / 3)


def avFills(order):
    prices = 0
    qty = 0
    for fill in order['fills']:
        prices += (float(fill['price']) * float(fill['qty']))
        qty += float(fill['qty'])
    return prices / qty


def get_price(coin):
     return client.get_ticker(symbol=coin)['lastPrice']


def create_order(pair, usdt_to_spend, action):
    try:
        order = client.create_order(
            symbol = pair,
            side = action,
            type = 'MARKET',
            quoteOrderQty = usdt_to_spend,
            recvWindow = "10000"
        )
    except Exception as exception:       
        wrong = traceback.format_exc(limit=None, chain=True)
        send_msg(wrong)
    return order


def executed_orders():
    global executed_queque
    while True:
        if len(executed_queque) > 0:
            if os.path.exists(executed_trades_file):
                existing_file = load_json(executed_trades_file)
                existing_file += executed_queque
            else: 
                existing_file = executed_queque
            save_json(executed_trades_file, existing_file)
            executed_queque = []
        time.sleep(0.1)


def sell():
    told_ya = False
    while True:
        try:
            flag_update = False
            not_sold_orders = []
            order = []
            if os.path.exists(executed_trades_file):
                order = load_json(executed_trades_file)
            if len(order) > 0:
                for coin in list(order):
                    # store some necesarry trade info for a sell
                    stored_price = float(coin['price'])
                    coin_tp = coin['tp']
                    coin_sl = coin['sl']
                    #volume = coin['executedQty']
                    symbol = coin['symbol']
                    coin_bought = coin['fills'][0]['commissionAsset']
                    volume = float(client.get_asset_balance(asset=coin_bought)['free'])
                    if volume >0:
                        if volume > 1:
                            volume= int(volume)
                        if not told_ya:    
                            send_msg("--WSB-- Volume: {}".format(volume,5))
                        last_price = get_price(symbol)

                        # update stop loss and take profit values if threshold is reached
                        if float(last_price) > coin_tp and tsl_mode:
                            # increase as absolute value for TP
                            new_tp = float(last_price) + (float(last_price)*tp /100)

                            # same deal as above, only applied to trailing SL
                            new_sl = float(last_price) - (float(last_price)*sl /100)

                            # new values to be added to the json file
                            coin['tp'] = new_tp
                            coin['sl'] = new_sl
                            not_sold_orders.append(coin)
                            flag_update = True

                            threading.Thread(target=send_spam, args=(symbol, f'--WSB-- Updated tp: {round(new_tp, 3)} and sl: {round(new_sl, 3)} for: {symbol}')).start()
                        # close trade if tsl is reached or trail option is not enabled
                        elif float(last_price) < coin_sl or float(last_price) > coin_tp:
                            try:

                                # sell for real if test mode is set to false
                                if not test_mode:
                                    sell = client.create_order(symbol = symbol, side = 'SELL', type = 'MARKET', quantity = volume, recvWindow = "10000")

                                send_msg(f"--WSB-- Sold {symbol} at {(float(last_price) - stored_price) / float(stored_price)*100}!")
                                kill_spam(symbol)
                                flag_update = True
                                # remove order from json file by not adding it

                            except Exception as exception:
                                wrong = traceback.format_exc(limit=None, chain=True)
                                send_msg(wrong)

                            # store sold trades data
                            else:
                                if os.path.exists(executed_sales_file):
                                    sold_coins = load_json(executed_sales_file)

                                else:
                                    sold_coins = []

                                if not test_mode:
                                    sold_coins.append(sell)
                                else:
                                    sell = {
                                                'symbol':symbol,
                                                'price':last_price,
                                                'volume':volume,
                                                'time':datetime.timestamp(datetime.now()),
                                                'profit': float(last_price) - stored_price,
                                                'relative_profit': round((float(last_price) - stored_price) / stored_price*100, 3)
                                                }
                                    sold_coins.append(sell)
                                save_json(executed_sales_file, sold_coins)

                        else:
                            not_sold_orders.append(coin)
                        if flag_update: save_json(executed_trades_file, not_sold_orders)
                    else:
                        send_msg("--WSB-- Volume less than 0, retrying...")
                        time.sleep(0.5)
        except Exception as exception:       
            wrong = traceback.format_exc(limit=None, chain=True)
            send_msg(wrong)
            exit(-1)
        time.sleep(0.2)


def place_order_at_time(pair, threads):
    delay = 0
    global executed_queque
    try:
        order = {}
        order = create_order(pair, amount, 'BUY')
        order['price'] = avFills(order)
        amount_order = order['executedQty']
        price = order['price']
        order['tp'] = price + (price*tp /100)
        order['sl'] = price - (price*sl /100)
        send_msg(f'--WSB-- Bought {amount_order} {pair} at {price} each')
        executed_queque.append(order)
    except Exception as exception:       
        wrong = traceback.format_exc(limit=None, chain=True)
        send_msg(wrong)


# Listener on the fd pointing to path
def get_new_coin():
    inotify = INotify()
    # watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF
    watch_flags = flags.MODIFY 
    wd = inotify.add_watch(coins_file, watch_flags)
    # And see the corresponding events:
    for event in inotify.read():
        return tail()
        # print(event)
        # for flag in flags.from_mask(event.mask):
            # print('    ' + str(flag))

def create_pair_and_quantity(new_coin):
    global amount
    if client.get_symbol_info(new_coin + "USDT") is None:
        # No USDT pairing
        info = client.get_symbol_info(new_coin + "BTC")
        if info is not None:
            # BTC pairing
            btc_price = float(client.get_symbol_ticker(symbol="BTCUSDT")['price'])
            for filter in info['filters']:
                # Getting minimum order
                if filter['filterType'] == "MIN_NOTIONAL":
                    least_amount = float(filter['minNotional'])
                    value_least_amount = btc_price * least_amount
                    # TODO: maybe implement a config value to say if to exceed or not, if up to a certain threshold...
                    # Adjust to least order
                    if value_least_amount > amount:
                        amount = least_amount
                    # If less than desired value, get more
                    else:
                        amount = least_amount * (amount/value_least_amount)
                    return new_coin + "BTC"
        else:
            # No BTC pairing
            return None
    else:
        return new_coin + "USDT"

def main():
    while True:
        send_msg('--WSB-- Ready to listen.')
        coin = get_new_coin()
        if coin != "":
            coin_with_ansi = coin.replace(b'\x1b\x5b\x30\x6d\x0a', b'')
            new_coin = coin_with_ansi.decode().rstrip('\n').rstrip('\n')
            pair = create_pair_and_quantity(new_coin)
            if pair is None:
                send_msg(f'--WSB-- Coin '+new_coin+' doesn\'t have USDT nor BTC as counterpart. It will be skipped.')
            else:
                # threading.Thread(target=place_order_at_time, args=(pair, threading.active_count() + 1)).start()
                send_msg(f'--WSB-- Buying {pair}...')

                # threading.Thread(target=sell, args=()).start()
                # threading.Thread(target=executed_orders, args=()).start()
                threading.Thread(target=send_spam, args=("ping", f'--WSB-- Delay to Binance: {ping_binance()*1000:.1f}ms.&disable_notification=true')).start()

if __name__ == '__main__':
    try:
        if not test_mode:
            send_msg('--WSB-- Running in live mode.')
        send_msg(f'--WSB-- Delay to Binance: {ping_binance()*1000:.1f}ms.')
        main()
    except Exception as exception:
        wrong = traceback.format_exc(limit=None, chain=True)
        send_msg(wrong)
