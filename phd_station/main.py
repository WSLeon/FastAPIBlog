import os
import sqlite3
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
from datetime import datetime

app = FastAPI(title="博士生精神状态监测站 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

DB_FILE = os.path.join(BASE_DIR, "phd_survival.db")


# --- 数据模型更新：加入每日总结 ---
class DailyRecordUpdate(BaseModel):
    date: str
    study_time_seconds: int
    ball_time_seconds: int
    mood: str
    summary: str = ""  # 新增每日总结字段


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_records (
            date TEXT PRIMARY KEY,
            mood TEXT,
            study_time_seconds INTEGER DEFAULT 0,
            ball_time_seconds INTEGER DEFAULT 0,
            cat_clicks INTEGER DEFAULT 0,
            dog_clicks INTEGER DEFAULT 0
        )
    ''')

    # 【无损升级】尝试为老表加上 summary 字段，如果已存在则跳过
    try:
        cursor.execute("ALTER TABLE daily_records ADD COLUMN summary TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

        # ... 其他表结构保持不变 ...
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, icon TEXT)''')
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS location_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, location_id INTEGER, clicks INTEGER DEFAULT 0, FOREIGN KEY (location_id) REFERENCES locations (id), UNIQUE(date, location_id))''')

    cursor.execute('SELECT COUNT(*) FROM locations')
    if cursor.fetchone()[0] == 0:
        default_locations = [('图书馆', 'library'), ('实验室', 'lab'), ('咖啡厅', 'cafe'), ('家里', 'home')]
        cursor.executemany('INSERT INTO locations (name, icon) VALUES (?, ?)', default_locations)

    conn.commit()
    conn.close()


init_db()


@app.get("/")
def read_root():
    return {"message": "博士生精神状态监测站 - 后端运行中！"}


# --- 新增：获取单日详细数据的接口 ---
@app.get("/day/{target_date}")
def get_day(target_date: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT study_time_seconds, ball_time_seconds, mood, summary FROM daily_records WHERE date=?",
                   (target_date,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {"study_time_seconds": row[0], "ball_time_seconds": row[1], "mood": row[2], "summary": row[3] or ""}
    else:
        # 如果当天还没数据，返回默认全0格式
        return {"study_time_seconds": 0, "ball_time_seconds": 0, "mood": "平静", "summary": ""}


# ... 下面的 get_stats 和 upload_image 保持不变 ...
@app.get("/stats/{target_date}")
def get_stats(target_date: str):
    year = target_date[:4]
    month = target_date[:7]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    def get_time_sums(condition, params):
        cursor.execute(f"SELECT SUM(study_time_seconds), SUM(ball_time_seconds) FROM daily_records WHERE {condition}",
                       params)
        res = cursor.fetchone()
        return {"study": res[0] or 0, "ball": res[1] or 0}

    def get_location_sums(condition, params):
        cursor.execute(f"SELECT SUM(clicks) FROM location_logs WHERE {condition}", params)
        res = cursor.fetchone()
        return res[0] or 0

    stats = {
        "study": {
            "today": get_time_sums("date = ?", (target_date,))["study"],
            "month": get_time_sums("date LIKE ?", (f"{month}%",))["study"],
            "year": get_time_sums("date LIKE ?", (f"{year}%",))["study"],
            "total": get_time_sums("1=1", ())["study"]
        },
        "ball": {
            "today": get_time_sums("date = ?", (target_date,))["ball"],
            "month": get_time_sums("date LIKE ?", (f"{month}%",))["ball"],
            "year": get_time_sums("date LIKE ?", (f"{year}%",))["ball"],
            "total": get_time_sums("1=1", ())["ball"]
        },
        "location": {
            "today": get_location_sums("date = ?", (target_date,)),
            "month": get_location_sums("date LIKE ?", (f"{month}%",)),
            "year": get_location_sums("date LIKE ?", (f"{year}%",)),
            "total": get_location_sums("1=1", ())
        }
    }
    conn.close()
    return stats


@app.post("/update_day/")
async def update_day(data: DailyRecordUpdate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO daily_records (date, study_time_seconds, ball_time_seconds, mood, summary)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET 
        study_time_seconds=excluded.study_time_seconds, 
        ball_time_seconds=excluded.ball_time_seconds, 
        mood=excluded.mood,
        summary=excluded.summary
    ''', (data.date, data.study_time_seconds, data.ball_time_seconds, data.mood, data.summary))
    conn.commit()
    conn.close()
    return {"status": "success"}