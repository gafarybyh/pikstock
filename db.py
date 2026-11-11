"""db.py — riwayat run di SQLite. Nol dependency (sqlite3 bawaan Python).

Skema sengaja longgar: kolom `data` menyimpan JSON hasil lengkap, jadi menambah
field keyword/tren nanti tidak butuh migrasi besar.
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "history.db"

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    path       TEXT UNIQUE,
    name       TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS batches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER REFERENCES projects(id),
    folder      TEXT,
    total       INTEGER NOT NULL DEFAULT 0,
    done        INTEGER NOT NULL DEFAULT 0,
    failed      INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'running',
    created_at  TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id    INTEGER REFERENCES batches(id),
    source      TEXT NOT NULL DEFAULT 'upload',
    path        TEXT,
    filename    TEXT NOT NULL,
    thumb       TEXT,
    data        TEXT,
    model       TEXT,
    duration_ms INTEGER,
    status      TEXT NOT NULL DEFAULT 'ok',
    error       TEXT,
    favorite    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    term       TEXT PRIMARY KEY,
    status     TEXT NOT NULL,
    pos        INTEGER NOT NULL DEFAULT -1,
    note       TEXT,
    checked_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_batch   ON runs(batch_id);
"""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init():
    with _lock, connect() as con:
        con.executescript(SCHEMA)
        cols = {r["name"] for r in con.execute("PRAGMA table_info(runs)")}
        if "favorite" not in cols:
            con.execute("ALTER TABLE runs ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")


def upsert_project(path, name=None):
    if not path:
        return None
    with _lock, connect() as con:
        con.execute("INSERT OR IGNORE INTO projects(path, name, created_at) VALUES (?,?,?)",
                    (path, name or Path(path).name, now()))
        row = con.execute("SELECT id FROM projects WHERE path=?", (path,)).fetchone()
        return row["id"] if row else None


def create_batch(project_id, folder, total):
    with _lock, connect() as con:
        cur = con.execute(
            "INSERT INTO batches(project_id, folder, total, created_at) VALUES (?,?,?,?)",
            (project_id, folder, total, now()))
        return cur.lastrowid


def update_batch(batch_id, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with _lock, connect() as con:
        con.execute(f"UPDATE batches SET {cols} WHERE id=?", (*fields.values(), batch_id))


def add_run(*, batch_id=None, source="upload", path=None, filename="", thumb=None,
            data=None, model="", duration_ms=0, status="ok", error=None):
    payload = json.dumps(data, ensure_ascii=False) if data is not None else None
    with _lock, connect() as con:
        cur = con.execute(
            "INSERT INTO runs(batch_id, source, path, filename, thumb, data, model,"
            " duration_ms, status, error, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (batch_id, source, path, filename, thumb, payload, model,
             duration_ms, status, error, now()))
        return cur.lastrowid


def update_run(run_id, *, thumb=None, data=None, model="", duration_ms=0, status="ok",
               error=None, filename=None):
    """Timpa isi run yang sudah ada. Kolom yang tidak diberikan dibiarkan."""
    payload = json.dumps(data, ensure_ascii=False) if data is not None else None
    sets = ["thumb=?", "data=?", "model=?", "duration_ms=?", "status=?", "error=?"]
    args = [thumb, payload, model, duration_ms, status, error]
    if filename is not None:
        sets.append("filename=?")
        args.append(filename)
    args.append(run_id)
    with _lock, connect() as con:
        cur = con.execute(f"UPDATE runs SET {', '.join(sets)} WHERE id=?", args)
        return cur.rowcount > 0


def _run_row(row):
    d = dict(row)
    for key in ("markets", "sizes", "images"):
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except json.JSONDecodeError:
                d[key] = None
    if d.get("data"):
        try:
            d["data"] = json.loads(d["data"])
        except json.JSONDecodeError:
            d["data"] = None
    return d


def list_runs(q="", limit=50, offset=0, status=None, source=None, scope=None, favorite=False, market=None):
    where, args = [], []
    if q:
        where.append("(filename LIKE ? OR data LIKE ?)")
        args += [f"%{q}%", f"%{q}%"]
    if market:
        where.append("json_extract(data, '$._marketplaces') LIKE ?")
        args.append(f'%"{market}"%')
    if favorite:
        where.append("favorite=1")
    if status == "ok":
        where.append("status='ok'")
    elif status == "bad":
        where.append("status!='ok'")
    if scope == "extract":
        where.append("source LIKE 'extract%'")
    elif scope == "image":
        where.append("source='image'")
    elif scope == "keyword":
        where.append("source NOT LIKE 'extract%' AND source!='image'")
    if source:
        where.append("source=?")
        args.append(source)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    sql = ("SELECT id, batch_id, source, filename, thumb, model, duration_ms,"
           " status, error, favorite, created_at,"
           " json_extract(data, '$._marketplaces') AS markets,"
           " json_extract(data, '$.sizes') AS sizes,"
           " json_extract(data, '$.images') AS images FROM runs" + clause +
           " ORDER BY id DESC LIMIT ? OFFSET ?")
    with _lock, connect() as con:
        rows = con.execute(sql, args + [int(limit), int(offset)]).fetchall()
        # total ikut filter yang sama (dulu selalu COUNT(*) tanpa WHERE → paginasi salah)
        total = con.execute("SELECT COUNT(*) c FROM runs" + clause, args).fetchone()["c"]
    return [_run_row(r) for r in rows], total


