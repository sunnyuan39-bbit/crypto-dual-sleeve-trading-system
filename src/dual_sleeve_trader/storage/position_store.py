from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

from dual_sleeve_trader.core.account import ExchangePositionSnapshot


class SQLitePositionStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT NOT NULL,
                position_side TEXT NOT NULL,
                position_amt TEXT NOT NULL,
                entry_price TEXT,
                mark_price TEXT,
                unrealized_profit TEXT NOT NULL,
                notional TEXT NOT NULL,
                isolated_margin TEXT NOT NULL,
                update_time_ms INTEGER,
                PRIMARY KEY(symbol, position_side)
            )
            """
        )
        self.conn.commit()

    def upsert_position(self, position: ExchangePositionSnapshot) -> None:
        self.conn.execute(
            """
            INSERT INTO positions (
                symbol, position_side, position_amt, entry_price, mark_price,
                unrealized_profit, notional, isolated_margin, update_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, position_side) DO UPDATE SET
                position_amt=excluded.position_amt,
                entry_price=excluded.entry_price,
                mark_price=excluded.mark_price,
                unrealized_profit=excluded.unrealized_profit,
                notional=excluded.notional,
                isolated_margin=excluded.isolated_margin,
                update_time_ms=excluded.update_time_ms
            """,
            (
                position.symbol,
                position.position_side,
                str(position.position_amt),
                str(position.entry_price) if position.entry_price is not None else None,
                str(position.mark_price) if position.mark_price is not None else None,
                str(position.unrealized_profit),
                str(position.notional),
                str(position.isolated_margin),
                position.update_time_ms,
            ),
        )
        self.conn.commit()

    def get_position(self, symbol: str, position_side: str = "BOTH") -> ExchangePositionSnapshot | None:
        row = self.conn.execute(
            "SELECT * FROM positions WHERE symbol = ? AND position_side = ?",
            (symbol, position_side),
        ).fetchone()
        return _row_to_position(row) if row else None

    def list_positions(self, include_flat: bool = False) -> list[ExchangePositionSnapshot]:
        rows = self.conn.execute("SELECT * FROM positions").fetchall()
        positions = [_row_to_position(row) for row in rows]
        if include_flat:
            return positions
        return [position for position in positions if not position.is_flat]

    def close(self) -> None:
        self.conn.close()


def _row_to_position(row: sqlite3.Row) -> ExchangePositionSnapshot:
    return ExchangePositionSnapshot(
        symbol=row["symbol"],
        position_side=row["position_side"],
        position_amt=Decimal(row["position_amt"]),
        entry_price=Decimal(row["entry_price"]) if row["entry_price"] is not None else None,
        mark_price=Decimal(row["mark_price"]) if row["mark_price"] is not None else None,
        unrealized_profit=Decimal(row["unrealized_profit"]),
        notional=Decimal(row["notional"]),
        isolated_margin=Decimal(row["isolated_margin"]),
        update_time_ms=row["update_time_ms"],
    )
