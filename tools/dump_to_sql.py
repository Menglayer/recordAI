# -*- coding: utf-8 -*-
"""
MyLedger SQL Dump Tool: SQLite -> SQL Text
"""
import sqlite3
import os

def generate_sql():
    db_path = 'local_ledger.db'
    if not os.path.exists(db_path):
        print(f"❌ 未找到 {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    output_file = 'supabase_import.sql'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- MyLedger Data Migration SQL\n")
        f.write("BEGIN;\n\n")

        # 1. Snapshots
        f.write("-- 📥 Migrating Snapshots\n")
        cursor.execute("SELECT date, account_name, symbol, quantity, created_at FROM snapshots")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                f.write(f"INSERT INTO snapshots (date, account_name, symbol, quantity, created_at) VALUES ('{row[0]}', '{row[1]}', '{row[2]}', {row[3]}, '{row[4]}');\n")
        
        # 2. Transfers
        f.write("\n-- 💸 Migrating Transfers\n")
        cursor.execute("SELECT date, type, amount_usd, note, created_at FROM transfers")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                note = row[3].replace("'", "''") if row[3] else ""
                f.write(f"INSERT INTO transfers (date, type, amount_usd, note, created_at) VALUES ('{row[0]}', '{row[1]}', {row[2]}, '{note}', '{row[4]}');\n")

        # 3. Price History
        f.write("\n-- 📈 Migrating Price History\n")
        cursor.execute("SELECT date, symbol, price_usd, source, created_at FROM price_history")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                f.write(f"INSERT INTO price_history (date, symbol, price_usd, source, created_at) VALUES ('{row[0]}', '{row[1]}', {row[2]}, '{row[3]}', '{row[4]}');\n")

        f.write("\nCOMMIT;")
    
    conn.close()
    print(f"✅ 生成成功！请打开当前文件夹下的 {output_file}，并复制其内容。")

if __name__ == "__main__":
    generate_sql()
