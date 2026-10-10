<script setup>
import {ref, computed, onMounted} from 'vue'
import axios from 'axios'

const api = axios.create({baseURL: 'http://127.0.0.1:8000'})

// --- 全局基础状态 ---
const activeTab = ref('monitor')
const currentDateStr = ref(new Date().toLocaleString('zh-CN', {dateStyle: 'full', timeStyle: 'short'}))

// 获取本地时区的 YYYY-MM-DD 格式
const getTodayStr = () => {
  const today = new Date()
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
}

// --- 今日总结与心情控制区 ---
const currentMood = ref('努力')
const dailySummary = ref('')
const isSummaryModalOpen = ref(false) // 新增：控制复盘弹窗的开关

// 保存今日总结和心情
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

    // 保存成功后关闭弹窗
    isSummaryModalOpen.value = false
    alert("📝 今日总结已保存！")
  } catch (error) {
    console.error(error)
  }
}

// 点击心情立即静默保存 (保持不变)
const updateMoodInstantly = async (m) => {
  currentMood.value = m // 第一步：立刻改变按钮颜色，给用户视觉反馈

  try {
    const todayStr = getTodayStr()
    const res = await api.get(`/day/${todayStr}`) // 获取当前已有的时长和总结，防覆盖

    const payload = {
      date: todayStr,
      study_time_seconds: res.data.study_time_seconds || 0,
      ball_time_seconds: res.data.ball_time_seconds || 0,
      mood: m, // 强制更新为刚点击的心情
      summary: res.data.summary || dailySummary.value
    }
    await api.post('/update_day/', payload)
    console.log(`静默保存成功：今日心情切换为 [${m}]`)
    // 注意：这里故意不写 alert 弹窗，为了做到真正的“无感保存”
  } catch (error) {
    console.error("心情自动保存失败", error)
  }
}
// --- 模拟与展示用的统计数据 (后续对接) ---
const showFullStats = ref(false)
const stats = ref({
  study: {today: '3.5h', month: '82h', year: '450h', total: '1200h'},
  ball: {today: '1h', month: '12h', year: '80h', total: '200h'},
  location: [
    {name: '图书馆', icon: '📚', today: 2, month: 15, year: 120, total: 300},
    {name: '实验室', icon: '💡', today: 1, month: 20, year: 150, total: 400},
    {name: '咖啡厅', icon: '☕', today: 0, month: 5, year: 20, total: 50},
    {name: '家里', icon: '🏠', today: 1, month: 5, year: 10, total: 50},
  ]
})


// --- 实时专注计时器逻辑 (无感静默累加版) ---
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
    // 停止计时
    clearInterval(timerInterval)
    isTimerRunning.value = false

    // 【核心】自动累加到今天的数据库中，不弹窗！
    try {
      const todayStr = getTodayStr()
      // 1. 查出今天的原有时长
      const res = await api.get(`/day/${todayStr}`)
      const currentStudy = res.data.study_time_seconds || 0

      // 2. 加上刚才秒表跑的时间
      const payload = {
        date: todayStr,
        study_time_seconds: currentStudy + timerSeconds.value,
        ball_time_seconds: res.data.ball_time_seconds || 0,
        mood: res.data.mood || currentMood.value,
        summary: res.data.summary || dailySummary.value
      }

      // 3. 静默保存
      await api.post('/update_day/', payload)
      alert(`🎉 专注结束！已自动为您累加 ${Math.floor(timerSeconds.value / 60)} 分钟科研时长！`)

      // 4. 秒表清零
      timerSeconds.value = 0
    } catch (err) {
      alert("自动保存失败，请检查后端。")
    }

  } else {
    // 开始计时
    isTimerRunning.value = true
    timerInterval = setInterval(() => {
      timerSeconds.value++
    }, 1000)
  }
}

// --- 日历生成核心逻辑 ---
const viewDate = ref(new Date())
const daysOfWeek = ['日', '一', '二', '三', '四', '五', '六']

const calendarDays = computed(() => {
  const year = viewDate.value.getFullYear()
  const month = viewDate.value.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const lastDate = new Date(year, month + 1, 0).getDate()

  let days = []
  for (let i = 0; i < firstDay; i++) days.push({day: '', currentMonth: false})
  for (let d = 1; d <= lastDate; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({
      day: d,
      currentMonth: true,
      fullDate: dateStr,
      isToday: getTodayStr() === dateStr
    })
  }
  return days
})
const changeMonth = (step) => {
  viewDate.value = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth() + step, 1)
}

