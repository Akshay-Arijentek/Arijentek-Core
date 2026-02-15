<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue';
import { leaveApi, dashboardApi, useCachedFetch } from '../services/api';
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

let isMounted = true;
onBeforeUnmount(() => { isMounted = false; });

// Holidays month filter
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

const filteredHolidays = computed(() => {
  const list = holidays.value;
  if (!holidaysMonthFilter.value) return list;
  return list.filter((h) => h.holiday_date.startsWith(holidaysMonthFilter.value));
});

// Colors for leave types
const typeColorVars = [
  { bg: 'rgba(20,184,166,0.1)', text: 'var(--accent)', ring: 'rgba(20,184,166,0.2)' },
  { bg: 'var(--info-bg)', text: 'var(--info-text)', ring: 'rgba(59,130,246,0.2)' },
  { bg: 'rgba(168,85,247,0.1)', text: '#a855f7', ring: 'rgba(168,85,247,0.2)' },
  { bg: 'var(--warning-bg)', text: 'var(--warning-text)', ring: 'rgba(245,158,11,0.2)' },
  { bg: 'var(--danger-bg)', text: 'var(--danger-text)', ring: 'rgba(239,68,68,0.2)' },
  { bg: 'var(--success-bg)', text: 'var(--success-text)', ring: 'rgba(34,197,94,0.2)' },
];
function getTypeColor(idx: number) {
  return typeColorVars[idx % typeColorVars.length];
}

const statusColorMap: Record<string, { bg: string; text: string }> = {
  'Open': { bg: 'var(--warning-bg)', text: 'var(--warning-text)' },
  'Approved': { bg: 'var(--success-bg)', text: 'var(--success-text)' },
  'Rejected': { bg: 'var(--danger-bg)', text: 'var(--danger-text)' },
  'Cancelled': { bg: 'var(--neutral-bg)', text: 'var(--neutral-text)' },
};
function getStatusStyle(status: string) {
  return statusColorMap[status] || statusColorMap['Cancelled'];
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
  return { from: `${year}-01-01`, to: `${year}-12-31` };
}

async function loadData() {
  // loading.value = true;
  const { from, to } = getDefaultDateRange();
  
  useCachedFetch('leave_balance', leaveApi.getBalance, (data) => {
    if (!isMounted) return;
    const list = Array.isArray(data) ? data : (data || []);
    if (Array.isArray(list)) {
      balance.value = list;
      loading.value = false;
    }
  });

  useCachedFetch('leave_applications', leaveApi.getApplications, (data) => {
    if (!isMounted) return;
    const list = Array.isArray(data) ? data : (data || []);
    if (Array.isArray(list)) applications.value = list;
  });

  // These are less critical to cache but might as well
  useCachedFetch('leave_types', leaveApi.getTypes, (data) => {
    if (isMounted && Array.isArray(data)) leaveTypes.value = data;
  });

  useCachedFetch('reporting_info', dashboardApi.getReportingInfo, (data) => {
    if (isMounted && data) manager.value = data;
  });

  useCachedFetch('holidays', () => leaveApi.getHolidays(from, to, true), (data) => {
    if (isMounted && Array.isArray(data)) holidays.value = data;
  });
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
    if (!isMounted) return;
    if (result.success) {
      applySuccess.value = `Leave application ${result.name} submitted successfully!`;
      showApplyForm.value = false;
      await loadData();
    } else {
      applyError.value = result.error || 'Failed to submit';
    }
  } catch (e: any) {
    if (isMounted) applyError.value = e.message || 'Something went wrong';
  } finally {
    if (isMounted) applyLoading.value = false;
  }
}

