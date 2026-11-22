import sqlite3, threading, time, json

SCHEMA = """
CREATE TABLE IF NOT EXISTS wallets(id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, simulator TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS ledger(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, idem_key TEXT UNIQUE NOT NULL, wallet_id TEXT NOT NULL,
  asset TEXT NOT NULL, delta TEXT NOT NULL, kind TEXT NOT NULL, ref TEXT, ts REAL NOT NULL, source TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger BEGIN SELECT RAISE(ABORT,'ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger BEGIN SELECT RAISE(ABORT,'ledger is append-only'); END;
CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, idem_key TEXT UNIQUE NOT NULL, wallet_id TEXT, symbol TEXT, side TEXT,
  qty TEXT, price TEXT, status TEXT, reason TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, body TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, actor TEXT, action TEXT, detail TEXT);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
CREATE TABLE IF NOT EXISTS config(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS channels(name TEXT PRIMARY KEY, channel_id INTEGER, panel_message_id INTEGER);
CREATE TABLE IF NOT EXISTS candles(symbol TEXT, ts INTEGER, o REAL,h REAL,l REAL,c REAL,v REAL, source TEXT, PRIMARY KEY(symbol,ts,source));
CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, level TEXT, msg TEXT);
"""

class Database:
    def __init__(self, path=":memory:"):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        if path != ":memory:": self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
    def execute(self, sql, params=()):
        with self.lock: return self.conn.execute(sql, params)
    def tx(self): return _Tx(self)
    def audit(self, actor, action, detail=None):
        self.execute("INSERT INTO audit(ts,actor,action,detail) VALUES(?,?,?,?)", (time.time(), actor, action, json.dumps(detail, default=str)))
    def get_config(self, k, default=None):
        r = self.execute("SELECT v FROM config WHERE k=?", (k,)).fetchone()
        return r["v"] if r else default
    def set_config(self, k, v):
        self.execute("INSERT INTO config(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))

class _Tx:
    def __init__(self, db): self.db = db
    def __enter__(self):
        self.db.lock.acquire(); self.db.conn.execute("BEGIN IMMEDIATE"); return self.db
    def __exit__(self, et, ev, tb):
        try: self.db.conn.execute("ROLLBACK" if et else "COMMIT")
        finally: self.db.lock.release()
        return False
