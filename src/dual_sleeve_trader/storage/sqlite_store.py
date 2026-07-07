from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord

_OPEN_STATUSES = {
    OrderStatus.CREATED,
    OrderStatus.SUBMITTED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.UNKNOWN,
}


class SQLiteOrderStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                client_order_id TEXT PRIMARY KEY,
                exchange_order_id TEXT,
                sleeve_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity TEXT NOT NULL,
                price TEXT,
                reduce_only INTEGER NOT NULL,
                setup_id TEXT,
                status TEXT NOT NULL,
                filled_quantity TEXT NOT NULL,
                average_fill_price TEXT
            )
            """
        )
        self.conn.commit()

    def upsert_order(self, order: OrderRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO orders (
                client_order_id, exchange_order_id, sleeve_id, symbol, side, order_type, action,
                quantity, price, reduce_only, setup_id, status, filled_quantity, average_fill_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(client_order_id) DO UPDATE SET
                exchange_order_id=excluded.exchange_order_id,
                status=excluded.status,
                filled_quantity=excluded.filled_quantity,
                average_fill_price=excluded.average_fill_price
            """,
            (
                order.client_order_id,
                order.exchange_order_id,
                order.intent.sleeve_id.value,
                order.intent.symbol,
                order.intent.side.value,
                order.intent.order_type.value,
                order.intent.action.value,
                str(order.intent.quantity),
                str(order.intent.price) if order.intent.price is not None else None,
                int(order.intent.reduce_only),
                order.intent.setup_id,
                order.status.value,
                str(order.filled_quantity),
                str(order.average_fill_price) if order.average_fill_price is not None else None,
            ),
        )
        self.conn.commit()

    def get_order(self, client_order_id: str) -> OrderRecord | None:
        row = self.conn.execute(
            "SELECT * FROM orders WHERE client_order_id = ?",
            (client_order_id,),
        ).fetchone()
        return _row_to_order(row) if row else None

    def list_open_orders(self) -> list[OrderRecord]:
        placeholders = ",".join("?" for _ in _OPEN_STATUSES)
        rows = self.conn.execute(
            f"SELECT * FROM orders WHERE status IN ({placeholders})",
            tuple(status.value for status in _OPEN_STATUSES),
        ).fetchall()
        return [_row_to_order(row) for row in rows]

    def close(self) -> None:
        self.conn.close()


def _row_to_order(row: sqlite3.Row) -> OrderRecord:
    intent = OrderIntent(
        sleeve_id=SleeveId(row["sleeve_id"]),
        symbol=row["symbol"],
        side=OrderSide(row["side"]),
        order_type=OrderType(row["order_type"]),
        action=OrderAction(row["action"]),
        quantity=Decimal(row["quantity"]),
        price=Decimal(row["price"]) if row["price"] is not None else None,
        reduce_only=bool(row["reduce_only"]),
        setup_id=row["setup_id"],
    )
    return OrderRecord(
        client_order_id=row["client_order_id"],
        intent=intent,
        status=OrderStatus(row["status"]),
        exchange_order_id=row["exchange_order_id"],
        filled_quantity=Decimal(row["filled_quantity"]),
        average_fill_price=Decimal(row["average_fill_price"])
        if row["average_fill_price"] is not None
        else None,
    )
