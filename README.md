# telegram_mt5_integration
Telegram MT5 integration

This repo allows you to integrate Telegram app and pass on specific messages through a channel receive those message and execute the trades on MT5.

The code is written for Specific hourly requirements of a trader.
Requirements were as follow :
* To have 100 points Stop loss
* To have 100 points Target
* Auto exit trades after every hour

The code

We have used Metatrader5 library to integrate with Metatrader and telethon to integrate with telegram.

Config is as show below:
```
{
  "api_id": "<api_id>", // API ID of your Telegram 
  "api_hash": "<api_hash>", // API Hash of your Telegram 
  "phone": "+91<mobile_number>", // Your Phone Number
  "user_name": "Goku97Sama", // Your Telegram Username
  "account": 12345678 , // MT5 Account ID
  "password": "", // MT5 Password
  "symbol": "GBPUSD", // Trading Instrument Symbol
  "orders_file": "orders.csv", // File to Store order history
  "deviation": 1  // Deviation to when placing order
  "volume": // Quanitity when placing/closing orders 
  "sender_name": "InvestingGuide", // Name of person sending message
  "sender_id": "sender_id" // Chat id of the person sending messages,
  "close_orders_file": "close_orders.csv" // File path to store Closed Orders
}

```

The flow of program is as follow:
* The client sends a message on telegram with a message which is a JSON String ```{"position": 1}``` or ```{"position": -1}``` where 1 denotes Buy and -1 denotes Sell.
* The New messages is parsed from json string and sent to handle_trades that executes the Position based on Configuration settings.
* The close trade function is something that keeps executing in the background to exit all existing orders after an hour.