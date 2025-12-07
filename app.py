import sqlite3
import json
import time
import math
from math import inf, exp
from heapq import heappush, heappop
from flask import Flask, g, request, jsonify, render_template
from flask_cors import CORS

# ===========================================================
# CONFIG
# ===========================================================

DB_PATH = "safe_route.db"
GRID_WIDTH = 10
GRID_HEIGHT = 10

# severity range: 1 = mild, 2 = moderate, 3 = severe
DEFAULT_SEVERITY = 1

# Incident base weights
INCIDENT_WEIGHTS = {
    'pickpocket': 2.0,
    'harassment': 3.5,
    'poor_lighting': 1.4,
    'stray_dog': 1.1,
    'flood': 2.8,
    'pothole': 0.6,
    'accident': 3.0,
    'other': 1.0
}

# Time decay: incidents lose influence over time
# DECAY_FACTOR = seconds
DECAY_FACTOR = 7 * 24 * 3600   # 7 days


# ===========================================================
# FLASK APP SETUP
# ===========================================================

app = Flask(__name__)
CORS(app)


# ===========================================================
# DATABASE HELPERS
# ===========================================================

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        x INTEGER NOT NULL,
        y INTEGER NOT NULL,
        type TEXT NOT NULL,
        severity INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        notes TEXT
    )
    """)
    db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db:
        db.close()


# ===========================================================
# ADVANCED RISK MODEL (C)
# ===========================================================

def time_decay_factor(t_report, t_now=None):
    """Recent incidents matter more."""
    if t_now is None:
        t_now = int(time.time())
    age = t_now - t_report
    return exp(-age / DECAY_FACTOR)


def read_all_reports():
    db = get_db()
    rows = db.execute("SELECT * FROM reports").fetchall()
    return [dict(r) for r in rows]


def risk_grid_from_reports(width=GRID_WIDTH, height=GRID_HEIGHT, reports=None):
    """Compute weighted, decayed risk for each grid cell."""
    if reports is None:
        reports = read_all_reports()

    now = int(time.time())
    grid = [[0.0 for _ in range(width)] for _ in range(height)]

    for r in reports:
        x, y = int(r["x"]), int(r["y"])
        if 0 <= x < width and 0 <= y < height:
            base_w = INCIDENT_WEIGHTS.get(r["type"], INCIDENT_WEIGHTS["other"])
            severity = int(r.get("severity", DEFAULT_SEVERITY))
            decay = time_decay_factor(r["timestamp"], now)

            # FINAL SCORE = weight × severity × time_decay
            contribution = base_w * severity * decay
            grid[y][x] += contribution

    return grid


# ===========================================================
# DIJKSTRA PATHFINDING (D)
# ===========================================================

def neighbors(x, y, width=GRID_WIDTH, height=GRID_HEIGHT):
    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx, ny = x+dx, y+dy
        if 0 <= nx < width and 0 <= ny < height:
            yield nx, ny


def find_safest_path(start, end, grid):
    """Standard Dijkstra with risk-aware weights."""
    width, height = len(grid[0]), len(grid)
    (sx, sy), (ex, ey) = start, end

    dist = {(sx, sy): 0}
    prev = {}
    pq = [(0, (sx, sy))]

    while pq:
        d, (x, y) = heappop(pq)
        if d > dist.get((x,y), inf):
            continue
        if (x, y) == (ex, ey):
            break

        for nx, ny in neighbors(x, y, width, height):
            cost = (grid[y][x] + grid[ny][nx]) / 2 + 1
            nd = d + cost

            if nd < dist.get((nx, ny), inf):
                dist[(nx, ny)] = nd
                prev[(nx, ny)] = (x, y)
                heappush(pq, (nd, (nx, ny)))

    if (ex, ey) not in dist:
        return None, None

    # Backtrack path
    path = []
    cur = (ex, ey)
    while cur != (sx, sy):
        path.append(cur)
        cur = prev[cur]
    path.append((sx, sy))
    path.reverse()

    return path, dist[(ex, ey)]


# ===========================================================
# API ROUTES
# ===========================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/reports", methods=["GET", "POST"])
def api_reports():

    if request.method == "POST":
        data = request.get_json() or {}
        x = int(data.get("x", -1))
        y = int(data.get("y", -1))
        t = data.get("type", "other")
        sev = int(data.get("severity", 1))
        notes = data.get("notes", "")
        ts = int(time.time())

        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
            return jsonify({"error": "invalid grid location"}), 400

        db = get_db()
        db.execute("""
            INSERT INTO reports (x,y,type,severity,timestamp,notes)
            VALUES (?,?,?,?,?,?)
        """, (x, y, t, sev, ts, notes))
        db.commit()

        return jsonify({"status": "ok"})

    else:
        return jsonify({"reports": read_all_reports()})


@app.route("/api/grid")
def api_grid():
    grid = risk_grid_from_reports()
    return jsonify({"grid": grid, "width": GRID_WIDTH, "height": GRID_HEIGHT})


@app.route("/api/route")
def api_route():
    try:
        sx = int(request.args["sx"])
        sy = int(request.args["sy"])
        ex = int(request.args["ex"])
        ey = int(request.args["ey"])
    except:
        return jsonify({"error": "Missing sx,sy,ex,ey"}), 400

    grid = risk_grid_from_reports()
    path, cost = find_safest_path((sx, sy), (ex, ey), grid)

    if path is None:
        return jsonify({"error": "no path found"}), 500

    return jsonify({"path": path, "cost": cost})


# dev only
@app.route("/api/clear", methods=["POST"])
def api_clear():
    db = get_db()
    db.execute("DELETE FROM reports")
    db.commit()
    return jsonify({"status": "cleared"})


# Init DB
with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
