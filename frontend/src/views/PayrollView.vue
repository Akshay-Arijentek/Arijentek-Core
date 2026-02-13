<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { payrollApi } from '../services/api';
import { useAuthStore } from '../stores/auth';
import {
  Wallet,
  Download,
  FileText,
  TrendingUp,
  Calendar,
  Banknote,
  Loader2,
  Play,
  CheckCircle2,
  AlertCircle,
} from 'lucide-vue-next';

const auth = useAuthStore();
const loading = ref(true);
const generateLoading = ref(false);
const generateError = ref('');
const generateSuccess = ref('');

// Generate payroll form - defaults to previous month
const now = new Date();
const prevMonth = now.getMonth() === 0 ? 12 : now.getMonth();
const prevYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
const genMonth = ref(prevMonth);
const genYear = ref(prevYear);

interface SalarySlip {
  name: string;
  start_date: string;
  end_date: string;
  net_pay: number;
  gross_pay: number;
  month: string;
  year: number;
}

const slips = ref<SalarySlip[]>([]);

const totalNet = computed(() =>
  slips.value.reduce((s, sl) => s + (sl.net_pay || 0), 0)
);
const totalGross = computed(() =>
  slips.value.reduce((s, sl) => s + (sl.gross_pay || 0), 0)
);
const avgNet = computed(() =>
  slips.value.length ? Math.round(totalNet.value / slips.value.length) : 0
);

function formatCurrency(val: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(val);
}

function downloadSlip(name: string) {
  const token = auth.csrfToken || (window as any).csrf_token || '';
  const url = payrollApi.getDownloadUrl(name);
  window.open(url, '_blank');
}

async function loadData() {
  loading.value = true;
  try {
    const data = await payrollApi.getSlips();
    slips.value = Array.isArray(data) ? data : [];
  } catch {
    slips.value = [];
  } finally {
    loading.value = false;
  }
}

async function generatePayroll() {
  generateLoading.value = true;
  generateError.value = '';
  generateSuccess.value = '';
  try {
    const result = await payrollApi.generatePayroll(genMonth.value, genYear.value);
    if (result?.success) {
      generateSuccess.value = result.message || 'Payroll generated successfully';
      await loadData();
    } else {
      generateError.value = result?.error || 'Failed to generate payroll';
    }
  } catch (e: any) {
    generateError.value = e?.message || 'Something went wrong';
  } finally {
    generateLoading.value = false;
  }
}

const monthOptions = [
  { value: 1, label: 'January' }, { value: 2, label: 'February' }, { value: 3, label: 'March' },
  { value: 4, label: 'April' }, { value: 5, label: 'May' }, { value: 6, label: 'June' },
  { value: 7, label: 'July' }, { value: 8, label: 'August' }, { value: 9, label: 'September' },
  { value: 10, label: 'October' }, { value: 11, label: 'November' }, { value: 12, label: 'December' },
];

onMounted(loadData);
</script>

