# 🎓 博士生精神状态监测站 (PhD Survival Station)
### —— 学术渡劫自救工作台 · 科研与生活平衡面板

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.5+-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-8.0+-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<br/>

**“科研与羽毛球并重，不生气不摸鱼。”**  
专为博士生、科研学者与知识工作者打造的极简、轻量、高颜值状态监控与时间管理面板。

</div>

---

## 📖 项目背景与愿景

读博是一场漫长的精神修行。文献读不完、实验总翻车、审稿人意见刁钻……常常陷入「今天好像忙了一整天，又好像什么都没做」的精神内耗。

**博士生精神状态监测站（学术渡劫站）** 由此而生。它致力于消除繁重的打卡负担，以**极低阻力、无感记录**为核心哲学，帮助你：
- 🔬 记录真实的**科研专注时间**，看得到自己的每一步脚印；
- 🏸 捍卫属于自己的**运动解压时间**（如羽毛球扣杀），科研要搞，身体也要保；
- 🎭 敏锐捕捉**当下心理情绪**，及时调整心态，避免严重内耗；
- 📅 随时**复盘与补录**历史轨迹，沉淀属于自己的学术长征日志。

---

## ✨ 核心特性

- **⏱️ 实时科研专注秒表 (Deep Work Timer)**
  - 一键开启/结束科研专注倒计时。
  - 结束时**自动无感累加**写入当天数据库，杜绝繁琐手动记录步骤。
- **🏸 科研 × 运动双轨并行追踪**
  - 不仅统计科研时长，同时记录羽毛球等解压运动时长。
  - 平衡科研与生命体征，健康毕业才是终极胜利。
- **🎭 当下心境即时打卡 (Instant Mood Tracking)**
  - 预设 6 大学术心境：`糟糕`、`忙碌`、`开心`、`平静`、`努力`、`摸鱼`。
  - 单击即时切换并**静默保存**至云端/本地数据库，无需弹窗打扰。
- **📝 今日简短复盘与学术日记 (Daily Retro)**
  - 醒目的复盘卡片，支持随时记录今天读了什么文献、跑了哪些实验、有哪些教训与灵感。
- **📊 多维聚合成果看板 (Stats Dashboard)**
  - 支持 **今日 / 本月 / 本年 / 历史总计** 四个时间维度的科研专注与运动解压时长看板。
  - 一键展开/收起年度与总计数据，让学术成果量化可见。
- **📍 地点驻留统计 (Location Presence)**
  - 记录与统计图书馆、实验室、咖啡厅、家里等不同科研主场的驻留频次。
- **📅 交互式学术日历与历史补录 (Interactive Calendar)**
  - 月视图可视化日历，智能标注当月日期与“今日”高亮。
  - 点击任意过去日期即可唤起**补录与修改弹窗**，随时调整历史科研时长、运动时长、心境与复盘总结。

---

## 🛠 技术栈

### 后端 (Backend)
- **框架**: [FastAPI](https://fastapi.tiangolo.com/) (现代、快速、高性能的 Python Web 框架)
- **数据库**: SQLite3（轻量、免额外配置、开箱即用，支持 schema 无损自动升级）
- **数据验证**: [Pydantic v2](https://docs.pydantic.dev/)
- **服务网关**: [Uvicorn](https://www.uvicorn.org/) (ASGI 服务器)

### 前端 (Frontend)
- **框架**: [Vue 3](https://vuejs.org/) (Composition API / `<script setup>`)
- **构建工具**: [Vite 8](https://vitejs.dev/)
- **样式方案**: [Tailwind CSS v4](https://tailwindcss.com/)
- **网络通信**: [Axios](https://axios-http.com/)

---

## 📂 目录结构

```text
FastAPIBlog/
├── main.py                     # 项目根入口（便捷启动 FastAPI 服务）
├── test_main.http              # HTTP Client API 测试套件
├── requirements.txt            # Python 后端依赖清单
├── .gitignore                  # Git 忽略配置
├── README.md                   # 项目使用与说明文档
│
└── phd_station/                # 博士生精神状态监测站核心目录
    ├── main.py                 # FastAPI 后端核心业务路由与 SQLite 逻辑
    ├── phd_survival.db         # SQLite 数据库文件 (自动创建/管理)
    ├── uploads/                # 附件/文件上传目录
    │
    └── frontend/               # Vue 3 前端工程
        ├── index.html          # 前端 HTML 入口
        ├── package.json        # 前端依赖配置
        ├── vite.config.js      # Vite 配置文件
        ├── tailwind.config.js  # Tailwind 配置
        └── src/
            ├── App.vue         # 监测站主页面及完整交互组件
            ├── main.js         # 前端入口文件
            └── style.css       # 全局样式
```

---

## 🚀 快速上手

### 1. 克隆代码仓库
```bash
git clone https://github.com/WSLeon/phd-survival-station.git
cd phd-survival-station
```

### 2. 启动后端 (Python + FastAPI)

推荐在虚拟环境中运行：

```bash
# 1. 创建并激活虚拟环境 (可选)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 启动 FastAPI 服务
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

> 💡 启动成功后可访问接口文档：
> - Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
> - ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3. 启动前端 (Vue 3 + Vite)

另开一个终端窗口：

```bash
cd phd_station/frontend

# 1. 安装前端依赖
npm install

# 2. 启动开发服务器
npm run dev
```

浏览器打开输出的本地地址（通常为 [http://localhost:5173/](http://localhost:5173/)），即可开始使用！

---

## 📡 接口概览

| 请求方法 | 接口路径 | 说明 |
| :--- | :--- | :--- |
| `GET` | `/` | 状态检查（返回运行状态） |
| `GET` | `/day/{target_date}` | 获取指定日期（格式：`YYYY-MM-DD`）的科研时长、运动时长、心情与总结 |
| `GET` | `/stats/{target_date}` | 获取截至该日期的今日、本月、本年、累计总时长与地点驻留聚合统计 |
| `POST` | `/update_day/` | 增量更新或录入某一天的记录（时长、心境、总结） |
| `GET` | `/uploads/{file_name}` | 静态附件访问 |

---

## 🗺️ 后续路线图 (Roadmap)

- [ ] **任务管理看板 (Task Kanban)**：针对论文写作、审稿修回与实验批次的分阶段任务管理。
- [ ] **学术日记归档 (Diary Archive)**：支持 Markdown 格式的长文学术日记写作与导出（PDF/Markdown）。
- [ ] **数据可视化图表**：接入 ECharts / Chart.js，展示科研专注时长与羽毛球运动周/月趋势热力图。
- [ ] **多设备同步与云备份**：支持轻量级账号系统或本地数据导入导出。
- [ ] **Docker 容器化**：提供一键部署 Docker Compose 配置。

---

## 🤝 参与贡献

欢迎对学术生活同样充满热情的同学们提交 Issue 或 PR！
1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
祝愿每一位科研汪都能论文顺利发，心态平稳，健康毕业！🎉
