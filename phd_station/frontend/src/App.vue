<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const api = axios.create({ baseURL: 'http://127.0.0.1:8000' })

// --- 全局状态 ---
const activeTab = ref('monitor')
const currentDateStr = ref(new Date().toLocaleString('zh-CN', { dateStyle: 'full', timeStyle: 'short' }))

// Toast 轻提示系统
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null
const showToast = (message, type = 'success') => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => {
    toast.value.show = false
  }, 2500)
}

// 本地时区 YYYY-MM-DD
const getTodayStr = () => {
  const today = new Date()
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
}

// ==================== 1. 监测中心状态与逻辑 ====================
const currentMood = ref('努力')
const dailySummary = ref('')
const isSummaryModalOpen = ref(false)

// 统计看板数据
const showFullStats = ref(false)
const stats = ref({
  study: { today: '0h', month: '0h', year: '0h', total: '0h' },
  ball: { today: '0h', month: '0h', year: '0h', total: '0h' },
  location: [
    { id: 1, name: '图书馆', icon: '📚', today: 0, month: 0, total: 0 },
    { id: 2, name: '实验室', icon: '💡', today: 0, month: 0, total: 0 },
    { id: 3, name: '咖啡厅', icon: '☕', today: 0, month: 0, total: 0 },
    { id: 4, name: '家里', icon: '🏠', today: 0, month: 0, total: 0 },
    { id: 5, name: '羽毛球馆', icon: '🏸', today: 0, month: 0, total: 0 }
  ]
})

// 加载今日数据
const loadTodayData = async () => {
  try {
    const todayStr = getTodayStr()
    const res = await api.get(`/day/${todayStr}`)
    if (res.data) {
      if (res.data.mood) currentMood.value = res.data.mood
      if (res.data.summary !== undefined) dailySummary.value = res.data.summary
    }
  } catch (err) {
    console.error('加载今日数据失败:', err)
  }
}

// 加载看板统计
const loadStats = async () => {
  try {
    const todayStr = getTodayStr()
    const res = await api.get(`/stats/${todayStr}`)
    if (res.data) {
      if (res.data.study) stats.value.study = res.data.study
      if (res.data.ball) stats.value.ball = res.data.ball
      if (res.data.location && Array.isArray(res.data.location)) {
        stats.value.location = res.data.location
      }
    }
  } catch (err) {
    console.error('加载看板统计失败:', err)
  }
}

// 地点一键打卡
const checkinLocation = async (loc) => {
  try {
    const todayStr = getTodayStr()
    await api.post('/locations/checkin/', { location_id: loc.id, date: todayStr })
    showToast(`📍 在 [${loc.name}] 打卡成功！驻留 +1`)
    await loadStats()
  } catch (err) {
    console.error('打卡失败:', err)
    showToast('打卡失败，请检查网络或后端服务', 'error')
  }
}

// 保存今日总结
const saveTodaySummary = async () => {
  try {
    const todayStr = getTodayStr()
    const res = await api.get(`/day/${todayStr}`)
    const payload = {
      date: todayStr,
      study_time_seconds: res.data.study_time_seconds || 0,
      ball_time_seconds: res.data.ball_time_seconds || 0,
      mood: currentMood.value,
      summary: dailySummary.value
    }
    await api.post('/update_day/', payload)
    isSummaryModalOpen.value = false
    showToast('📝 今日学术复盘已保存！')
    await loadMonthRecords()
  } catch (error) {
    console.error(error)
    showToast('保存失败，请稍后重试', 'error')
  }
}

// 瞬间切换心情
const updateMoodInstantly = async (m) => {
  currentMood.value = m
  try {
    const todayStr = getTodayStr()
    const res = await api.get(`/day/${todayStr}`)
    const payload = {
      date: todayStr,
      study_time_seconds: res.data.study_time_seconds || 0,
      ball_time_seconds: res.data.ball_time_seconds || 0,
      mood: m,
      summary: res.data.summary || dailySummary.value
    }
    await api.post('/update_day/', payload)
    showToast(`当下心情已更新为【${m}】`)
    await loadMonthRecords()
  } catch (error) {
    console.error('心情自动保存失败', error)
  }
}

// --- 实时专注计时器（支持科研专注 / 羽毛球运动双模式）---
const timerMode = ref('study') // 'study' | 'ball'
const isTimerRunning = ref(false)
const timerSeconds = ref(0)
let timerInterval = null

const formattedTimer = computed(() => {
  const h = String(Math.floor(timerSeconds.value / 3600)).padStart(2, '0')
  const m = String(Math.floor((timerSeconds.value % 3600) / 60)).padStart(2, '0')
  const s = String(timerSeconds.value % 60).padStart(2, '0')
  return `${h}:${m}:${s}`
})

const toggleTimer = async () => {
  if (isTimerRunning.value) {
    clearInterval(timerInterval)
    isTimerRunning.value = false

    try {
      const todayStr = getTodayStr()
      const res = await api.get(`/day/${todayStr}`)
      const currentStudy = res.data.study_time_seconds || 0
      const currentBall = res.data.ball_time_seconds || 0

      const payload = {
        date: todayStr,
        study_time_seconds: timerMode.value === 'study' ? currentStudy + timerSeconds.value : currentStudy,
        ball_time_seconds: timerMode.value === 'ball' ? currentBall + timerSeconds.value : currentBall,
        mood: res.data.mood || currentMood.value,
        summary: res.data.summary || dailySummary.value
      }

      await api.post('/update_day/', payload)
      const minutes = Math.max(1, Math.floor(timerSeconds.value / 60))
      const modeName = timerMode.value === 'study' ? '科研专注' : '羽毛球解压'
      showToast(`🎉 计时结束！已自动为您累加 ${minutes} 分钟 ${modeName} 时长！`)
      timerSeconds.value = 0
      await loadStats()
      await loadMonthRecords()
    } catch (err) {
      console.error(err)
      showToast('自动保存失败，请检查后端', 'error')
    }
  } else {
    isTimerRunning.value = true
    timerInterval = setInterval(() => {
      timerSeconds.value++
    }, 1000)
  }
}