<template>
  <div>
  <!-- Header -->
  <div class="mb-8 animate-fade-in">
    <h1 class="text-2xl sm:text-3xl font-bold text-white">Payroll</h1>
    <p class="text-sm text-slate-500 mt-1">View and download your salary slips</p>
  </div>

  <!-- Loading -->
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
  </div>

  <div v-else class="space-y-6 animate-slide-up">
    <!-- Generate Payroll (HR/Manager only) -->
    <div v-if="auth.hasPayrollPermission" class="glass-card p-6">
      <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Generate Payslips</h3>
      <p class="text-sm text-slate-500 mb-4">Create salary slips for all eligible employees for the selected month</p>
      <div class="flex flex-wrap items-end gap-4">
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1.5">Month</label>
          <select v-model.number="genMonth" class="input-dark w-40">
            <option v-for="m in monthOptions" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1.5">Year</label>
          <input v-model.number="genYear" type="number" min="2020" max="2030"
            class="input-dark w-24" />
        </div>
        <button @click="generatePayroll" :disabled="generateLoading"
          class="btn-accent flex items-center gap-2 px-5 py-2.5">
          <Loader2 v-if="generateLoading" :size="18" class="animate-spin" />
          <Play v-else :size="18" :stroke-width="1.8" />
          {{ generateLoading ? 'Generating...' : 'Generate Payroll' }}
        </button>
      </div>
      <div v-if="generateError" class="mt-4 flex items-start gap-2 text-sm text-red-400 bg-red-500/10 p-3 rounded-xl">
        <AlertCircle :size="16" class="mt-0.5 shrink-0" />
        {{ generateError }}
      </div>
      <div v-if="generateSuccess" class="mt-4 flex items-center gap-2 text-sm text-emerald-400 bg-emerald-500/10 p-3 rounded-xl">
        <CheckCircle2 :size="16" class="shrink-0" />
        {{ generateSuccess }}
      </div>
    </div>

    <!-- Summary cards -->
    <div v-if="slips.length" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="glass-card-hover p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-medium text-slate-400">Avg Net Pay</span>
          <div class="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <TrendingUp :size="18" :stroke-width="1.8" />
          </div>
        </div>
        <p class="text-2xl font-bold text-emerald-400">{{ formatCurrency(avgNet) }}</p>
        <p class="text-xs text-slate-500 mt-1">per month</p>
      </div>
      <div class="glass-card-hover p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-medium text-slate-400">YTD Gross</span>
          <div class="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
            <Banknote :size="18" :stroke-width="1.8" />
          </div>
        </div>
        <p class="text-2xl font-bold text-blue-400">{{ formatCurrency(totalGross) }}</p>
        <p class="text-xs text-slate-500 mt-1">{{ slips.length }} slip{{ slips.length !== 1 ? 's' : '' }}</p>
      </div>
      <div class="glass-card-hover p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-medium text-slate-400">YTD Net</span>
          <div class="w-9 h-9 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center">
            <Wallet :size="18" :stroke-width="1.8" />
          </div>
        </div>
        <p class="text-2xl font-bold text-teal-400">{{ formatCurrency(totalNet) }}</p>
        <p class="text-xs text-slate-500 mt-1">total credited</p>
      </div>
    </div>

    <!-- Salary Slips list -->
    <div>
      <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Salary Slips</h3>

      <div v-if="slips.length" class="space-y-3">
        <div v-for="slip in slips" :key="slip.name"
          class="glass-card-hover p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <!-- Left: Month info -->
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center shrink-0">
              <Calendar :size="20" :stroke-width="1.8" />
            </div>
            <div>
              <p class="text-base font-semibold text-white">{{ slip.month }} {{ slip.year }}</p>
              <p class="text-xs text-slate-500">
                {{ new Date(slip.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                — {{ new Date(slip.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              </p>
            </div>
          </div>

          <!-- Center: Pay info -->
          <div class="flex items-center gap-6 sm:gap-8">
            <div>
              <p class="text-xs text-slate-500">Gross</p>
              <p class="text-sm font-semibold text-slate-300">{{ formatCurrency(slip.gross_pay) }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500">Net Pay</p>
              <p class="text-sm font-bold text-emerald-400">{{ formatCurrency(slip.net_pay) }}</p>
            </div>
          </div>

          <!-- Right: Download -->
          <button @click="downloadSlip(slip.name)"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl
                   bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06]
                   text-sm font-medium text-slate-300 hover:text-white transition-all
                   self-start sm:self-center shrink-0">
            <Download :size="16" :stroke-width="1.8" />
            Download
          </button>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="glass-card p-12 text-center">
        <FileText :size="40" class="mx-auto text-slate-600 mb-3" />
        <p class="text-slate-400 font-medium">No salary slips found</p>
        <p class="text-sm text-slate-500 mt-1">Your payslips will appear here once processed</p>
      </div>
    </div>
  </div>
  </div>
</template>