// --- 日历点击：从数据库拉取真实数据并在弹窗显示 ---
const isEditModalOpen = ref(false)
const selectedDayData = ref({date: '', study_h: 0, study_m: 0, ball_h: 0, ball_m: 0, mood: '', summary: ''})

const openEditModal = async (item) => {
  if (!item.currentMonth) return

  try {
    // 【核心】从后端获取当天的真实时长
    const res = await api.get(`/day/${item.fullDate}`)

    selectedDayData.value = {
      date: item.fullDate,
      // 把秒转换回小时和分钟显示在框里
      study_h: Math.floor((res.data.study_time_seconds || 0) / 3600),
      study_m: Math.floor(((res.data.study_time_seconds || 0) % 3600) / 60),
      ball_h: Math.floor((res.data.ball_time_seconds || 0) / 3600),
      ball_m: Math.floor(((res.data.ball_time_seconds || 0) % 3600) / 60),
      mood: res.data.mood || '平静',
      summary: res.data.summary || ''
    }
    isEditModalOpen.value = true
  } catch (e) {
    console.error("获取数据失败", e)
  }
}

const saveDailyData = async () => {
  try {
    const studySeconds = (selectedDayData.value.study_h || 0) * 3600 + (selectedDayData.value.study_m || 0) * 60
    const ballSeconds = (selectedDayData.value.ball_h || 0) * 3600 + (selectedDayData.value.ball_m || 0) * 60
    const payload = {
      date: selectedDayData.value.date,
      study_time_seconds: studySeconds,
      ball_time_seconds: ballSeconds,
      mood: selectedDayData.value.mood,
      summary: selectedDayData.value.summary
    }
    await api.post('/update_day/', payload)
    isEditModalOpen.value = false
  } catch (error) {
    console.error(error)
  }
}
</script>