async function cancelLeave(name: string) {
  if (!confirm('Cancel this leave application?')) return;
  try {
    const result = await leaveApi.cancel(name);
    if (result.success) await loadData();
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
      <h1 class="text-2xl sm:text-3xl font-bold" :style="{ color: 'var(--heading-color)' }">Leave Management</h1>
      <p class="text-sm mt-1" :style="{ color: 'var(--text-tertiary)' }">Track, apply and manage your leaves</p>
    </div>
    <button @click="openApplyForm" class="btn-accent flex items-center gap-2 self-start">
      <Plus :size="18" />
      Apply Leave
    </button>
  </div>

  <!-- Loading -->
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="w-10 h-10 border-2 rounded-full animate-spin"
      :style="{ borderColor: 'var(--border-color)', borderTopColor: 'var(--accent)' }" />
  </div>

  <div v-else class="space-y-6 animate-slide-up">
    <!-- Manager Info -->
    <div v-if="manager?.reporting_manager || manager?.leave_approver" class="glass-card p-5">
      <h3 class="text-sm font-semibold uppercase tracking-wider mb-4" :style="{ color: 'var(--text-secondary)' }">Reporting & Approval</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-if="manager.reporting_manager" class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center"
            :style="{ backgroundColor: 'var(--info-bg)', color: 'var(--info-text)' }">
            <User :size="18" :stroke-width="1.8" />
          </div>
          <div>
            <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">Reporting Manager</p>
            <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">{{ manager.reporting_manager.employee_name }}</p>
            <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">{{ manager.reporting_manager.designation }}</p>
          </div>
        </div>
        <div v-if="manager.leave_approver" class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center"
            :style="{ backgroundColor: 'rgba(168,85,247,0.1)', color: '#a855f7' }">
            <Briefcase :size="18" :stroke-width="1.8" />
          </div>
          <div>
            <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">Leave Approver</p>
            <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">{{ manager.leave_approver.employee_name }}</p>
            <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">{{ manager.leave_approver.designation }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Holidays -->
    <div v-if="holidays.length" class="glass-card p-5">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider" :style="{ color: 'var(--text-secondary)' }">Company Holidays</h3>
          <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">From your assigned Holiday List</p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <label class="text-xs whitespace-nowrap" :style="{ color: 'var(--text-tertiary)' }">Filter:</label>
          <div class="relative">
            <select v-model="holidaysMonthFilter"
              class="input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[160px]">
              <option v-for="opt in holidaysMonthOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
            <ChevronDown :size="14" class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
              :style="{ color: 'var(--text-tertiary)' }" />
          </div>
        </div>
      </div>
      <div class="relative">
        <div class="holidays-scroll grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-64 overflow-y-auto overflow-x-hidden">
          <div v-for="h in filteredHolidays" :key="h.holiday_date"
            class="flex items-center gap-3 py-2 px-3 rounded-lg"
            :style="{ backgroundColor: 'var(--glass-bg)', border: '1px solid var(--border-color)' }">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
              :style="{ backgroundColor: 'var(--warning-bg)', color: 'var(--warning-text)' }">
              <Calendar :size="18" :stroke-width="1.8" />
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">
                {{ new Date(h.holiday_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }}
              </p>
              <p class="text-xs truncate" :style="{ color: 'var(--text-tertiary)' }">{{ h.description || 'Holiday' }}</p>
            </div>
          </div>
        </div>
        <p v-if="filteredHolidays.length === 0" class="text-sm py-6 text-center" :style="{ color: 'var(--text-tertiary)' }">
          No holidays in selected month
        </p>
      </div>
    </div>

    <!-- Leave Balance Cards -->
    <div>
      <h3 class="text-sm font-semibold uppercase tracking-wider mb-4" :style="{ color: 'var(--text-secondary)' }">Leave Balance</h3>
      <p class="text-xs mb-4" :style="{ color: 'var(--text-tertiary)' }">Casual Leave, Sick Leave, Earned Leave, Regional Holidays</p>
      <div v-if="balance.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div v-for="(b, idx) in balance" :key="b.leave_type"
          class="glass-card-hover p-5"
          :style="{
            boxShadow: `inset 0 0 0 1px ${getTypeColor(idx).ring}`,
          }">
          <p class="text-sm font-medium mb-2 truncate" :title="b.leave_type" :style="{ color: 'var(--text-secondary)' }">
            {{ b.leave_type }}
          </p>
          <p class="text-3xl font-bold" :style="{ color: getTypeColor(idx).text }">
            {{ b.balance }}
          </p>
          <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">days</p>
        </div>
        <div class="glass-card p-5" :style="{ boxShadow: 'inset 0 0 0 1px rgba(20,184,166,0.2)' }">
          <p class="text-sm font-medium mb-2" :style="{ color: 'var(--text-secondary)' }">Total</p>
          <p class="text-3xl font-bold" :style="{ color: 'var(--accent)' }">{{ totalBalance }}</p>
          <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">days remaining</p>
        </div>
      </div>
      <div v-else class="glass-card p-8 text-center">
        <Palmtree :size="32" class="mx-auto mb-2" :style="{ color: 'var(--text-tertiary)' }" />
        <p class="text-sm" :style="{ color: 'var(--text-tertiary)' }">No leave balance data available</p>
      </div>
    </div>

    <!-- Applications List -->
    <div>
      <h3 class="text-sm font-semibold uppercase tracking-wider mb-4" :style="{ color: 'var(--text-secondary)' }">
        My Applications
      </h3>
      <div v-if="applications.length" class="glass-card overflow-hidden">
        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr :style="{ borderBottom: '1px solid var(--border-color)' }">
                <th class="text-left text-xs font-semibold uppercase tracking-wider px-5 py-3" :style="{ color: 'var(--text-tertiary)' }">Type</th>
                <th class="text-left text-xs font-semibold uppercase tracking-wider px-5 py-3" :style="{ color: 'var(--text-tertiary)' }">Period</th>
                <th class="text-center text-xs font-semibold uppercase tracking-wider px-5 py-3" :style="{ color: 'var(--text-tertiary)' }">Days</th>
                <th class="text-center text-xs font-semibold uppercase tracking-wider px-5 py-3" :style="{ color: 'var(--text-tertiary)' }">Status</th>
                <th class="text-right text-xs font-semibold uppercase tracking-wider px-5 py-3" :style="{ color: 'var(--text-tertiary)' }">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="app in applications" :key="app.name"
                class="transition-colors"
                :style="{ borderBottom: '1px solid var(--border-color)' }">
                <td class="px-5 py-4">
                  <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">{{ app.leave_type }}</p>
                </td>
                <td class="px-5 py-4">
                  <p class="text-sm" :style="{ color: 'var(--text-secondary)' }">
                    {{ new Date(app.from_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                    <template v-if="app.from_date !== app.to_date">
                      — {{ new Date(app.to_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                    </template>
                  </p>
                </td>
                <td class="px-5 py-4 text-center">
                  <span class="text-sm font-semibold" :style="{ color: 'var(--heading-color)' }">{{ app.total_leave_days }}</span>
                </td>
                <td class="px-5 py-4 text-center">
                  <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold"
                    :style="{ backgroundColor: getStatusStyle(app.status).bg, color: getStatusStyle(app.status).text }">
                    {{ app.status }}
                  </span>
                </td>
                <td class="px-5 py-4 text-right">
                  <button v-if="app.status === 'Open'" @click="cancelLeave(app.name)"
                    class="text-xs transition-colors" :style="{ color: 'var(--danger-text)' }">
                    Cancel
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Mobile cards -->
        <div class="sm:hidden divide-y" :style="{ borderColor: 'var(--border-color)' }">
          <div v-for="app in applications" :key="app.name" class="p-4 space-y-2">
            <div class="flex items-center justify-between">
              <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">{{ app.leave_type }}</p>
              <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold"
                :style="{ backgroundColor: getStatusStyle(app.status).bg, color: getStatusStyle(app.status).text }">
                {{ app.status }}
              </span>
            </div>
            <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">
              {{ new Date(app.from_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              <template v-if="app.from_date !== app.to_date">
                — {{ new Date(app.to_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              </template>
              &middot; {{ app.total_leave_days }} day{{ app.total_leave_days !== 1 ? 's' : '' }}
            </p>
            <button v-if="app.status === 'Open'" @click="cancelLeave(app.name)"
              class="text-xs" :style="{ color: 'var(--danger-text)' }">Cancel</button>
          </div>
        </div>
      </div>
      <div v-else class="glass-card p-8 text-center">
        <Calendar :size="32" class="mx-auto mb-2" :style="{ color: 'var(--text-tertiary)' }" />
        <p class="text-sm" :style="{ color: 'var(--text-tertiary)' }">No leave applications yet</p>
      </div>
    </div>
  </div>

  <!-- Apply Leave Modal -->
  <transition name="modal">
    <div v-if="showApplyForm" class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
      :style="{ backgroundColor: 'var(--overlay-bg)' }"
      @click.self="showApplyForm = false">
      <div class="modal-content glass-card w-full max-w-md p-6 space-y-5">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold" :style="{ color: 'var(--heading-color)' }">Apply for Leave</h2>
          <button @click="showApplyForm = false" class="p-1 transition-colors" :style="{ color: 'var(--text-tertiary)' }">
            <X :size="20" />
          </button>
        </div>

        <form @submit.prevent="submitLeave" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1.5" :style="{ color: 'var(--text-secondary)' }">Leave Type</label>
            <div class="relative">
              <select v-model="form.leave_type" class="input-dark appearance-none pr-10 cursor-pointer"
                :disabled="!leaveTypes.length">
                <option value="" disabled>Select leave type</option>
                <option v-for="t in leaveTypes" :key="t" :value="t">{{ t }}</option>
                <option v-if="!leaveTypes.length" value="" disabled>No leave types</option>
              </select>
              <ChevronDown :size="16" class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
                :style="{ color: 'var(--text-tertiary)' }" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium mb-1.5" :style="{ color: 'var(--text-secondary)' }">From</label>
              <input type="date" v-model="form.from_date" required class="input-dark" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1.5" :style="{ color: 'var(--text-secondary)' }">To</label>
              <input type="date" v-model="form.to_date" required class="input-dark" />
            </div>
          </div>

          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" :true-value="1" :false-value="0" v-model="form.half_day"
              class="w-4 h-4 rounded" :style="{ accentColor: 'var(--accent)' }" />
            <span class="text-sm" :style="{ color: 'var(--text-secondary)' }">Half day</span>
          </label>

          <div>
            <label class="block text-sm font-medium mb-1.5" :style="{ color: 'var(--text-secondary)' }">
              Reason <span :style="{ color: 'var(--text-tertiary)' }">(optional)</span>
            </label>
            <textarea v-model="form.reason" rows="3" class="input-dark resize-none"
              placeholder="Briefly describe the reason..."></textarea>
          </div>

          <div v-if="applyError" class="flex items-start gap-2 text-sm p-3 rounded-xl"
            :style="{ backgroundColor: 'var(--danger-bg)', color: 'var(--danger-text)' }">
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
                                    flex items-center gap-2 px-5 py-3 rounded-xl shadow-lg"
      :style="{
        backgroundColor: 'var(--success-bg)',
        border: '1px solid var(--success-text)',
        color: 'var(--success-text)',
      }">
      <CheckCircle2 :size="18" />
      <span class="text-sm font-medium">{{ applySuccess }}</span>
      <button @click="applySuccess = ''" class="ml-2 opacity-60 hover:opacity-100">
        <X :size="16" />
      </button>
    </div>
  </transition>
  </div>
</template>
