-- MyLedger Data Migration SQL
BEGIN;

-- 📥 Migrating Snapshots
INSERT INTO snapshots (date, account_name, symbol, quantity, created_at) VALUES ('2026-01-07', 'Binance', 'USDT', 90594.0, '2026-01-07 01:02:07.910031');
INSERT INTO snapshots (date, account_name, symbol, quantity, created_at) VALUES ('2026-01-07', 'Bitget', 'USDT', 220965.0, '2026-01-07 01:03:03.245184');
INSERT INTO snapshots (date, account_name, symbol, quantity, created_at) VALUES ('2026-01-07', 'OKX', 'USDT', 0.1, '2026-01-07 01:03:25.718525');
INSERT INTO snapshots (date, account_name, symbol, quantity, created_at) VALUES ('2026-01-07', 'Bron', 'USDT', 20558.0, '2026-01-07 01:05:23.234756');
INSERT INTO snapshots (date, account_name, symbol, quantity, created_at) VALUES ('2026-01-07', 'Buidlpad Vault', 'USDT', 100350.0, '2026-01-07 01:06:42.653554');
INSERT INTO snapshots (date, account_name, symbol, quantity, created_at) VALUES ('2026-01-07', 'vSOLV Vesting', 'VSOLV', 122033.8184, '2026-01-07 01:08:12.469644');

-- 💸 Migrating Transfers

-- 📈 Migrating Price History
INSERT INTO price_history (date, symbol, price_usd, source, created_at) VALUES ('2026-01-07', 'USDT', 1.0, 'fixed', '2026-01-07 01:19:06.673005');
INSERT INTO price_history (date, symbol, price_usd, source, created_at) VALUES ('2026-01-07', 'VSOLV', 0.0085, 'manual', '2026-01-07 01:21:40.607312');

COMMIT;