// --- 日历生成与打点逻辑 ---
const viewDate = ref(new Date())
const daysOfWeek = ['日', '一', '二', '三', '四', '五', '六']
const monthRecords = ref({})

const loadMonthRecords = async () => {
  try {
    const year = viewDate.value.getFullYear()
    const month = String(viewDate.value.getMonth() + 1).padStart(2, '0')
    const res = await api.get(`/month_records/${year}-${month}`)
    monthRecords.value = res.data || {}
  } catch (err) {
    console.error('加载月度打点数据失败:', err)
  }
}

const calendarDays = computed(() => {
  const year = viewDate.value.getFullYear()
  const month = viewDate.value.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const lastDate = new Date(year, month + 1, 0).getDate()

  let days = []
  for (let i = 0; i < firstDay; i++) days.push({ day: '', currentMonth: false })
  for (let d = 1; d <= lastDate; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const record = monthRecords.value[dateStr]
    days.push({
      day: d,
      currentMonth: true,
      fullDate: dateStr,
      isToday: getTodayStr() === dateStr,
      hasRecord: Boolean(record && (record.study_time_seconds > 0 || record.ball_time_seconds > 0 || record.summary)),
      record: record || null
    })
  }
  return days
})

const changeMonth = async (step) => {
  viewDate.value = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth() + step, 1)
  await loadMonthRecords()
}

// 日历弹窗修改
const isEditModalOpen = ref(false)
const selectedDayData = ref({ date: '', study_h: 0, study_m: 0, ball_h: 0, ball_m: 0, mood: '', summary: '' })

const openEditModal = async (item) => {
  if (!item.currentMonth) return
  try {
    const res = await api.get(`/day/${item.fullDate}`)
    selectedDayData.value = {
      date: item.fullDate,
      study_h: Math.floor((res.data.study_time_seconds || 0) / 3600),
      study_m: Math.floor(((res.data.study_time_seconds || 0) % 3600) / 60),
      ball_h: Math.floor((res.data.ball_time_seconds || 0) / 3600),
      ball_m: Math.floor(((res.data.ball_time_seconds || 0) % 3600) / 60),
      mood: res.data.mood || '努力',
      summary: res.data.summary || ''
    }
    isEditModalOpen.value = true
  } catch (e) {
    console.error('获取历史数据失败', e)
    showToast('拉取历史数据失败', 'error')
  }
}

const saveDailyData = async () => {
  try {
    const studySeconds = (Number(selectedDayData.value.study_h) || 0) * 3600 + (Number(selectedDayData.value.study_m) || 0) * 60
    const ballSeconds = (Number(selectedDayData.value.ball_h) || 0) * 3600 + (Number(selectedDayData.value.ball_m) || 0) * 60
    const payload = {
      date: selectedDayData.value.date,
      study_time_seconds: studySeconds,
      ball_time_seconds: ballSeconds,
      mood: selectedDayData.value.mood,
      summary: selectedDayData.value.summary
    }
    await api.post('/update_day/', payload)
    isEditModalOpen.value = false
    showToast('✅ 历史记录已成功覆盖更新！')
    await loadMonthRecords()
    await loadStats()
    if (selectedDayData.value.date === getTodayStr()) {
      await loadTodayData()
    }
  } catch (error) {
    console.error(error)
    showToast('保存历史记录失败', 'error')
  }
}

// ==================== 2. 任务管理模块 ====================
const tasks = ref([])
const taskFilter = ref('all') // 'all' | 'todo' | 'in_progress' | 'done'
const isTaskModalOpen = ref(false)
const newTask = ref({
  title: '',
  category: '科研',
  priority: '高',
  due_date: getTodayStr(),
  status: 'todo'
})

const loadTasks = async () => {
  try {
    const res = await api.get('/tasks/')
    tasks.value = res.data || []
  } catch (err) {
    console.error('加载任务失败:', err)
  }
}

const filteredTasks = computed(() => {
  if (taskFilter.value === 'all') return tasks.value
  return tasks.value.filter(t => t.status === taskFilter.value)
})

const taskStats = computed(() => {
  const total = tasks.value.length
  const done = tasks.value.filter(t => t.status === 'done').length
  const inProgress = tasks.value.filter(t => t.status === 'in_progress').length
  const todo = tasks.value.filter(t => t.status === 'todo').length
  return { total, done, inProgress, todo }
})

const openCreateTaskModal = () => {
  newTask.value = {
    title: '',
    category: '科研',
    priority: '高',
    due_date: getTodayStr(),
    status: 'todo'
  }
  isTaskModalOpen.value = true
}

const submitCreateTask = async () => {
  if (!newTask.value.title.trim()) {
    showToast('请输入任务名称', 'error')
    return
  }
  try {
    await api.post('/tasks/', newTask.value)
    isTaskModalOpen.value = false
    showToast('🎯 任务创建成功！')
    await loadTasks()
  } catch (err) {
    console.error(err)
    showToast('创建任务失败', 'error')
  }
}

const toggleTaskStatus = async (task) => {
  const nextStatus = task.status === 'done' ? 'todo' : 'done'
  try {
    await api.put(`/tasks/${task.id}`, { status: nextStatus })
    task.status = nextStatus
    showToast(nextStatus === 'done' ? '🎉 恭喜完成任务！' : '任务已重置为待办')
  } catch (err) {
    console.error(err)
    showToast('更新状态失败', 'error')
  }
}

const updateTaskProgress = async (task, status) => {
  try {
    await api.put(`/tasks/${task.id}`, { status })
    task.status = status
    showToast(`任务状态变更为【${status === 'in_progress' ? '进行中' : status === 'done' ? '已完成' : '待办'}】`)
  } catch (err) {
    console.error(err)
    showToast('更新状态失败', 'error')
  }
}

