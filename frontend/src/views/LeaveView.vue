<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { leaveApi, dashboardApi } from '../services/api';
import {
  Palmtree,
  Plus,
  X,
  Calendar,
  Clock,
  User,
  Briefcase,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-vue-next';

const loading = ref(true);
const balance = ref<{ leave_type: string; balance: number }[]>([]);
const applications = ref<any[]>([]);
const leaveTypes = ref<string[]>([]);
const holidays = ref<{ holiday_date: string; description: string; weekly_off?: number }[]>([]);
const manager = ref<any>(null);

// Holidays month filter: "YYYY-MM" or "" for all. Default: current month
const _today = new Date();
const holidaysMonthFilter = ref<string>(
  `${_today.getFullYear()}-${String(_today.getMonth() + 1).padStart(2, '0')}`
);

// Apply form
const showApplyForm = ref(false);
const applyLoading = ref(false);
const applyError = ref('');
const applySuccess = ref('');
const form = ref({
  leave_type: '',
  from_date: '',
  to_date: '',
  half_day: 0,
  reason: '',
});

const totalBalance = computed(() =>
  balance.value.reduce((s, b) => s + b.balance, 0)
);

// Month options for holidays filter (current year + next year)
const holidaysMonthOptions = computed(() => {
  const now = new Date();
  const year = now.getFullYear();
  const opts: { value: string; label: string }[] = [
    { value: '', label: 'All months' },
  ];
  for (let y = year; y <= year + 1; y++) {
    for (let m = 1; m <= 12; m++) {
      const value = `${y}-${String(m).padStart(2, '0')}`;
      const d = new Date(y, m - 1, 1);
      opts.push({ value, label: d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) });
    }
  }
  return opts;
});

// Holidays filtered by selected month
const filteredHolidays = computed(() => {
  const list = holidays.value;
  if (!holidaysMonthFilter.value) return list;
  return list.filter((h) => h.holiday_date.startsWith(holidaysMonthFilter.value));
});

// Colors for leave types
const typeColors = [
  { bg: 'bg-teal-500/10', text: 'text-teal-400', ring: 'ring-teal-500/20' },
  { bg: 'bg-blue-500/10', text: 'text-blue-400', ring: 'ring-blue-500/20' },
  { bg: 'bg-purple-500/10', text: 'text-purple-400', ring: 'ring-purple-500/20' },
  { bg: 'bg-amber-500/10', text: 'text-amber-400', ring: 'ring-amber-500/20' },
  { bg: 'bg-rose-500/10', text: 'text-rose-400', ring: 'ring-rose-500/20' },
  { bg: 'bg-emerald-500/10', text: 'text-emerald-400', ring: 'ring-emerald-500/20' },
];

function getTypeColor(idx: number) {
  return typeColors[idx % typeColors.length];
}

function statusBadge(status: string) {
  const m: Record<string, string> = {
    'Open': 'badge-warning',
    'Approved': 'badge-success',
    'Rejected': 'badge-danger',
    'Cancelled': 'badge-neutral',
  };
  return m[status] || 'badge-neutral';
}

function statusIcon(status: string) {
  const m: Record<string, any> = {
    'Open': Clock,
    'Approved': CheckCircle2,
    'Rejected': XCircle,
    'Cancelled': XCircle,
  };
  return m[status] || Clock;
}

function getDefaultDateRange() {
  const now = new Date();
  const year = now.getFullYear();
  const from = `${year}-01-01`;
  const to = `${year}-12-31`;
  return { from, to };
}

async function loadData() {
  loading.value = true;
  try {
    const { from, to } = getDefaultDateRange();
    const [bal, apps, types, mgr, hols] = await Promise.allSettled([
      leaveApi.getBalance(),
      leaveApi.getApplications(),
      leaveApi.getTypes(),
      dashboardApi.getReportingInfo(),
      leaveApi.getHolidays(from, to, true),
    ]);
    if (bal.status === 'fulfilled') balance.value = Array.isArray(bal.value) ? bal.value : [];
    if (apps.status === 'fulfilled') applications.value = Array.isArray(apps.value) ? apps.value : [];
    if (types.status === 'fulfilled') leaveTypes.value = Array.isArray(types.value) ? types.value : [];
    if (mgr.status === 'fulfilled') manager.value = mgr.value;
    if (hols.status === 'fulfilled') holidays.value = Array.isArray(hols.value) ? hols.value : [];
  } finally {
    loading.value = false;
  }
}

function openApplyForm() {
  form.value = { leave_type: leaveTypes.value[0] || '', from_date: '', to_date: '', half_day: 0, reason: '' };
  applyError.value = '';
  applySuccess.value = '';
  showApplyForm.value = true;
}

async function submitLeave() {
  applyLoading.value = true;
  applyError.value = '';
  applySuccess.value = '';
  try {
    const result = await leaveApi.apply(form.value);
    if (result.success) {
      applySuccess.value = `Leave application ${result.name} submitted successfully!`;
      showApplyForm.value = false;
      await loadData();
    } else {
      applyError.value = result.error || 'Failed to submit';
    }
  } catch (e: any) {
    applyError.value = e.message || 'Something went wrong';
  } finally {
    applyLoading.value = false;
  }
}

