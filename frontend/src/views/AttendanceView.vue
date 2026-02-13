<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { attendanceApi, leaveApi } from '../services/api';
import ClockWidget from '../components/ClockWidget.vue';
import {
  CalendarCheck,
  CalendarX,
  CalendarClock,
  CalendarHeart,
  Calendar,
  ChevronDown,
  Clock,
} from 'lucide-vue-next';

const loading = ref(true);

// Month filter — default to current month
const _today = new Date();
const selectedMonth = ref(_today.getMonth() + 1);
const selectedYear = ref(_today.getFullYear());

interface AttendanceRecord {
  date: string;
  status: string;
  working_hours: number;
  in_time: string | null;
  out_time: string | null;
}

const records = ref<AttendanceRecord[]>([]);
const summary = ref<Record<string, number>>({});
const holidays = ref<{ holiday_date: string; description: string; weekly_off?: number }[]>([]);

// Month options (last 12 months + current + next 2)
const monthOptions = computed(() => {
  const opts: { value: string; label: string; month: number; year: number }[] = [];
  const now = new Date();
  // Go back 12 months and forward 2
  for (let offset = -12; offset <= 2; offset++) {
    const d = new Date(now.getFullYear(), now.getMonth() + offset, 1);
    const m = d.getMonth() + 1;
    const y = d.getFullYear();
    opts.push({
      value: `${y}-${m}`,
      label: d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
      month: m,
      year: y,
    });
  }
  return opts;
});

const selectedMonthKey = computed({
  get: () => `${selectedYear.value}-${selectedMonth.value}`,
  set: (val: string) => {
    const [y, m] = val.split('-').map(Number);
    selectedYear.value = y;
    selectedMonth.value = m;
  },
});

// Holiday month key for filtering
const holidayMonthKey = computed(() =>
  `${selectedYear.value}-${String(selectedMonth.value).padStart(2, '0')}`
);

const filteredHolidays = computed(() => {
  return holidays.value.filter((h) => h.holiday_date.startsWith(holidayMonthKey.value));
});