const deleteTask = async (taskId) => {
  if (!confirm('确定删除该任务吗？')) return
  try {
    await api.delete(`/tasks/${taskId}`)
    tasks.value = tasks.value.filter(t => t.id !== taskId)
    showToast('任务已删除')
  } catch (err) {
    console.error(err)
    showToast('删除任务失败', 'error')
  }
}

// ==================== 3. 学术日记模块 ====================
const diaries = ref([])
const isDiaryModalOpen = ref(false)
const newDiary = ref({
  title: '',
  date: getTodayStr(),
  tag: '实验心得',
  mood: '努力',
  content: ''
})

const loadDiaries = async () => {
  try {
    const res = await api.get('/diaries/')
    diaries.value = res.data || []
  } catch (err) {
    console.error('加载日记失败:', err)
  }
}

const openCreateDiaryModal = () => {
  newDiary.value = {
    title: '',
    date: getTodayStr(),
    tag: '实验心得',
    mood: currentMood.value,
    content: ''
  }
  isDiaryModalOpen.value = true
}

const submitCreateDiary = async () => {
  if (!newDiary.value.title.trim()) {
    showToast('请输入日记标题', 'error')
    return
  }
  if (!newDiary.value.content.trim()) {
    showToast('请输入日记正文', 'error')
    return
  }
  try {
    await api.post('/diaries/', newDiary.value)
    isDiaryModalOpen.value = false
    showToast('📖 学术日记发布成功！')
    await loadDiaries()
  } catch (err) {
    console.error(err)
    showToast('发布日记失败', 'error')
  }
}

const deleteDiary = async (diaryId) => {
  if (!confirm('确定删除这篇日记吗？')) return
  try {
    await api.delete(`/diaries/${diaryId}`)
    diaries.value = diaries.value.filter(d => d.id !== diaryId)
    showToast('日记已删除')
  } catch (err) {
    console.error(err)
    showToast('删除日记失败', 'error')
  }
}

// ==================== 页面挂载初始化 ====================
onMounted(async () => {
  setInterval(() => {
    currentDateStr.value = new Date().toLocaleString('zh-CN', { dateStyle: 'full', timeStyle: 'short' })
  }, 1000)

  await loadTodayData()
  await loadStats()
  await loadMonthRecords()
  await loadTasks()
  await loadDiaries()
})
</script>

