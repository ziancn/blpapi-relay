# BLPAPI RELAY

A lightweight, RESTful API relay layer that allows you to communicate with the Bloomberg API (BLPAPI) via standard HTTP requests.

## Why not just Excel Add-in?

This relay layer enables you to build custom, modern dashboards using your existing Bloomberg Terminal as the data source.

If you have ever experienced Excel freezing or crashing due to bloated BDP or BDH formulas, this project offers a robust, modern alternative. 
By pairing this API layer with today's AI coding agents, you can build a highly customized, visually appealing, and efficient web-based frontend at a fraction of the traditional development cost.

## Supported BLPAPI services:
- `//blp/refdata` (Reference Data Services for historical and static data)
- `//blp/mktdata` (Market Data Services for real-time streaming data)

## Request Examples

```http
# //blp/refdata
# Get last price (static, normally last close price) of NVDA US Equity
GET /refdata?tickers=NVDA%20US%20Equity&fields=PX_LAST HTTP/1.1

# //blp/mktdata
# Subscribe last price (live stream) of Bitcoin
WebSocket /mktdata?tickers=XBTUSD%20Curncy&fields=LAST_PRICE
```