<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { dashboardApi, attendanceApi, leaveApi, useCachedFetch } from '../services/api';
import ClockWidget from '../components/ClockWidget.vue';
import {
  CalendarCheck,
  CalendarX,
  CalendarClock,
  CalendarHeart,
  Palmtree,
  Wallet,
  ArrowRight,
  Briefcase,
  Building2,
} from 'lucide-vue-next';

const router = useRouter();
const auth = useAuthStore();
const loading = ref(true);

interface DashData {
  employee: string;
  employee_name: string;
  department: string;
  designation: string;
  current_month: string;
  year: number;
  attendance_summary: Record<string, number>;
  leave_type_breakdown?: Record<string, number>;
  last_punch: { log_type: string; time: string } | null;
}

const dash = ref<DashData | null>(null);
const leaveBalance = ref<{ leave_type: string; balance: number }[]>([]);
const recentLeaves = ref<any[]>([]);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
});

const today = computed(() =>
  new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
);

const stats = computed(() => {
  const s = dash.value?.attendance_summary || {};
  const items = [
    { label: 'Present', value: s['Present'] || 0, icon: CalendarCheck, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Absent', value: s['Absent'] || 0, icon: CalendarX, color: 'text-red-400', bg: 'bg-red-500/10' },
    { label: 'Half Day', value: s['Half Day'] || 0, icon: CalendarClock, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  ];
  // Show "On Leave" stat with leave-type breakdown
  const onLeave = s['On Leave'] || 0;
  if (onLeave > 0) {
    const breakdown = dash.value?.leave_type_breakdown || {};
    const typeNames = Object.keys(breakdown);
    const subtitle = typeNames.length ? typeNames.join(', ') : '';
    items.push({
      label: subtitle || 'On Leave',
      value: onLeave,
      icon: CalendarHeart,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    });
  }
  return items;
});

const totalLeave = computed(() =>
  leaveBalance.value.reduce((sum, b) => sum + b.balance, 0)
);

let loadInProgress = false;
let lastLoadTime = 0;

async function loadDashboard() {
  const now = Date.now();
  if (loadInProgress) return;
  
  loadInProgress = true;
  lastLoadTime = now;

  // 1. Dashboard Data
  useCachedFetch('dashboard_data', dashboardApi.getData, (data) => {
    if (data && !data.error) {
       dash.value = data.message || data;
       loading.value = false;
    }
  });

  // 2. Leave Balance
  useCachedFetch('leave_balance', leaveApi.getBalance, (data) => {
     if (Array.isArray(data)) {
       leaveBalance.value = data;
     } else if (data.message && Array.isArray(data.message)) {
       leaveBalance.value = data.message;
     }
  });

  // 3. Recent Leaves
  useCachedFetch('leave_applications', leaveApi.getApplications, (data) => {
     const arr = Array.isArray(data) ? data : (data.message || []);
     if (Array.isArray(arr)) {
       recentLeaves.value = arr.slice(0, 5);
     }
  });
  
  loadInProgress = false;
}



function statusBadge(status: string) {
  const map: Record<string, string> = {
    'Open': 'badge-warning',
    'Approved': 'badge-success',
    'Rejected': 'badge-danger',
    'Cancelled': 'badge-neutral',
  };
  return map[status] || 'badge-neutral';
}

onMounted(loadDashboard);
</script>

<template>
  <div>
  <!-- Header -->
  <div class="mb-8 animate-fade-in">
    <h1 class="text-2xl sm:text-3xl font-bold text-white">
      {{ greeting }}, <span class="text-accent">{{ auth.fullName?.split(' ')[0] || 'there' }}</span>
    </h1>
    <p class="text-sm text-slate-500 mt-1">{{ today }}</p>
  </div>

  <!-- Clock Widget: always mounted (avoids unmount/remount loop when loadDashboard runs) -->
  <div class="glass-card p-6 sm:p-8 lg:row-span-2 flex flex-col items-center justify-center mb-6">
    <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-6">Attendance</h2>
    <ClockWidget @punched="loadDashboard" />
  </div>

  <!-- Loading skeleton (stats/leave only; ClockWidget stays mounted above) -->
  <div v-if="loading" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div v-for="i in 4" :key="i" class="glass-card p-6 animate-pulse">
      <div class="h-4 bg-white/5 rounded w-20 mb-3" />
      <div class="h-8 bg-white/5 rounded w-12" />
    </div>
  </div>

  <!-- Dashboard content (stats, leave, profile, etc.) -->
  <div v-else class="space-y-6 animate-slide-up">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Stats -->
      <div v-for="stat in stats" :key="stat.label" class="glass-card-hover p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-medium text-slate-400">{{ stat.label }}</span>
          <div :class="[stat.bg, stat.color]" class="w-9 h-9 rounded-xl flex items-center justify-center">
            <component :is="stat.icon" :size="18" :stroke-width="1.8" />
          </div>
        </div>
        <p class="stat-number" :class="stat.color">{{ stat.value }}</p>
        <p class="text-xs text-slate-500 mt-1">{{ dash?.current_month }} {{ dash?.year }}</p>
      </div>

      <!-- Leave balance mini -->
      <div class="glass-card-hover p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-medium text-slate-400">Leave Balance</span>
          <div class="w-9 h-9 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center">
            <Palmtree :size="18" :stroke-width="1.8" />
          </div>
        </div>
        <p class="stat-number text-teal-400">{{ totalLeave }}</p>
        <p class="text-xs text-slate-500 mt-1">days remaining</p>
      </div>
    </div>

    <!-- Employee info + Quick actions row -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Employee info (from auth store – always available) -->
      <div class="glass-card p-6">
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Profile</h3>
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Briefcase :size="16" :stroke-width="1.8" />
            </div>
            <div>
              <p class="text-xs text-slate-500">Designation</p>
              <p class="text-sm font-medium text-white">{{ auth.designation || dash?.designation || '—' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <Building2 :size="16" :stroke-width="1.8" />
            </div>
            <div>
              <p class="text-xs text-slate-500">Department</p>
              <p class="text-sm font-medium text-white">{{ auth.department || dash?.department || '—' }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="glass-card p-6">
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Quick Actions</h3>
        <div class="grid grid-cols-2 gap-3">
          <button @click="router.push('/leave')"
            class="flex items-center gap-2 p-4 rounded-xl bg-white/[0.03] hover:bg-white/[0.06]
                   border border-white/[0.04] hover:border-white/[0.08] transition-all group">
            <Palmtree :size="18" class="text-teal-400" :stroke-width="1.8" />
            <span class="text-sm font-medium text-slate-300 group-hover:text-white">Apply Leave</span>
          </button>
          <button @click="router.push('/payroll')"
            class="flex items-center gap-2 p-4 rounded-xl bg-white/[0.03] hover:bg-white/[0.06]
                   border border-white/[0.04] hover:border-white/[0.08] transition-all group">
            <Wallet :size="18" class="text-emerald-400" :stroke-width="1.8" />
            <span class="text-sm font-medium text-slate-300 group-hover:text-white">View Payslips</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Recent Leave Applications -->
    <div v-if="recentLeaves.length" class="glass-card p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Recent Leave</h3>
        <button @click="router.push('/leave')"
          class="text-xs text-accent hover:text-accent-light flex items-center gap-1 transition-colors">
          View all <ArrowRight :size="14" />
        </button>
      </div>
      <div class="space-y-3">
        <div v-for="app in recentLeaves" :key="app.name"
          class="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0">
          <div>
            <p class="text-sm font-medium text-white">{{ app.leave_type }}</p>
            <p class="text-xs text-slate-500">
              {{ new Date(app.from_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              <span v-if="app.from_date !== app.to_date">
                — {{ new Date(app.to_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              </span>
              &middot; {{ app.total_leave_days }} day{{ app.total_leave_days !== 1 ? 's' : '' }}
            </p>
          </div>
          <span :class="statusBadge(app.status)">{{ app.status }}</span>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>