// Stats cards
const stats = computed(() => {
  const s = summary.value || {};
  return [
    { label: 'Present', value: s['Present'] || 0, icon: CalendarCheck, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Absent', value: s['Absent'] || 0, icon: CalendarX, color: 'text-red-400', bg: 'bg-red-500/10' },
    { label: 'Half Day', value: s['Half Day'] || 0, icon: CalendarClock, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { label: 'On Leave', value: s['On Leave'] || 0, icon: CalendarHeart, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  ];
});

function statusColor(status: string) {
  const map: Record<string, string> = {
    'Present': 'text-emerald-400',
    'Absent': 'text-red-400',
    'Half Day': 'text-amber-400',
    'On Leave': 'text-blue-400',
  };
  return map[status] || 'text-slate-400';
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    'Present': 'badge-success',
    'Absent': 'badge-danger',
    'Half Day': 'badge-warning',
    'On Leave': 'badge-info',
  };
  return map[status] || 'badge-neutral';
}

function formatTime(timeStr: string | null) {
  if (!timeStr) return '—';
  try {
    const d = new Date(timeStr);
    if (isNaN(d.getTime())) return timeStr;
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return timeStr;
  }
}

function formatDate(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

async function loadData() {
  loading.value = true;
  try {
    const [attData, holData] = await Promise.allSettled([
      attendanceApi.getRecords(selectedMonth.value, selectedYear.value),
      leaveApi.getHolidays(
        `${selectedYear.value}-01-01`,
        `${selectedYear.value}-12-31`
      ),
    ]);

    if (attData.status === 'fulfilled' && attData.value) {
      records.value = attData.value.records || [];
      summary.value = attData.value.summary || {};
    }
    if (holData.status === 'fulfilled') {
      holidays.value = Array.isArray(holData.value) ? holData.value : [];
    }
  } finally {
    loading.value = false;
  }
}

// Reload when month changes
watch([selectedMonth, selectedYear], () => {
  loadData();
});

function onPunched() {
  // Reload attendance data after punch
  loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-white">Attendance</h1>
        <p class="text-sm text-slate-500 mt-1">Track your daily attendance and working hours</p>
      </div>
      <!-- Month selector -->
      <div class="flex items-center gap-2 shrink-0">
        <label class="text-xs text-slate-500 whitespace-nowrap">Month:</label>
        <div class="relative">
          <select v-model="selectedMonthKey"
            class="input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[180px] border border-white/10 rounded-lg">
            <option v-for="opt in monthOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <ChevronDown :size="14" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
        </div>
      </div>
    </div>

    <!-- Clock Widget -->
    <div class="glass-card p-6 sm:p-8 flex flex-col items-center justify-center mb-6">
      <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-6">Today's Clock</h2>
      <ClockWidget @punched="onPunched" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else class="space-y-6 animate-slide-up">
      <!-- Summary Stats -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div v-for="stat in stats" :key="stat.label" class="glass-card-hover p-5">
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-medium text-slate-400">{{ stat.label }}</span>
            <div :class="[stat.bg, stat.color]" class="w-9 h-9 rounded-xl flex items-center justify-center">
              <component :is="stat.icon" :size="18" :stroke-width="1.8" />
            </div>
          </div>
          <p class="stat-number" :class="stat.color">{{ stat.value }}</p>
        </div>
      </div>

      <!-- Holidays for selected month -->
      <div v-if="filteredHolidays.length" class="glass-card p-5">
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Holidays in {{ monthOptions.find(o => o.value === selectedMonthKey)?.label || 'Selected Month' }}
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div v-for="h in filteredHolidays" :key="h.holiday_date"
            class="flex items-center gap-3 py-2 px-3 rounded-lg bg-white/[0.03] border border-white/[0.04]">
            <div class="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
              <Calendar :size="18" :stroke-width="1.8" />
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-white">
                {{ new Date(h.holiday_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }}
              </p>
              <p class="text-xs text-slate-500 truncate">{{ h.description || 'Holiday' }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Attendance Records Table -->
      <div>
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Attendance Records
        </h3>
        <div v-if="records.length" class="glass-card overflow-hidden">
          <!-- Desktop table -->
          <div class="hidden sm:block overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-white/[0.06]">
                  <th class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Date</th>
                  <th class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Status</th>
                  <th class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">In Time</th>
                  <th class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Out Time</th>
                  <th class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Hours</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rec in records" :key="rec.date"
                  class="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                  <td class="px-5 py-4">
                    <p class="text-sm font-medium text-white">{{ formatDate(rec.date) }}</p>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span :class="statusBadge(rec.status)">{{ rec.status }}</span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-sm text-slate-300">{{ formatTime(rec.in_time) }}</span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-sm text-slate-300">{{ formatTime(rec.out_time) }}</span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-sm font-semibold" :class="statusColor(rec.status)">
                      {{ rec.working_hours > 0 ? rec.working_hours.toFixed(1) + 'h' : '—' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Mobile cards -->
          <div class="sm:hidden divide-y divide-white/[0.04]">
            <div v-for="rec in records" :key="rec.date" class="p-4 space-y-2">
              <div class="flex items-center justify-between">
                <p class="text-sm font-medium text-white">{{ formatDate(rec.date) }}</p>
                <span :class="statusBadge(rec.status)">{{ rec.status }}</span>
              </div>
              <div class="flex items-center gap-4 text-xs text-slate-500">
                <span v-if="rec.in_time">
                  <Clock :size="12" class="inline mr-1" />In: {{ formatTime(rec.in_time) }}
                </span>
                <span v-if="rec.out_time">
                  <Clock :size="12" class="inline mr-1" />Out: {{ formatTime(rec.out_time) }}
                </span>
                <span v-if="rec.working_hours > 0" :class="statusColor(rec.status)">
                  {{ rec.working_hours.toFixed(1) }}h
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="glass-card p-8 text-center">
          <CalendarCheck :size="32" class="mx-auto text-slate-600 mb-2" />
          <p class="text-slate-500 text-sm">No attendance records for this month</p>
        </div>
      </div>
    </div>
  </div>
</template>
