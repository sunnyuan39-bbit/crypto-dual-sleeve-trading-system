from __future__ import annotations

from enum import StrEnum


class TradingMode(StrEnum):
    SIGNAL_ONLY = "SIGNAL_ONLY"
    PAPER_LOCAL = "PAPER_LOCAL"
    EXCHANGE_TESTNET = "EXCHANGE_TESTNET"


class SleeveId(StrEnum):
    A = "A"
    B = "B"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class OrderAction(StrEnum):
    ENTRY = "EN"
    STOP_LOSS = "SL"
    TAKE_PROFIT_1 = "TP1"
    TAKE_PROFIT_2 = "TP2"
    TAKE_PROFIT_3 = "TP3"
    TIME_STOP = "TS"
    CIRCUIT_BREAK = "CB"


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class SafeModeState(StrEnum):
    NORMAL = "NORMAL"
    SAFE_MODE = "SAFE_MODE"


class CircuitAction(StrEnum):
    NONE = "NONE"
    BLOCK_NEW_ENTRIES = "BLOCK_NEW_ENTRIES"
    EXIT_ONLY = "EXIT_ONLY"
    CANCEL_ENTRIES = "CANCEL_ENTRIES"
    FLATTEN_A_REDUCE_ONLY = "FLATTEN_A_REDUCE_ONLY"
    MANUAL_REVIEW = "MANUAL_REVIEW"