async function cancelLeave(name: string) {
  if (!confirm('Cancel this leave application?')) return;
  try {
    const result = await leaveApi.cancel(name);
    if (result.success) {
      await loadData();
    }
  } catch (e: any) {
    alert(e.message || 'Failed to cancel');
  }
}

onMounted(loadData);
</script>

<template>
  <div>
  <!-- Header -->
  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in">
    <div>
      <h1 class="text-2xl sm:text-3xl font-bold text-white">Leave Management</h1>
      <p class="text-sm text-slate-500 mt-1">Track, apply and manage your leaves</p>
    </div>
    <button @click="openApplyForm" class="btn-accent flex items-center gap-2 self-start">
      <Plus :size="18" />
      Apply Leave
    </button>
  </div>

  <!-- Loading -->
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
  </div>

  <div v-else class="space-y-6 animate-slide-up">
    <!-- Manager Info -->
    <div v-if="manager?.reporting_manager || manager?.leave_approver" class="glass-card p-5">
      <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Reporting & Approval</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-if="manager.reporting_manager" class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
            <User :size="18" :stroke-width="1.8" />
          </div>
          <div>
            <p class="text-xs text-slate-500">Reporting Manager</p>
            <p class="text-sm font-medium text-white">{{ manager.reporting_manager.employee_name }}</p>
            <p class="text-xs text-slate-500">{{ manager.reporting_manager.designation }}</p>
          </div>
        </div>
        <div v-if="manager.leave_approver" class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
            <Briefcase :size="18" :stroke-width="1.8" />
          </div>
          <div>
            <p class="text-xs text-slate-500">Leave Approver</p>
            <p class="text-sm font-medium text-white">{{ manager.leave_approver.employee_name }}</p>
            <p class="text-xs text-slate-500">{{ manager.leave_approver.designation }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Holidays (from ERPNext Holiday List) -->
    <div v-if="holidays.length" class="glass-card p-5">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
        <div>
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Company Holidays</h3>
          <p class="text-xs text-slate-500 mt-1">Holidays from your assigned Holiday List in ERPNext</p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <label class="text-xs text-slate-500 whitespace-nowrap">Filter by month:</label>
          <div class="relative">
            <select v-model="holidaysMonthFilter"
              class="input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[160px] border border-white/10 rounded-lg">
              <option v-for="opt in holidaysMonthOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
            <ChevronDown :size="14" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          </div>
        </div>
      </div>
      <div class="relative">
        <div class="holidays-scroll grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-64 overflow-y-auto overflow-x-hidden"
          style="scrollbar-width: thin; scrollbar-color: rgb(71 85 105) rgba(255,255,255,0.03);">
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
        <p v-if="filteredHolidays.length === 0" class="text-sm text-slate-500 py-6 text-center">
          No holidays in selected month
        </p>
      </div>
    </div>

    <!-- Leave Balance Cards -->
    <div>
      <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Leave Balance</h3>
      <p class="text-xs text-slate-500 mb-4">Casual Leave, Sick Leave, Earned Leave (1 per 20 working days), Regional Holidays</p>
      <div v-if="balance.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div v-for="(b, idx) in balance" :key="b.leave_type"
          class="glass-card-hover p-5 ring-1" :class="getTypeColor(idx).ring">
          <p class="text-sm font-medium text-slate-400 mb-2 truncate" :title="b.leave_type">
            {{ b.leave_type }}
          </p>
          <p class="text-3xl font-bold" :class="getTypeColor(idx).text">
            {{ b.balance }}
          </p>
          <p class="text-xs text-slate-500 mt-1">days</p>
        </div>
        <!-- Total -->
        <div class="glass-card p-5 border-accent/20">
          <p class="text-sm font-medium text-slate-400 mb-2">Total</p>
          <p class="text-3xl font-bold text-accent">{{ totalBalance }}</p>
          <p class="text-xs text-slate-500 mt-1">days remaining</p>
        </div>
      </div>
      <div v-else class="glass-card p-8 text-center">
        <Palmtree :size="32" class="mx-auto text-slate-600 mb-2" />
        <p class="text-slate-500 text-sm">No leave balance data available</p>
      </div>
    </div>

    <!-- Applications List -->
    <div>
      <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
        My Applications
      </h3>
      <div v-if="applications.length" class="glass-card overflow-hidden">
        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-white/[0.06]">
                <th class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Type</th>
                <th class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Period</th>
                <th class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Days</th>
                <th class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Status</th>
                <th class="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="app in applications" :key="app.name"
                class="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                <td class="px-5 py-4">
                  <p class="text-sm font-medium text-white">{{ app.leave_type }}</p>
                </td>
                <td class="px-5 py-4">
                  <p class="text-sm text-slate-300">
                    {{ new Date(app.from_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                    <template v-if="app.from_date !== app.to_date">
                      — {{ new Date(app.to_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                    </template>
                  </p>
                </td>
                <td class="px-5 py-4 text-center">
                  <span class="text-sm font-semibold text-white">{{ app.total_leave_days }}</span>
                </td>
                <td class="px-5 py-4 text-center">
                  <span :class="statusBadge(app.status)">{{ app.status }}</span>
                </td>
                <td class="px-5 py-4 text-right">
                  <button v-if="app.status === 'Open'" @click="cancelLeave(app.name)"
                    class="text-xs text-red-400 hover:text-red-300 transition-colors">
                    Cancel
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Mobile cards -->
        <div class="sm:hidden divide-y divide-white/[0.04]">
          <div v-for="app in applications" :key="app.name" class="p-4 space-y-2">
            <div class="flex items-center justify-between">
              <p class="text-sm font-medium text-white">{{ app.leave_type }}</p>
              <span :class="statusBadge(app.status)">{{ app.status }}</span>
            </div>
            <p class="text-xs text-slate-500">
              {{ new Date(app.from_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              <template v-if="app.from_date !== app.to_date">
                — {{ new Date(app.to_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              </template>
              &middot; {{ app.total_leave_days }} day{{ app.total_leave_days !== 1 ? 's' : '' }}
            </p>
            <button v-if="app.status === 'Open'" @click="cancelLeave(app.name)"
              class="text-xs text-red-400 hover:text-red-300">Cancel</button>
          </div>
        </div>
      </div>
      <div v-else class="glass-card p-8 text-center">
        <Calendar :size="32" class="mx-auto text-slate-600 mb-2" />
        <p class="text-slate-500 text-sm">No leave applications yet</p>
      </div>
    </div>
  </div>

  <!-- Apply Leave Modal -->
  <transition name="modal">
    <div v-if="showApplyForm" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
         @click.self="showApplyForm = false">
      <div class="modal-content glass-card w-full max-w-md p-6 space-y-5">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-white">Apply for Leave</h2>
          <button @click="showApplyForm = false" class="text-slate-500 hover:text-white transition-colors p-1">
            <X :size="20" />
          </button>
        </div>

        <form @submit.prevent="submitLeave" class="space-y-4">
          <!-- Leave Type (from ERPNext) -->
          <div>
            <label class="block text-sm font-medium text-slate-400 mb-1.5">Leave Type</label>
            <div class="relative">
              <select v-model="form.leave_type" class="input-dark appearance-none pr-10 cursor-pointer"
                :disabled="!leaveTypes.length">
                <option value="" disabled>Select leave type</option>
                <option v-for="t in leaveTypes" :key="t" :value="t">{{ t }}</option>
                <option v-if="!leaveTypes.length" value="" disabled>No leave types in ERPNext</option>
              </select>
              <ChevronDown :size="16" class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
            </div>
            <p v-if="leaveTypes.length" class="text-xs text-slate-500 mt-1">Leave types from ERPNext</p>
          </div>

          <!-- Dates -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-slate-400 mb-1.5">From</label>
              <input type="date" v-model="form.from_date" required class="input-dark" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-400 mb-1.5">To</label>
              <input type="date" v-model="form.to_date" required class="input-dark" />
            </div>
          </div>

          <!-- Half day -->
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" :true-value="1" :false-value="0" v-model="form.half_day"
              class="w-4 h-4 rounded border-white/10 bg-white/5 text-accent focus:ring-accent/30" />
            <span class="text-sm text-slate-400">Half day</span>
          </label>

          <!-- Reason -->
          <div>
            <label class="block text-sm font-medium text-slate-400 mb-1.5">Reason <span class="text-slate-600">(optional)</span></label>
            <textarea v-model="form.reason" rows="3" class="input-dark resize-none"
              placeholder="Briefly describe the reason..."></textarea>
          </div>

          <!-- Error / Success -->
          <div v-if="applyError" class="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 p-3 rounded-xl">
            <AlertCircle :size="16" class="mt-0.5 shrink-0" />
            {{ applyError }}
          </div>

          <button type="submit" :disabled="applyLoading || !form.leave_type || !form.from_date || !form.to_date"
            class="btn-accent w-full flex items-center justify-center gap-2">
            <Loader2 v-if="applyLoading" :size="18" class="animate-spin" />
            <span>{{ applyLoading ? 'Submitting...' : 'Submit Application' }}</span>
          </button>
        </form>
      </div>
    </div>
  </transition>

  <!-- Success toast -->
  <transition name="modal">
    <div v-if="applySuccess" class="fixed bottom-24 lg:bottom-8 left-1/2 -translate-x-1/2 z-50
                                    flex items-center gap-2 bg-emerald-500/15 border border-emerald-500/20
                                    text-emerald-400 px-5 py-3 rounded-xl shadow-lg">
      <CheckCircle2 :size="18" />
      <span class="text-sm font-medium">{{ applySuccess }}</span>
      <button @click="applySuccess = ''" class="ml-2 text-emerald-400/60 hover:text-emerald-400">
        <X :size="16" />
      </button>
    </div>
  </transition>
  </div>
</template>
