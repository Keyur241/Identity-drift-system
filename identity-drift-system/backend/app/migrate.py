"""Safe schema initialisation: adds new agent columns to an existing SQLite DB (create_all adds new tables)."""
from sqlalchemy import inspect, text

ADD = [("description", "TEXT", "''"), ("baseline", "JSON", None), ("risk_score", "FLOAT", "0"),
       ("session_active", "BOOLEAN", "1"), ("restricted_permissions", "JSON", None), ("drift_sig", "VARCHAR", "''")]


def ensure_schema(engine):
    have = {c["name"] for c in inspect(engine).get_columns("agents")}
    with engine.begin() as conn:
        for name, typ, default in ADD:
            if name not in have:
                conn.execute(text(f"ALTER TABLE agents ADD COLUMN {name} {typ}" + (f" DEFAULT {default}" if default else "")))
