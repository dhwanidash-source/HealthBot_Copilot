import sqlite3
from pathlib import Path

# Database location
db_path = Path(__file__).parent.parent / "healthcare_copilot.db"

# Output file
output_path = Path(__file__).parent / "schema.sql"

conn = sqlite3.connect(db_path)

with open(output_path, "w", encoding="utf-8") as f:
    # Get all CREATE statements (tables, indexes, triggers, views)
    cursor = conn.execute("""
        SELECT sql
        FROM sqlite_master
        WHERE sql IS NOT NULL
        ORDER BY type, name
    """)

    f.write("-- HealthBot Copilot Database Schema\n")
    f.write("-- Auto-generated\n\n")

    for (sql,) in cursor:
        f.write(sql.strip() + ";\n\n")

conn.close()

print(f"Schema exported to: {output_path}")