<template>
  <div class="flex h-screen bg-purple-50 font-sans text-gray-800 relative">

    <aside class="w-56 bg-white shadow-lg flex flex-col pt-8 z-10">
      <div class="px-8 pb-8 border-b border-gray-100 mb-6 text-center">
        <h2 class="text-2xl font-black text-purple-600 tracking-tighter">学术渡劫站</h2>
        <p class="text-[10px] text-gray-400 mt-1 uppercase tracking-widest">PHD Survival Station</p>
      </div>
      <nav class="flex-1 px-4 space-y-2">
        <button @click="activeTab = 'monitor'"
                :class="['w-full text-left px-6 py-4 rounded-2xl transition-all flex items-center gap-3', activeTab === 'monitor' ? 'bg-purple-500 text-white shadow-md scale-105' : 'text-gray-500 hover:bg-purple-100']">
          <span class="text-xl">🚀</span> <span class="font-bold">监测中心</span></button>
        <button @click="activeTab = 'task'"
                :class="['w-full text-left px-6 py-4 rounded-2xl transition-all flex items-center gap-3', activeTab === 'task' ? 'bg-purple-500 text-white shadow-md scale-105' : 'text-gray-500 hover:bg-purple-100']">
          <span class="text-xl">📝</span> <span class="font-bold">任务管理</span></button>
        <button @click="activeTab = 'diary'"
                :class="['w-full text-left px-6 py-4 rounded-2xl transition-all flex items-center gap-3', activeTab === 'diary' ? 'bg-purple-500 text-white shadow-md scale-105' : 'text-gray-500 hover:bg-purple-100']">
          <span class="text-xl">📖</span> <span class="font-bold">学术日记</span></button>
      </nav>
    </aside>

    <main class="flex-1 p-10 overflow-y-auto">
      <div v-if="activeTab === 'monitor'" class="max-w-6xl mx-auto space-y-6 animate-in fade-in">

        <header class="flex justify-between items-end mb-2">
          <div>
            <h1 class="text-3xl font-bold text-gray-800">欢迎回来，博士。</h1>
            <p class="text-gray-500 mt-2">今日目标：科研与羽毛球并重，不生气不摸鱼。</p>
          </div>
          <div class="text-right">
            <p class="text-xs text-gray-400 font-mono">{{ currentDateStr }}</p>
          </div>
        </header>

        <div class="flex gap-6 mb-6 h-48">
          <div @click="isSummaryModalOpen = true"
               class="flex-1 bg-white rounded-3xl shadow-sm p-8 border border-transparent hover:border-purple-200 cursor-pointer transition-all group relative overflow-hidden flex flex-col">
            <div class="flex justify-between items-center mb-4">
              <h3 class="text-sm font-bold text-gray-500 flex items-center gap-2">📝 今日简短复盘</h3>
              <span
                  class="text-purple-500 bg-purple-50 px-3 py-1 rounded-full text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                 ✏️ 点击撰写 / 修改
               </span>
            </div>

            <div class="flex-1 overflow-y-auto pr-2 custom-scrollbar">
              <p v-if="dailySummary" class="text-gray-700 whitespace-pre-wrap leading-relaxed text-sm">{{
                  dailySummary
                }}</p>
              <div v-else
                   class="h-full flex items-center justify-center border-2 border-dashed border-gray-100 rounded-xl">
                <p class="text-gray-400 italic text-sm">今天科研有何进展？羽毛球扣杀帅吗？点击这里写下今天的总结...</p>
              </div>
            </div>
          </div>

          <div
              class="w-24 bg-white rounded-3xl shadow-sm p-3 border border-purple-50 flex flex-col gap-2 justify-between">
            <h3 class="text-[10px] font-bold text-gray-400 text-center uppercase tracking-widest mt-1">当下心情</h3>
            <div class="flex flex-col gap-1.5 flex-1 justify-center">
              <button v-for="m in ['糟糕', '忙碌', '开心', '平静', '努力', '摸鱼']" :key="m"
                      @click="updateMoodInstantly(m)"
                      :class="['py-2 rounded-xl border text-xs font-bold transition-all w-full',
                               currentMood === m ? 'bg-purple-500 text-white border-purple-500 shadow-md scale-105' : 'border-gray-100 text-gray-500 hover:border-purple-300 hover:bg-purple-50']">
                {{ m }}
              </button>
            </div>
          </div>

        </div>

        <section class="bg-white rounded-3xl shadow-sm p-8 transition-all">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-xl font-bold text-gray-800">📊 成果看板</h3>
            <button @click="showFullStats = !showFullStats" class="text-purple-500 text-sm font-bold hover:underline">
              {{ showFullStats ? '收起详情 ▲' : '查看年度/总计 ▼' }}
            </button>
          </div>

          <div class="grid grid-cols-3 gap-6">
            <div class="bg-purple-600 text-white p-6 rounded-2xl shadow-lg relative overflow-hidden">
              <div class="relative z-10">
                <p class="text-purple-200 text-xs font-bold uppercase tracking-wider">科研专注</p>
                <div class="flex items-baseline gap-2 mt-2">
                  <p class="text-4xl font-black">{{ stats.study.today }}</p>
                  <p class="text-xs opacity-70">/ 今日</p>
                </div>
                <div class="mt-4 pt-4 border-t border-purple-400/40">
                  <p class="text-sm">本月：<span class="font-bold">{{ stats.study.month }}</span></p>
                  <div v-if="showFullStats" class="mt-2 space-y-1 animate-in">
                    <p class="text-sm text-purple-200">本年：<span class="font-bold text-white">{{
                        stats.study.year
                      }}</span></p>
                  </div>
                </div>
              </div>
              <span class="absolute -right-4 -bottom-4 text-8xl opacity-10">🔬</span>
            </div>

            <div class="bg-orange-500 text-white p-6 rounded-2xl shadow-lg relative overflow-hidden">
              <div class="relative z-10">
                <p class="text-orange-100 text-xs font-bold uppercase tracking-wider">羽毛球解压</p>
                <div class="flex items-baseline gap-2 mt-2">
                  <p class="text-4xl font-black">{{ stats.ball.today }}</p>
                  <p class="text-xs opacity-70">/ 今日</p>
                </div>
                <div class="mt-4 pt-4 border-t border-orange-400/40">
                  <p class="text-sm">本月：<span class="font-bold">{{ stats.ball.month }}</span></p>
                  <div v-if="showFullStats" class="mt-2 space-y-1 animate-in">
                    <p class="text-sm text-orange-200">本年：<span class="font-bold text-white">{{
                        stats.ball.year
                      }}</span></p>
                  </div>
                </div>
              </div>
              <span class="absolute -right-4 -bottom-4 text-8xl opacity-10">🏸</span>
            </div>

            <div class="bg-emerald-500 text-white p-5 rounded-2xl shadow-lg relative overflow-hidden">
              <div class="relative z-10">
                <p class="text-emerald-100 text-xs font-bold uppercase tracking-wider mb-3">地点驻留</p>
                <div class="grid grid-cols-2 gap-2">
                  <div v-for="loc in stats.location" :key="loc.name"
                       class="bg-emerald-600/40 rounded-xl p-2.5 backdrop-blur-sm border border-emerald-400/20">
                    <div class="flex items-center gap-1.5 mb-1"><span class="text-sm">{{ loc.icon }}</span><span
                        class="text-xs font-bold text-emerald-50">{{ loc.name }}</span></div>
                    <div class="flex items-end gap-1 mb-1"><span class="text-xl font-black leading-none">{{
                        loc.today
                      }}</span><span class="text-[9px] text-emerald-200">次 / 今日</span></div>
                    <p class="text-[10px] text-emerald-100">本月: {{ loc.month }}次</p>
                  </div>
                </div>
              </div>
              <span class="absolute -right-4 -bottom-4 text-8xl opacity-10">📍</span>
            </div>
          </div>
        </section>

        <div class="grid grid-cols-12 gap-8">
          <div class="col-span-7">
            <section class="bg-white rounded-3xl shadow-sm p-8 h-full relative">
              <div
                  class="absolute top-4 right-4 bg-purple-50 text-purple-600 text-[10px] px-3 py-1 rounded-full font-bold">
                👆 点击补录修改记录
              </div>
              <div class="flex justify-between items-center mb-8 mt-2">
                <h3 class="text-xl font-bold text-gray-700">{{ viewDate.getFullYear() }}年 {{
                    viewDate.getMonth() + 1
                  }}月</h3>
                <div class="flex gap-2">
                  <button @click="changeMonth(-1)"
                          class="p-2 bg-gray-50 hover:bg-purple-100 rounded-xl text-purple-500 transition">◀
                  </button>
                  <button @click="changeMonth(1)"
                          class="p-2 bg-gray-50 hover:bg-purple-100 rounded-xl text-purple-500 transition">▶
                  </button>
                </div>
              </div>

              <div class="grid grid-cols-7 gap-2 text-center">
                <div v-for="day in daysOfWeek" :key="day" class="text-xs font-bold text-gray-400 pb-2 uppercase">{{
                    day
                  }}
                </div>
                <div v-for="(item, index) in calendarDays" :key="index" @click="openEditModal(item)"
                     :class="['aspect-square flex flex-col items-center justify-center rounded-2xl text-sm relative transition-all duration-200 cursor-pointer',
                              item.currentMonth ? 'hover:bg-purple-100 hover:scale-105 text-gray-700 bg-gray-50/50' : 'text-gray-200 pointer-events-none',
                              item.isToday ? '!bg-purple-500 !text-white shadow-md font-bold' : '']">
                  {{ item.day }}
                </div>
              </div>
            </section>
          </div>

          <div class="col-span-5">
            <section class="bg-white rounded-3xl shadow-sm p-8 h-full flex flex-col justify-center">
              <div class="text-center mb-8">
                <h3 class="text-lg font-bold text-gray-500 mb-2">⏱️ 实时专注器</h3>
                <p :class="['text-5xl font-mono tracking-wider transition-colors duration-300', isTimerRunning ? 'text-purple-600 font-black scale-105' : 'text-gray-800']">
                  {{ formattedTimer }}</p>
              </div>

              <div class="flex gap-4 justify-center">
                <button @click="toggleTimer"
                        :class="['text-white w-full py-4 rounded-2xl font-bold shadow-lg transition-all duration-300 active:scale-95 text-lg', isTimerRunning ? 'bg-orange-500 hover:bg-orange-600 animate-pulse' : 'bg-purple-600 hover:bg-purple-700']">
                  {{ isTimerRunning ? '⏹ 结束并自动存入今日时长' : '▶ 开始专注' }}
                </button>
              </div>
            </section>
          </div>
        </div>

      </div>
    </main>

    <div v-if="isEditModalOpen"
         class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div class="bg-white rounded-[2rem] p-8 w-[400px] shadow-2xl animate-in zoom-in-95">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-xl font-bold text-gray-800">📝 修改历史记录</h3>
          <p class="text-sm font-bold text-purple-500 bg-purple-50 px-3 py-1 rounded-full">{{
              selectedDayData.date
            }}</p>
        </div>
        <div class="space-y-4">
          <div class="bg-purple-50/50 p-4 rounded-2xl border border-purple-100">
            <label class="text-sm font-bold text-purple-600 block mb-2">🔬 科研时长</label>
            <div class="flex items-center gap-3">
              <input v-model="selectedDayData.study_h" type="number"
                     class="w-full p-2 border border-purple-200 rounded-xl text-center"><span
                class="text-sm font-bold text-gray-500">时</span>
              <input v-model="selectedDayData.study_m" type="number"
                     class="w-full p-2 border border-purple-200 rounded-xl text-center"><span
                class="text-sm font-bold text-gray-500">分</span>
            </div>
          </div>
          <div class="bg-orange-50/50 p-4 rounded-2xl border border-orange-100">
            <label class="text-sm font-bold text-orange-600 block mb-2">🏸 羽毛球时长</label>
            <div class="flex items-center gap-3">
              <input v-model="selectedDayData.ball_h" type="number"
                     class="w-full p-2 border border-orange-200 rounded-xl text-center"><span
                class="text-sm font-bold text-gray-500">时</span>
              <input v-model="selectedDayData.ball_m" type="number"
                     class="w-full p-2 border border-orange-200 rounded-xl text-center"><span
                class="text-sm font-bold text-gray-500">分</span>
            </div>
          </div>
          <div class="flex gap-2 items-center pt-2">
            <label class="text-sm font-bold text-gray-600">当天心情:</label>
            <select v-model="selectedDayData.mood" class="p-2 border rounded-xl flex-1 focus:ring-purple-200">
              <option v-for="m in ['糟糕', '忙碌', '开心', '平静', '努力', '摸鱼']">{{ m }}</option>
            </select>
          </div>
          <div class="pt-2">
            <label class="text-sm font-bold text-gray-600 mb-1 block">当天复盘记录:</label>
            <textarea v-model="selectedDayData.summary" class="w-full p-2 border rounded-xl text-sm"
                      rows="2"></textarea>
          </div>
        </div>

        <div class="flex gap-4 mt-8">
          <button @click="isEditModalOpen = false"
                  class="flex-1 py-3 rounded-xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition">取消
          </button>
          <button @click="saveDailyData"
                  class="flex-1 py-3 rounded-xl bg-purple-600 text-white font-bold shadow-lg hover:bg-purple-700 transition">
            覆盖保存
          </button>
        </div>
      </div>

    </div>
    <div v-if="isSummaryModalOpen"
         class="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-[60]">
      <div class="bg-white rounded-[2rem] p-8 w-[600px] shadow-2xl animate-in zoom-in-95 duration-200">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-xl font-bold text-gray-800 flex items-center gap-2">✍️ 撰写复盘</h3>
          <p class="text-sm text-purple-500 font-bold bg-purple-50 px-3 py-1 rounded-full">
            {{ currentDateStr.split(' ')[0] }}</p>
        </div>

        <textarea v-model="dailySummary"
                  class="w-full h-64 p-5 bg-gray-50 border-2 border-gray-100 rounded-2xl resize-none focus:ring-0 focus:border-purple-400 focus:bg-white text-gray-700 leading-relaxed text-base transition-colors"
                  placeholder="畅所欲言吧... 今天读了什么文献？做了几组实验？心情如何？"></textarea>

        <div class="flex gap-4 mt-6">
          <button @click="isSummaryModalOpen = false"
                  class="flex-1 py-3 rounded-xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition">取消
          </button>
          <button @click="saveTodaySummary"
                  class="flex-1 py-3 rounded-xl bg-purple-600 text-white font-bold shadow-lg hover:bg-purple-700 transition">
            💾 保存并关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* 保持原有动画代码不变... */
.animate-in {
  animation-duration: 0.3s;
  animation-fill-mode: both;
}

.fade-in {
  animation-name: fadeIn;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>