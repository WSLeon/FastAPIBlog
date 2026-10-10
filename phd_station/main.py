import os
import sqlite3
import shutil
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


# --- 数据模型 ---
class DailyRecordUpdate(BaseModel):
    date: str
    study_time_seconds: int
    ball_time_seconds: int
    mood: str
    summary: str = ""


class CheckinRequest(BaseModel):
    location_id: int
    date: str


class TaskCreate(BaseModel):
    title: str
    category: str = "科研"
    priority: str = "中"
    status: str = "todo"
    due_date: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None


class DiaryCreate(BaseModel):
    date: str
    title: str
    content: str
    tag: str = "文献笔记"
    mood: str = "努力"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 每日记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_records (
            date TEXT PRIMARY KEY,
            mood TEXT,
            study_time_seconds INTEGER DEFAULT 0,
            ball_time_seconds INTEGER DEFAULT 0,
            cat_clicks INTEGER DEFAULT 0,
            dog_clicks INTEGER DEFAULT 0,
            summary TEXT DEFAULT ''
        )
    ''')

    try:
        cursor.execute("ALTER TABLE daily_records ADD COLUMN summary TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # 地点定义表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            icon TEXT
        )
    ''')

    # 地点打卡日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS location_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            location_id INTEGER,
            clicks INTEGER DEFAULT 0,
            FOREIGN KEY (location_id) REFERENCES locations (id),
            UNIQUE(date, location_id)
        )
    ''')

    # 初始化默认地点（Emoji 图标）
    default_locations = [
        ('图书馆', '📚'),
        ('实验室', '💡'),
        ('咖啡厅', '☕'),
        ('家里', '🏠'),
        ('羽毛球馆', '🏸')
    ]
    for name, icon in default_locations:
        cursor.execute("SELECT id FROM locations WHERE name=?", (name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO locations (name, icon) VALUES (?, ?)", (name, icon))
        else:
            cursor.execute("UPDATE locations SET icon=? WHERE name=?", (icon, name))

    # 任务看板表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT '科研',
            priority TEXT DEFAULT '中',
            status TEXT DEFAULT 'todo',
            due_date TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    ''')

    # 学术日记表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tag TEXT DEFAULT '实验记录',
            mood TEXT DEFAULT '努力',
            created_at TEXT NOT NULL
        )
    ''')

    # 若任务表为空，插入几条博士生的初始引导任务
    cursor.execute('SELECT COUNT(*) FROM tasks')
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        today_str = datetime.now().strftime("%Y-%m-%d")
        sample_tasks = [
            ('精读顶会论文核心实验章节', '论文写作', '高', 'todo', today_str, now_str),
            ('跑完 Baseline 调参代码', '科研', '高', 'in_progress', today_str, now_str),
            ('羽毛球高远球对抗 1 小时（解压）', '运动生活', '中', 'todo', today_str, now_str),
            ('完成周报与组会 PPT 整理', '组会汇报', '中', 'done', today_str, now_str),
        ]
        cursor.executemany(
            'INSERT INTO tasks (title, category, priority, status, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            sample_tasks
        )

    # 若日记表为空，插入一条初始引导日记
    cursor.execute('SELECT COUNT(*) FROM diaries')
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        today_str = datetime.now().strftime("%Y-%m-%d")
        sample_diary = (
            today_str,
            '学术渡劫第一天：保持心平气和',
            '今天正式启用学术渡劫站！\n科研是马拉松不是短跑，读文献、写代码时保持专注，烦躁的时候去打球扣杀释放压力。\n不急不躁，稳扎稳打完成毕业大计。',
            '学术心悟',
            '努力',
            now_str
        )
        cursor.execute(
            'INSERT INTO diaries (date, title, content, tag, mood, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            sample_diary
        )

    conn.commit()
    conn.close()


init_db()


def format_seconds(seconds: int) -> str:
    if not seconds:
        return "0h"
    hours = round(seconds / 3600, 1)
    if hours.is_integer():
        return f"{int(hours)}h"
    return f"{hours}h"


# --- 路由定义 ---

@app.get("/")
def read_root():
    return {"message": "博士生精神状态监测站 - 后端运行中！"}


# 1. 单日记录查询
@app.get("/day/{target_date}")
def get_day(target_date: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT study_time_seconds, ball_time_seconds, mood, summary FROM daily_records WHERE date=?",
        (target_date,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "study_time_seconds": row[0] or 0,
            "ball_time_seconds": row[1] or 0,
            "mood": row[2] or "努力",
            "summary": row[3] or ""
        }
    else:
        return {
            "study_time_seconds": 0,
            "ball_time_seconds": 0,
            "mood": "努力",
            "summary": ""
        }


# 2. 单日记录保存/更新
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


# 3. 多周期聚合看板数据
@app.get("/stats/{target_date}")
def get_stats(target_date: str):
    year = target_date[:4]
    month = target_date[:7]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    def get_time_sums(condition, params):
        cursor.execute(
            f"SELECT SUM(study_time_seconds), SUM(ball_time_seconds) FROM daily_records WHERE {condition}",
            params
        )
        res = cursor.fetchone()
        return {"study": res[0] or 0, "ball": res[1] or 0}

    today_sums = get_time_sums("date = ?", (target_date,))
    month_sums = get_time_sums("date LIKE ?", (f"{month}%",))
    year_sums = get_time_sums("date LIKE ?", (f"{year}%",))
    total_sums = get_time_sums("1=1", ())

    # 地点聚合统计
    cursor.execute("SELECT id, name, icon FROM locations ORDER BY id ASC")
    loc_rows = cursor.fetchall()
    location_stats = []
    for loc_id, loc_name, loc_icon in loc_rows:
        # 当日点击
        cursor.execute("SELECT clicks FROM location_logs WHERE location_id=? AND date=?", (loc_id, target_date))
        today_row = cursor.fetchone()
        today_clicks = today_row[0] if today_row else 0

        # 当月点击
        cursor.execute("SELECT SUM(clicks) FROM location_logs WHERE location_id=? AND date LIKE ?", (loc_id, f"{month}%"))
        m_row = cursor.fetchone()
        month_clicks = m_row[0] if m_row and m_row[0] else 0

        # 累计总点击
        cursor.execute("SELECT SUM(clicks) FROM location_logs WHERE location_id=?", (loc_id,))
        t_row = cursor.fetchone()
        total_clicks = t_row[0] if t_row and t_row[0] else 0

        location_stats.append({
            "id": loc_id,
            "name": loc_name,
            "icon": loc_icon,
            "today": today_clicks,
            "month": month_clicks,
            "total": total_clicks
        })

    conn.close()

    return {
        "study": {
            "today": format_seconds(today_sums["study"]),
            "today_seconds": today_sums["study"],
            "month": format_seconds(month_sums["study"]),
            "year": format_seconds(year_sums["study"]),
            "total": format_seconds(total_sums["study"])
        },
        "ball": {
            "today": format_seconds(today_sums["ball"]),
            "today_seconds": today_sums["ball"],
            "month": format_seconds(month_sums["ball"]),
            "year": format_seconds(year_sums["ball"]),
            "total": format_seconds(total_sums["ball"])
        },
        "location": location_stats
    }


# 4. 地点一键打卡
@app.post("/locations/checkin/")
def checkin_location(req: CheckinRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO location_logs (date, location_id, clicks)
        VALUES (?, ?, 1)
        ON CONFLICT(date, location_id) DO UPDATE SET clicks = clicks + 1
    ''', (req.date, req.location_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


# 5. 月度全量日历数据（用于日历打点与状态可视化）
@app.get("/month_records/{year_month}")
def get_month_records(year_month: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, study_time_seconds, ball_time_seconds, mood, summary FROM daily_records WHERE date LIKE ?",
        (f"{year_month}%",)
    )
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for r in rows:
        result[r[0]] = {
            "study_time_seconds": r[1] or 0,
            "ball_time_seconds": r[2] or 0,
            "mood": r[3] or "努力",
            "summary": r[4] or ""
        }
    return result


# 6. 任务管理 CRUD
@app.get("/tasks/")
def get_tasks():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category, priority, status, due_date, created_at FROM tasks ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    tasks = []
    for r in rows:
        tasks.append({
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "priority": r[3],
            "status": r[4],
            "due_date": r[5] or "",
            "created_at": r[6]
        })
    return tasks


@app.post("/tasks/")
def create_task(task: TaskCreate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO tasks (title, category, priority, status, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (task.title, task.category, task.priority, task.status, task.due_date, now_str)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": task_id, "status": "success"}


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    updates = []
    params = []
    if task.title is not None:
        updates.append("title = ?")
        params.append(task.title)
    if task.category is not None:
        updates.append("category = ?")
        params.append(task.category)
    if task.priority is not None:
        updates.append("priority = ?")
        params.append(task.priority)
    if task.status is not None:
        updates.append("status = ?")
        params.append(task.status)
    if task.due_date is not None:
        updates.append("due_date = ?")
        params.append(task.due_date)

    if updates:
        params.append(task_id)
        cursor.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return {"status": "success"}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


# 7. 学术日记 CRUD
@app.get("/diaries/")
def get_diaries():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, title, content, tag, mood, created_at FROM diaries ORDER BY date DESC, id DESC")
    rows = cursor.fetchall()
    conn.close()

    diaries = []
    for r in rows:
        diaries.append({
            "id": r[0],
            "date": r[1],
            "title": r[2],
            "content": r[3],
            "tag": r[4],
            "mood": r[5],
            "created_at": r[6]
        })
    return diaries


@app.post("/diaries/")
def create_diary(diary: DiaryCreate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO diaries (date, title, content, tag, mood, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (diary.date, diary.title, diary.content, diary.tag, diary.mood, now_str)
    )
    diary_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": diary_id, "status": "success"}


@app.delete("/diaries/{diary_id}")
def delete_diary(diary_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM diaries WHERE id = ?", (diary_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


# 8. 附件上传
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"/uploads/{filename}", "filename": filename}