<template>
  <div class="flex h-screen bg-slate-50 font-sans text-gray-800 relative selection:bg-purple-200">

    <!-- 轻提示 (Toast) -->
    <div v-if="toast.show"
         :class="['fixed top-6 right-8 z-[100] px-5 py-3 rounded-2xl shadow-xl flex items-center gap-3 text-sm font-bold text-white transition-all transform animate-in slide-in-from-top-4',
                  toast.type === 'error' ? 'bg-red-500 shadow-red-200' : 'bg-purple-600 shadow-purple-200']">
      <span>{{ toast.type === 'error' ? '⚠️' : '✨' }}</span>
      <span>{{ toast.message }}</span>
    </div>

    <!-- 左侧导航侧边栏 -->
    <aside class="w-64 bg-white shadow-xl flex flex-col pt-8 z-10 border-r border-purple-50">
      <div class="px-8 pb-8 border-b border-gray-100 mb-6 text-center">
        <div class="inline-flex items-center justify-center w-12 h-12 bg-purple-100 text-purple-600 rounded-2xl text-2xl mb-3 shadow-inner">
          🎓
        </div>
        <h2 class="text-2xl font-black bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent tracking-tight">
          学术渡劫站
        </h2>
        <p class="text-[10px] text-gray-400 mt-1 uppercase tracking-widest font-mono">PHD Survival Station</p>
      </div>

      <nav class="flex-1 px-4 space-y-2">
        <button @click="activeTab = 'monitor'"
                :class="['w-full text-left px-5 py-3.5 rounded-2xl transition-all flex items-center gap-3 font-bold',
                         activeTab === 'monitor' ? 'bg-purple-600 text-white shadow-lg shadow-purple-200 scale-[1.02]' : 'text-gray-500 hover:bg-purple-50 hover:text-purple-600']">
          <span class="text-xl">🚀</span>
          <span>监测中心</span>
        </button>

        <button @click="activeTab = 'task'"
                :class="['w-full text-left px-5 py-3.5 rounded-2xl transition-all flex items-center justify-between font-bold',
                         activeTab === 'task' ? 'bg-purple-600 text-white shadow-lg shadow-purple-200 scale-[1.02]' : 'text-gray-500 hover:bg-purple-50 hover:text-purple-600']">
          <div class="flex items-center gap-3">
            <span class="text-xl">📝</span>
            <span>任务看板</span>
          </div>
          <span v-if="taskStats.todo > 0"
                :class="['text-xs px-2 py-0.5 rounded-full font-mono',
                         activeTab === 'task' ? 'bg-white text-purple-600 font-bold' : 'bg-purple-100 text-purple-600']">
            {{ taskStats.todo }}
          </span>
        </button>

        <button @click="activeTab = 'diary'"
                :class="['w-full text-left px-5 py-3.5 rounded-2xl transition-all flex items-center justify-between font-bold',
                         activeTab === 'diary' ? 'bg-purple-600 text-white shadow-lg shadow-purple-200 scale-[1.02]' : 'text-gray-500 hover:bg-purple-50 hover:text-purple-600']">
          <div class="flex items-center gap-3">
            <span class="text-xl">📖</span>
            <span>学术日记</span>
          </div>
          <span class="text-xs px-2 py-0.5 rounded-full font-mono opacity-80"
                :class="activeTab === 'diary' ? 'bg-white text-purple-600 font-bold' : 'bg-gray-100 text-gray-500'">
            {{ diaries.length }}
          </span>
        </button>
      </nav>

      <!-- 底部励志语录 -->
      <div class="p-5 m-4 bg-purple-50/70 rounded-2xl border border-purple-100">
        <p class="text-[11px] font-bold text-purple-700 leading-relaxed">💡 “保持热爱，奔赴山海。论文虽虐，心态要稳。”</p>
      </div>
    </aside>

    <!-- 主展示区 -->
    <main class="flex-1 p-8 overflow-y-auto">

      <!-- ====================== TAB 1: 监测中心 ====================== -->
      <div v-if="activeTab === 'monitor'" class="max-w-6xl mx-auto space-y-6 animate-in fade-in">

        <header class="flex justify-between items-end mb-2">
          <div>
            <h1 class="text-3xl font-extrabold text-gray-900 tracking-tight">欢迎回来，博士。</h1>
            <p class="text-gray-500 mt-1.5 text-sm">今日目标：科研与羽毛球并重，拒绝内耗，稳定产出。</p>
          </div>
          <div class="text-right">
            <p class="text-xs text-gray-400 font-mono bg-white px-3 py-1.5 rounded-xl border border-gray-100 shadow-sm">
              🕒 {{ currentDateStr }}
            </p>
          </div>
        </header>

        <!-- 心情与复盘区 -->
        <div class="flex gap-6 h-48">
          <div @click="isSummaryModalOpen = true"
               class="flex-1 bg-white rounded-3xl shadow-sm p-7 border border-transparent hover:border-purple-200 hover:shadow-md cursor-pointer transition-all group relative overflow-hidden flex flex-col">
            <div class="flex justify-between items-center mb-3">
              <h3 class="text-sm font-bold text-gray-600 flex items-center gap-2">
                <span>📝</span> 今日简短复盘
              </h3>
              <span class="text-purple-600 bg-purple-50 px-3 py-1 rounded-full text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                ✏️ 点击撰写 / 修改
              </span>
            </div>

            <div class="flex-1 overflow-y-auto pr-2 custom-scrollbar">
              <p v-if="dailySummary" class="text-gray-700 whitespace-pre-wrap leading-relaxed text-sm">
                {{ dailySummary }}
              </p>
              <div v-else class="h-full flex items-center justify-center border-2 border-dashed border-gray-100 rounded-2xl group-hover:border-purple-100 transition">
                <p class="text-gray-400 italic text-sm">今天科研有何进展？羽毛球扣杀帅吗？点击这里写下今天的总结...</p>
              </div>
            </div>
          </div>

          <div class="w-32 bg-white rounded-3xl shadow-sm p-4 border border-purple-50 flex flex-col justify-between">
            <h3 class="text-[11px] font-bold text-gray-400 text-center uppercase tracking-wider">当下心境</h3>
            <div class="grid grid-cols-2 gap-1.5 flex-1 items-center">
              <button v-for="m in ['糟糕', '忙碌', '开心', '平静', '努力', '摸鱼']" :key="m"
                      @click="updateMoodInstantly(m)"
                      :class="['py-2 rounded-xl text-xs font-bold transition-all border text-center',
                               currentMood === m ? 'bg-purple-600 text-white border-purple-600 shadow-md scale-105' : 'border-gray-100 text-gray-500 hover:border-purple-200 hover:bg-purple-50']">
                {{ m }}
              </button>
            </div>
          </div>
        </div>

        <!-- 成果看板 -->
        <section class="bg-white rounded-3xl shadow-sm p-7 transition-all">
          <div class="flex justify-between items-center mb-5">
            <div class="flex items-center gap-2">
              <span class="text-xl">📊</span>
              <h3 class="text-lg font-bold text-gray-800">成果看板</h3>
            </div>
            <button @click="showFullStats = !showFullStats" class="text-purple-600 text-sm font-bold hover:underline">
              {{ showFullStats ? '收起详情 ▲' : '查看年度/总计 ▼' }}
            </button>
          </div>

          <div class="grid grid-cols-3 gap-6">
            <!-- 科研专注看板 -->
            <div class="bg-gradient-to-br from-purple-600 to-indigo-700 text-white p-6 rounded-2xl shadow-lg shadow-purple-100 relative overflow-hidden">
              <div class="relative z-10">
                <p class="text-purple-200 text-xs font-bold uppercase tracking-wider">🔬 科研专注</p>
                <div class="flex items-baseline gap-2 mt-2">
                  <p class="text-4xl font-black font-mono">{{ stats.study.today }}</p>
                  <p class="text-xs opacity-75">/ 今日</p>
                </div>
                <div class="mt-4 pt-3 border-t border-purple-400/30">
                  <p class="text-xs">本月累计：<span class="font-bold font-mono">{{ stats.study.month }}</span></p>
                  <div v-if="showFullStats" class="mt-2 space-y-1 text-xs text-purple-200 animate-in">
                    <p>本年累计：<span class="font-bold text-white font-mono">{{ stats.study.year }}</span></p>
                    <p>历史总计：<span class="font-bold text-white font-mono">{{ stats.study.total }}</span></p>
                  </div>
                </div>
              </div>
              <span class="absolute -right-4 -bottom-4 text-8xl opacity-10 select-none">🔬</span>
            </div>

            <!-- 羽毛球解压看板 -->
            <div class="bg-gradient-to-br from-orange-500 to-amber-600 text-white p-6 rounded-2xl shadow-lg shadow-orange-100 relative overflow-hidden">
              <div class="relative z-10">
                <p class="text-orange-100 text-xs font-bold uppercase tracking-wider">🏸 羽毛球解压</p>
                <div class="flex items-baseline gap-2 mt-2">
                  <p class="text-4xl font-black font-mono">{{ stats.ball.today }}</p>
                  <p class="text-xs opacity-75">/ 今日</p>
                </div>
                <div class="mt-4 pt-3 border-t border-orange-400/30">
                  <p class="text-xs">本月累计：<span class="font-bold font-mono">{{ stats.ball.month }}</span></p>
                  <div v-if="showFullStats" class="mt-2 space-y-1 text-xs text-orange-200 animate-in">
                    <p>本年累计：<span class="font-bold text-white font-mono">{{ stats.ball.year }}</span></p>
                    <p>历史总计：<span class="font-bold text-white font-mono">{{ stats.ball.total }}</span></p>
                  </div>
                </div>
              </div>
              <span class="absolute -right-4 -bottom-4 text-8xl opacity-10 select-none">🏸</span>
            </div>

            <!-- 地点打卡与驻留统计 -->
            <div class="bg-gradient-to-br from-emerald-600 to-teal-700 text-white p-5 rounded-2xl shadow-lg shadow-emerald-100 relative overflow-hidden flex flex-col justify-between">
              <div class="relative z-10">
                <div class="flex justify-between items-center mb-3">
                  <p class="text-emerald-100 text-xs font-bold uppercase tracking-wider">📍 地点驻留（点击打卡）</p>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <div v-for="loc in stats.location" :key="loc.name"
                       @click="checkinLocation(loc)"
                       class="bg-emerald-700/40 hover:bg-emerald-700/70 cursor-pointer transition rounded-xl p-2.5 backdrop-blur-sm border border-emerald-400/20 active:scale-95 group">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-sm">{{ loc.icon }} {{ loc.name }}</span>
                      <span class="text-[9px] bg-emerald-500/40 px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition">+1</span>
                    </div>
                    <div class="flex items-end gap-1">
                      <span class="text-lg font-black leading-none font-mono">{{ loc.today }}</span>
                      <span class="text-[9px] text-emerald-200">次 / 今日</span>
                    </div>
                    <p class="text-[10px] text-emerald-100 mt-1">本月: {{ loc.month }} 次</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 下方：日历与专注器 -->
        <div class="grid grid-cols-12 gap-8">
          <!-- 学术日历 -->
          <div class="col-span-7">
            <section class="bg-white rounded-3xl shadow-sm p-7 h-full relative">
              <div class="flex justify-between items-center mb-6">
                <div>
                  <h3 class="text-lg font-bold text-gray-800">
                    📅 {{ viewDate.getFullYear() }}年 {{ viewDate.getMonth() + 1 }}月
                  </h3>
                  <p class="text-xs text-gray-400 mt-0.5">点击日期查看详情或补录历史时长</p>
                </div>
                <div class="flex gap-2">
                  <button @click="changeMonth(-1)"
                          class="p-2 bg-gray-50 hover:bg-purple-100 rounded-xl text-purple-600 transition">◀
                  </button>
                  <button @click="changeMonth(1)"
                          class="p-2 bg-gray-50 hover:bg-purple-100 rounded-xl text-purple-600 transition">▶
                  </button>
                </div>
              </div>

              <div class="grid grid-cols-7 gap-2 text-center">
                <div v-for="day in daysOfWeek" :key="day" class="text-xs font-bold text-gray-400 pb-2">
                  {{ day }}
                </div>
                <div v-for="(item, index) in calendarDays" :key="index"
                     @click="openEditModal(item)"
                     :class="['aspect-square flex flex-col items-center justify-center rounded-2xl text-sm relative transition-all duration-200',
                              item.currentMonth ? 'hover:bg-purple-100 hover:scale-105 text-gray-700 bg-gray-50/70 cursor-pointer' : 'text-gray-200 pointer-events-none',
                              item.isToday ? '!bg-purple-600 !text-white shadow-md font-bold' : '']">
                  <span class="font-mono text-sm">{{ item.day }}</span>
                  <!-- 打点指示 -->
                  <div v-if="item.hasRecord" class="flex gap-1 mt-1">
                    <span class="w-1.5 h-1.5 rounded-full"
                          :class="item.isToday ? 'bg-white' : 'bg-purple-500'"></span>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- 实时专注器 -->
          <div class="col-span-5">
            <section class="bg-white rounded-3xl shadow-sm p-7 h-full flex flex-col justify-between">
              <div>
                <div class="flex justify-between items-center mb-6">
                  <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <span>⏱️</span> 实时计时器
                  </h3>
                  <!-- 模式切换 -->
                  <div class="flex bg-gray-100 p-1 rounded-xl">
                    <button @click="timerMode = 'study'"
                            :class="['px-3 py-1 text-xs font-bold rounded-lg transition',
                                     timerMode === 'study' ? 'bg-purple-600 text-white shadow-sm' : 'text-gray-500 hover:text-gray-800']">
                      🔬 科研
                    </button>
                    <button @click="timerMode = 'ball'"
                            :class="['px-3 py-1 text-xs font-bold rounded-lg transition',
                                     timerMode === 'ball' ? 'bg-orange-500 text-white shadow-sm' : 'text-gray-500 hover:text-gray-800']">
                      🏸 羽毛球
                    </button>
                  </div>
                </div>

                <div class="text-center py-6">
                  <p class="text-xs uppercase tracking-widest text-gray-400 font-bold mb-2">
                    {{ timerMode === 'study' ? '科研专注计时' : '羽毛球解压计时' }}
                  </p>
                  <p :class="['text-5xl font-mono tracking-wider transition-colors duration-300 font-black',
                             isTimerRunning ? (timerMode === 'study' ? 'text-purple-600 scale-105' : 'text-orange-500 scale-105') : 'text-gray-800']">
                    {{ formattedTimer }}
                  </p>
                </div>
              </div>

              <div class="space-y-3">
                <button @click="toggleTimer"
                        :class="['w-full py-4 rounded-2xl font-bold shadow-lg transition-all duration-300 active:scale-95 text-base flex items-center justify-center gap-2 text-white',
                                 isTimerRunning
                                   ? 'bg-rose-500 hover:bg-rose-600 shadow-rose-200 animate-pulse'
                                   : (timerMode === 'study' ? 'bg-purple-600 hover:bg-purple-700 shadow-purple-200' : 'bg-orange-500 hover:bg-orange-600 shadow-orange-200')]">
                  <span>{{ isTimerRunning ? '⏹ 结束并自动录入今日记录' : '▶ 开始计时' }}</span>
                </button>
                <p class="text-[11px] text-gray-400 text-center">
                  💡 停止计时后将自动累加至当日累计时长，无需繁琐录入。
                </p>
              </div>
            </section>
          </div>
        </div>

      </div>

      <!-- ====================== TAB 2: 任务看板 ====================== -->
      <div v-if="activeTab === 'task'" class="max-w-6xl mx-auto space-y-6 animate-in fade-in">
        <header class="flex justify-between items-center">
          <div>
            <h1 class="text-3xl font-extrabold text-gray-900 tracking-tight">学术任务管理</h1>
            <p class="text-gray-500 mt-1.5 text-sm">清晰划分阶段性科研任务，论文攻坚更有条理。</p>
          </div>
          <button @click="openCreateTaskModal"
                  class="bg-purple-600 hover:bg-purple-700 text-white font-bold px-5 py-3 rounded-2xl shadow-lg shadow-purple-200 flex items-center gap-2 transition active:scale-95">
            <span>➕</span>
            <span>添加新任务</span>
          </button>
        </header>

        <!-- 任务状态统计卡片 -->
        <div class="grid grid-cols-4 gap-4">
          <div @click="taskFilter = 'all'"
               :class="['p-4 rounded-2xl border cursor-pointer transition',
                        taskFilter === 'all' ? 'bg-purple-50 border-purple-300 shadow-sm' : 'bg-white border-gray-100 hover:border-gray-200']">
            <p class="text-xs text-gray-500 font-bold">全部任务</p>
            <p class="text-2xl font-black text-gray-800 mt-1 font-mono">{{ taskStats.total }}</p>
          </div>
          <div @click="taskFilter = 'todo'"
               :class="['p-4 rounded-2xl border cursor-pointer transition',
                        taskFilter === 'todo' ? 'bg-amber-50 border-amber-300 shadow-sm' : 'bg-white border-gray-100 hover:border-gray-200']">
            <p class="text-xs text-amber-600 font-bold">⏳ 待办</p>
            <p class="text-2xl font-black text-amber-700 mt-1 font-mono">{{ taskStats.todo }}</p>
          </div>
          <div @click="taskFilter = 'in_progress'"
               :class="['p-4 rounded-2xl border cursor-pointer transition',
                        taskFilter === 'in_progress' ? 'bg-blue-50 border-blue-300 shadow-sm' : 'bg-white border-gray-100 hover:border-gray-200']">
            <p class="text-xs text-blue-600 font-bold">🚀 进行中</p>
            <p class="text-2xl font-black text-blue-700 mt-1 font-mono">{{ taskStats.inProgress }}</p>
          </div>
          <div @click="taskFilter = 'done'"
               :class="['p-4 rounded-2xl border cursor-pointer transition',
                        taskFilter === 'done' ? 'bg-emerald-50 border-emerald-300 shadow-sm' : 'bg-white border-gray-100 hover:border-gray-200']">
            <p class="text-xs text-emerald-600 font-bold">✅ 已完成</p>
            <p class="text-2xl font-black text-emerald-700 mt-1 font-mono">{{ taskStats.done }}</p>
          </div>
        </div>

        <!-- 任务列表 -->
        <div class="bg-white rounded-3xl shadow-sm p-6 space-y-3">
          <div v-if="filteredTasks.length === 0" class="py-16 text-center">
            <p class="text-4xl mb-3">🎉</p>
            <p class="text-gray-500 font-bold text-sm">当前分类下暂无任务</p>
            <p class="text-gray-400 text-xs mt-1">快点击右上角“添加新任务”记录今日科研待办吧！</p>
          </div>

          <div v-for="task in filteredTasks" :key="task.id"
               class="flex items-center justify-between p-4 rounded-2xl border border-gray-100 hover:border-purple-200 hover:bg-purple-50/20 transition group">
            <div class="flex items-center gap-4 flex-1">
              <!-- 复选框切换完成 -->
              <button @click="toggleTaskStatus(task)"
                      :class="['w-6 h-6 rounded-lg flex items-center justify-center border transition',
                               task.status === 'done' ? 'bg-purple-600 border-purple-600 text-white' : 'border-gray-300 hover:border-purple-400']">
                <span v-if="task.status === 'done'" class="text-xs font-bold">✓</span>
              </button>

              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span :class="['font-bold text-sm', task.status === 'done' ? 'line-through text-gray-400' : 'text-gray-800']">
                    {{ task.title }}
                  </span>
                  <!-- 标签 -->
                  <span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-purple-100 text-purple-700">
                    {{ task.category }}
                  </span>
                  <span :class="['text-[10px] px-2 py-0.5 rounded-full font-bold',
                                 task.priority === '高' ? 'bg-red-100 text-red-600' : (task.priority === '中' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600')]">
                    优先级: {{ task.priority }}
                  </span>
                </div>
                <div class="flex items-center gap-3 text-[11px] text-gray-400 mt-1 font-mono">
                  <span v-if="task.due_date">📅 截止: {{ task.due_date }}</span>
                  <span>🕒 创建于: {{ task.created_at }}</span>
                </div>
              </div>
            </div>

            <!-- 状态快速流转与删除 -->
            <div class="flex items-center gap-2">
              <select :value="task.status" @change="updateTaskProgress(task, $event.target.value)"
                      class="text-xs font-bold px-2.5 py-1.5 rounded-xl border border-gray-200 bg-white text-gray-600 focus:ring-0">
                <option value="todo">待办 ⏳</option>
                <option value="in_progress">进行中 🚀</option>
                <option value="done">已完成 ✅</option>
              </select>
              <button @click="deleteTask(task.id)"
                      class="p-2 text-gray-300 hover:text-red-500 rounded-xl transition">
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ====================== TAB 3: 学术日记 ====================== -->
      <div v-if="activeTab === 'diary'" class="max-w-6xl mx-auto space-y-6 animate-in fade-in">
        <header class="flex justify-between items-center">
          <div>
            <h1 class="text-3xl font-extrabold text-gray-900 tracking-tight">学术长征日记</h1>
            <p class="text-gray-500 mt-1.5 text-sm">记录灵感碎片、文献笔记与学术心悟，见证蜕变成长。</p>
          </div>
          <button @click="openCreateDiaryModal"
                  class="bg-purple-600 hover:bg-purple-700 text-white font-bold px-5 py-3 rounded-2xl shadow-lg shadow-purple-200 flex items-center gap-2 transition active:scale-95">
            <span>✍️</span>
            <span>写一篇日记</span>
          </button>
        </header>

        <!-- 日记卡片流 -->
        <div v-if="diaries.length === 0" class="bg-white rounded-3xl p-16 text-center shadow-sm">
          <p class="text-4xl mb-3">📖</p>
          <p class="text-gray-500 font-bold text-sm">还没有学术日记</p>
          <p class="text-gray-400 text-xs mt-1">记录今天的科研实验或者运动解压心得吧！</p>
        </div>

        <div v-else class="grid grid-cols-2 gap-6">
          <div v-for="diary in diaries" :key="diary.id"
               class="bg-white rounded-3xl shadow-sm p-6 border border-gray-100 hover:border-purple-200 hover:shadow-md transition flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-3">
                <div class="flex items-center gap-2">
                  <span class="text-xs px-2.5 py-1 rounded-full bg-purple-50 text-purple-600 font-bold">
                    🏷️ {{ diary.tag }}
                  </span>
                  <span class="text-xs px-2.5 py-1 rounded-full bg-orange-50 text-orange-600 font-bold">
                    心情: {{ diary.mood }}
                  </span>
                </div>
                <button @click="deleteDiary(diary.id)" class="text-gray-300 hover:text-red-500 text-sm">
                  🗑️
                </button>
              </div>

              <h3 class="text-lg font-bold text-gray-900 mb-2">{{ diary.title }}</h3>
              <p class="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed line-clamp-6">
                {{ diary.content }}
              </p>
            </div>

            <div class="mt-5 pt-3 border-t border-gray-100 flex justify-between items-center text-xs text-gray-400 font-mono">
              <span>📅 日期: {{ diary.date }}</span>
              <span>记录于: {{ diary.created_at }}</span>
            </div>
          </div>
        </div>
      </div>

    </main>

    <!-- ====================== 弹窗集合 ====================== -->

    <!-- 1. 今日复盘弹窗 -->
    <div v-if="isSummaryModalOpen"
         class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-[60] animate-in fade-in">
      <div class="bg-white rounded-[2rem] p-8 w-[600px] shadow-2xl animate-in zoom-in-95">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-xl font-bold text-gray-800 flex items-center gap-2">
            <span>✍️</span> 撰写今日复盘
          </h3>
          <p class="text-sm text-purple-600 font-bold bg-purple-50 px-3 py-1 rounded-full font-mono">
            {{ currentDateStr.split(' ')[0] }}
          </p>
        </div>

        <textarea v-model="dailySummary"
                  class="w-full h-64 p-5 bg-gray-50 border-2 border-gray-100 rounded-2xl resize-none focus:ring-0 focus:border-purple-400 focus:bg-white text-gray-700 leading-relaxed text-sm transition-colors"
                  placeholder="畅所欲言吧... 今天读了什么文献？做了几组实验？羽毛球发挥得怎样？"></textarea>

        <div class="flex gap-4 mt-6">
          <button @click="isSummaryModalOpen = false"
                  class="flex-1 py-3 rounded-xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition">
            取消
          </button>
          <button @click="saveTodaySummary"
                  class="flex-1 py-3 rounded-xl bg-purple-600 text-white font-bold shadow-lg shadow-purple-200 hover:bg-purple-700 transition">
            💾 保存并关闭
          </button>
        </div>
      </div>
    </div>

    <!-- 2. 日历补录修改弹窗 -->
    <div v-if="isEditModalOpen"
         class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in">
      <div class="bg-white rounded-[2rem] p-8 w-[440px] shadow-2xl animate-in zoom-in-95">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-xl font-bold text-gray-800">📝 修改 / 补录历史记录</h3>
          <p class="text-sm font-bold text-purple-600 bg-purple-50 px-3 py-1 rounded-full font-mono">
            {{ selectedDayData.date }}
          </p>
        </div>

        <div class="space-y-4">
          <div class="bg-purple-50/50 p-4 rounded-2xl border border-purple-100">
            <label class="text-sm font-bold text-purple-700 block mb-2">🔬 科研专注时长</label>
            <div class="flex items-center gap-3">
              <input v-model="selectedDayData.study_h" type="number" min="0"
                     class="w-full p-2 border border-purple-200 rounded-xl text-center font-bold bg-white">
              <span class="text-sm font-bold text-gray-500">时</span>
              <input v-model="selectedDayData.study_m" type="number" min="0" max="59"
                     class="w-full p-2 border border-purple-200 rounded-xl text-center font-bold bg-white">
              <span class="text-sm font-bold text-gray-500">分</span>
            </div>
          </div>

          <div class="bg-orange-50/50 p-4 rounded-2xl border border-orange-100">
            <label class="text-sm font-bold text-orange-700 block mb-2">🏸 羽毛球解压时长</label>
            <div class="flex items-center gap-3">
              <input v-model="selectedDayData.ball_h" type="number" min="0"
                     class="w-full p-2 border border-orange-200 rounded-xl text-center font-bold bg-white">
              <span class="text-sm font-bold text-gray-500">时</span>
              <input v-model="selectedDayData.ball_m" type="number" min="0" max="59"
                     class="w-full p-2 border border-orange-200 rounded-xl text-center font-bold bg-white">
              <span class="text-sm font-bold text-gray-500">分</span>
            </div>
          </div>

          <div class="flex gap-2 items-center pt-1">
            <label class="text-sm font-bold text-gray-600">当天心情:</label>
            <select v-model="selectedDayData.mood" class="p-2 border rounded-xl flex-1 text-sm font-bold bg-white">
              <option v-for="m in ['糟糕', '忙碌', '开心', '平静', '努力', '摸鱼']" :key="m">{{ m }}</option>
            </select>
          </div>

          <div class="pt-1">
            <label class="text-sm font-bold text-gray-600 mb-1 block">当天复盘总结:</label>
            <textarea v-model="selectedDayData.summary"
                      class="w-full p-3 border rounded-xl text-sm leading-relaxed" rows="3"
                      placeholder="补录这一天的心得或进展..."></textarea>
          </div>
        </div>

        <div class="flex gap-4 mt-6">
          <button @click="isEditModalOpen = false"
                  class="flex-1 py-3 rounded-xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition">
            取消
          </button>
          <button @click="saveDailyData"
                  class="flex-1 py-3 rounded-xl bg-purple-600 text-white font-bold shadow-lg shadow-purple-200 hover:bg-purple-700 transition">
            保存覆盖
          </button>
        </div>
      </div>
    </div>

    <!-- 3. 新建任务弹窗 -->
    <div v-if="isTaskModalOpen"
         class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in">
      <div class="bg-white rounded-[2rem] p-8 w-[480px] shadow-2xl animate-in zoom-in-95">
        <h3 class="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
          <span>🎯</span> 添加学术任务
        </h3>

        <div class="space-y-4">
          <div>
            <label class="text-xs font-bold text-gray-500 block mb-1">任务名称</label>
            <input v-model="newTask.title" type="text"
                   class="w-full p-3 border border-gray-200 rounded-xl text-sm font-bold focus:border-purple-500"
                   placeholder="例如：精读 IEEE Trans 顶刊论文实验对比...">
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs font-bold text-gray-500 block mb-1">所属分类</label>
              <select v-model="newTask.category" class="w-full p-2.5 border rounded-xl text-sm font-bold bg-white">
                <option>科研</option>
                <option>论文写作</option>
                <option>实验仿真</option>
                <option>组会汇报</option>
                <option>审稿修回</option>
                <option>运动生活</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-bold text-gray-500 block mb-1">优先级</label>
              <select v-model="newTask.priority" class="w-full p-2.5 border rounded-xl text-sm font-bold bg-white">
                <option>高</option>
                <option>中</option>
                <option>低</option>
              </select>
            </div>
          </div>

          <div>
            <label class="text-xs font-bold text-gray-500 block mb-1">截止日期</label>
            <input v-model="newTask.due_date" type="date"
                   class="w-full p-2.5 border border-gray-200 rounded-xl text-sm font-bold">
          </div>
        </div>

        <div class="flex gap-4 mt-7">
          <button @click="isTaskModalOpen = false"
                  class="flex-1 py-3 rounded-xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition">
            取消
          </button>
          <button @click="submitCreateTask"
                  class="flex-1 py-3 rounded-xl bg-purple-600 text-white font-bold shadow-lg shadow-purple-200 hover:bg-purple-700 transition">
            创建任务
          </button>
        </div>
      </div>
    </div>

    <!-- 4. 新建日记弹窗 -->
    <div v-if="isDiaryModalOpen"
         class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in">
      <div class="bg-white rounded-[2rem] p-8 w-[580px] shadow-2xl animate-in zoom-in-95">
        <h3 class="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
          <span>📖</span> 撰写学术长征日记
        </h3>

        <div class="space-y-4">
          <div>
            <label class="text-xs font-bold text-gray-500 block mb-1">日记标题</label>
            <input v-model="newDiary.title" type="text"
                   class="w-full p-3 border border-gray-200 rounded-xl text-sm font-bold"
                   placeholder="给今天的科研心得起个标题...">
          </div>

          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="text-xs font-bold text-gray-500 block mb-1">日期</label>
              <input v-model="newDiary.date" type="date"
                     class="w-full p-2 border border-gray-200 rounded-xl text-xs font-bold">
            </div>
            <div>
              <label class="text-xs font-bold text-gray-500 block mb-1">分类标签</label>
              <select v-model="newDiary.tag" class="w-full p-2 border rounded-xl text-xs font-bold bg-white">
                <option>实验心得</option>
                <option>文献笔记</option>
                <option>审稿吐槽</option>
                <option>运动复盘</option>
                <option>学术心悟</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-bold text-gray-500 block mb-1">心境</label>
              <select v-model="newDiary.mood" class="w-full p-2 border rounded-xl text-xs font-bold bg-white">
                <option v-for="m in ['糟糕', '忙碌', '开心', '平静', '努力', '摸鱼']" :key="m">{{ m }}</option>
              </select>
            </div>
          </div>

          <div>
            <label class="text-xs font-bold text-gray-500 block mb-1">正文内容</label>
            <textarea v-model="newDiary.content" rows="6"
                      class="w-full p-4 border border-gray-200 rounded-xl text-sm leading-relaxed"
                      placeholder="记录下实验的参数细节、文献的灵感启发、或者今天打羽毛球的心得体会..."></textarea>
          </div>
        </div>

        <div class="flex gap-4 mt-6">
          <button @click="isDiaryModalOpen = false"
                  class="flex-1 py-3 rounded-xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition">
            取消
          </button>
          <button @click="submitCreateDiary"
                  class="flex-1 py-3 rounded-xl bg-purple-600 text-white font-bold shadow-lg shadow-purple-200 hover:bg-purple-700 transition">
            发布日记
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style>
.animate-in {
  animation-duration: 0.25s;
  animation-fill-mode: both;
}

.fade-in {
  animation-name: fadeIn;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 隐藏输入框原生加减箭头 */
input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 优雅的自定义滚动条 */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(147, 51, 234, 0.2);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(147, 51, 234, 0.4);
}
</style>