def get_run(run_id):
    with _lock, connect() as con:
        row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    return _run_row(row) if row else None

def seen_filenames(names):
    """Subset nama (lowercase) yang sudah pernah diproses sukses. Untuk cegah duplikat."""
    low = [str(n).strip().lower() for n in names if str(n).strip()]
    if not low:
        return []
    marks = ",".join("?" * len(low))
    with _lock, connect() as con:
        rows = con.execute(
            f"SELECT DISTINCT LOWER(filename) f FROM runs"
            f" WHERE status='ok' AND source NOT LIKE 'extract%' AND source!='image'"
            f" AND LOWER(filename) IN ({marks})", low).fetchall()
    return [r["f"] for r in rows]


def set_favorite(run_id, favorite):
    with _lock, connect() as con:
        cur = con.execute("UPDATE runs SET favorite=? WHERE id=?", (1 if favorite else 0, run_id))
        return cur.rowcount > 0


def delete_run(run_id):
    with _lock, connect() as con:
        cur = con.execute("DELETE FROM runs WHERE id=?", (run_id,))
        return cur.rowcount > 0


def delete_runs(ids):
    ids = [int(i) for i in ids]
    if not ids:
        return 0
    marks = ",".join("?" * len(ids))
    with _lock, connect() as con:
        cur = con.execute(f"DELETE FROM runs WHERE id IN ({marks})", ids)
        return cur.rowcount


def clear_runs(scope=None):
    sql = "DELETE FROM runs"
    if scope == "extract":
        sql += " WHERE source LIKE 'extract%'"
    elif scope == "image":
        sql += " WHERE source='image'"
    elif scope == "keyword":
        sql += " WHERE source NOT LIKE 'extract%' AND source!='image'"
    with _lock, connect() as con:
        cur = con.execute(sql)
        return cur.rowcount


def list_batches(limit=30):
    with _lock, connect() as con:
        rows = con.execute(
            "SELECT b.*, p.name AS project_name FROM batches b"
            " LEFT JOIN projects p ON p.id=b.project_id"
            " ORDER BY b.id DESC LIMIT ?", (int(limit),)).fetchall()
    return [dict(r) for r in rows]


def stats():
    with _lock, connect() as con:
        r = con.execute(
            "SELECT COUNT(*) total,"
            " COALESCE(SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END),0) ok,"
            " COALESCE(SUM(CASE WHEN status!='ok' THEN 1 ELSE 0 END),0) bad,"
            " COALESCE(AVG(duration_ms),0) avg_ms FROM runs").fetchone()
    return dict(r)


def export_runs(q="", status=None, source=None):
    """Run sukses (dengan data) untuk ekspor CSV — urut lama->baru, mengikuti filter riwayat."""
    sql = ("SELECT id, filename, created_at, data FROM runs"
           " WHERE status='ok' AND data IS NOT NULL AND source NOT LIKE 'extract%' AND source!='image'")
    args = []
    if q:
        sql += " AND (filename LIKE ? OR data LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if source:
        sql += " AND source=?"
        args.append(source)
    sql += " ORDER BY id"
    with _lock, connect() as con:
        rows = con.execute(sql, args).fetchall()
    return [_run_row(r) for r in rows]


def get_signal(term, ttl_days=7):
    """Cache sinyal yang masih segar (default 7 hari); None kalau tidak ada/basi."""
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - ttl_days * 86400))
    with _lock, connect() as con:
        row = con.execute(
            "SELECT term, status, pos, note, checked_at FROM signals"
            " WHERE term=? AND checked_at>=?", (term, cutoff)).fetchone()
    return dict(row) if row else None


def set_signal(term, status, pos=-1, note=""):
    with _lock, connect() as con:
        con.execute(
            "INSERT INTO signals(term, status, pos, note, checked_at) VALUES (?,?,?,?,?)"
            " ON CONFLICT(term) DO UPDATE SET status=excluded.status, pos=excluded.pos,"
            " note=excluded.note, checked_at=excluded.checked_at",
            (term, status, int(pos), note, now()))


init()
