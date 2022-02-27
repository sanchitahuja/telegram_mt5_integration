import json
import threading
import time
from datetime import datetime, timedelta
from os import path

import MetaTrader5 as mt5
import pandas as pd
from telethon import TelegramClient, events

with open("config.json") as f:
    config = json.load(f)
client = TelegramClient(config["user_name"], config["api_id"], config["api_hash"])


def close_trades():
    while True:
        if not path.exists(config["orders_file"]):
            print(f"Order file {config['orders_file']} doesnt exist!")
            time.sleep(20)
            continue
        df = pd.read_csv(config["orders_file"])
        df["time"] = pd.to_datetime(df["time"])
        if path.exists(config["close_orders_file"]):
            close_orders_df = pd.read_csv(config["close_orders_file"])
        else:
            close_orders_df = pd.DataFrame(
                columns=[
                    "position_id",
                    "close_position_id",
                    "time",
                    "symbol",
                    "order_type",
                    "status",
                ]
            )

        for index, row in df.iterrows():
            if row["position_id"] in (close_orders_df["position_id"]):
                print(f"Position {row['position_id']} already closed!")
                continue
            positions = mt5.positions_get(ticket=row["position_id"])
            action = "sell" if row["order_type"] == 1 else "buy"
            symbol = row["symbol"]
            print("Positions", positions)
            if positions is None or len(positions) == 0:
                print(f"No  Position {row['position_id']} Exist")
            else:

                if datetime.now() >= row["time"] + timedelta(hours=1):
                    # Close Trade logic here Use the abobe function
                    if action == "buy":
                        trade_type = mt5.ORDER_TYPE_BUY
                        price = mt5.symbol_info_tick(symbol).ask
                    elif action == "sell":
                        trade_type = mt5.ORDER_TYPE_SELL
                        price = mt5.symbol_info_tick(symbol).bid
                    else:
                        continue
                    close_request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": config["volume"],
                        "type": trade_type,
                        "position": row["position_id"],
                        "price": price,
                        "deviation": config["deviation"],
                        "comment": "python script close",
                        "type_time": mt5.ORDER_TIME_GTC,  # good till cancelled
                        "type_filling": mt5.ORDER_FILLING_RETURN,
                    }
                    # send a close request
                    result = mt5.order_send(close_request)
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        print(
                            f"Close Order Send failed, retcode:{result.retcode}! Unable to close position: "
                            f"{row['position_id']}"
                        )
                        print(f"Error: {mt5.last_error()}")
                        print(result.order)
                    else:
                        print(f"Closed position with POSITION_TICKET: {result.order}")
                        d = {
                            "position_id": row["position_id"],
                            "close_position_id": result.order,
                            "time": datetime.now(),
                            "symbol": symbol,
                            "order_type": action,
                            "status": "closed",
                        }
                        close_orders_df = close_orders_df.append(d, ignore_index=True)

        close_orders_df.to_csv(config["close_orders_file"], index=False)
        del close_orders_df
        # Todo Check after one hour
        time.sleep(20)


def handle_trades(msg: str, symbol: str, volume: float):
    msg_obj = json.loads(msg)
    point = mt5.symbol_info(symbol).point
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type_time": mt5.ORDER_TIME_DAY,
        "type_filling": mt5.ORDER_FILLING_RETURN,
        "deviation": config["deviation"],
    }
    if msg_obj["position"] == 1:
        price = mt5.symbol_info_tick(symbol).ask
        print("Price", price)
        print("point", point)
        request.update(
            {
                "price": price,
                "sl": price - 100 * point,
                "tp": price + 100 * point,
                "type": mt5.ORDER_TYPE_BUY,
            }
        )
    elif msg_obj["position"] == -1:
        price = mt5.symbol_info_tick(symbol).bid
        request.update(
            {
                "price": price,
                "sl": price + 100 * point,
                "tp": price - 100 * point,
                "type": mt5.ORDER_TYPE_SELL,
            }
        )

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order Send failed, return code:{result.retcode}")
        print(f"Error: {mt5.last_error()}")
        print(result.order)
    else:
        print(f"Opened position with POSITION_TICKET: {result.order}")
        cur_order = result.order
        row = {
            "position_id": cur_order,
            "time": datetime.now(),
            "symbol": symbol,
            "order_type": msg_obj["position"],
            "status": "open",
        }
        if path.exists(config["orders_file"]):
            df = pd.read_csv(config["orders_file"])
        else:
            df = pd.DataFrame()
        df = df.append([row])
        df.to_csv(config["orders_file"], index=False)


@client.on(events.NewMessage)
async def handler(event):
    chat = await event.get_chat()
    sender = await event.get_sender()
    chat_id = event.chat_id
    sender_id = event.sender_id
    print("First Name", chat.first_name, "id", chat_id)
    if chat.first_name == config["sender_name"] and str(chat_id) == config["sender_id"]:
        try:
            print("Calling handle Trades")
            handle_trades(
                msg=event.message.message,
                symbol=config["symbol"],
                volume=config["volume"],
            )
        except Exception as e:
            print(f"error occurred: {e}")
    print(
        "Chat",
        chat,
        "Sender",
        sender,
        "chat_id",
        chat_id,
        "sender_id",
        sender_id,
        "event",
        event.message.message,
    )


client.start()

if not mt5.initialize():
    print("MT5 Initialize Failed initialize() failed")
    mt5.shutdown()
print(mt5.terminal_info())

if config["password"]:
    authorized = mt5.login(
        config["account"], password=config["password"], server=config["server"]
    )
else:
    authorized = mt5.login(config["account"])

if authorized:
    print("Account Info:", mt5.account_info())
else:
    print(
        "Failed to connect at account: {}, error code: {}".format(
            config["account"], mt5.last_error()
        )
    )
    mt5.shutdown()

close_trade_thread = threading.Thread(target=close_trades, name="CloseTrades")
close_trade_thread.start()
client.run_until_disconnected()
mt5.shutdown()
