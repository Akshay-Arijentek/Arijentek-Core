<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { managerApi, expensesApi } from '../services/api';
import {
  CheckCircle,
  XCircle,
  Calendar,
  User,
  Clock,
  Briefcase,
  AlertCircle,
  DollarSign,
  Receipt
} from 'lucide-vue-next';

interface LeaveApplication {
  name: string;
  employee_name: string;
  leave_type: string;
  from_date: string;
  to_date: string;
  total_leave_days: number;
  description: string;
  creation: string;
}

interface ExpenseClaim {
  name: string;
  employee_name: string;
  total_claimed_amount: number;
  posting_date: string;
  status: string;
  approval_status: string;
}

const activeTab = ref<'leave' | 'expense'>('leave');
const leaves = ref<LeaveApplication[]>([]);
const expenses = ref<ExpenseClaim[]>([]);
const loading = ref(true);
const processing = ref<string | null>(null);
const error = ref('');
const successMessage = ref('');

async function loadData() {
  loading.value = true;
  try {
    const [leavesData, expensesData] = await Promise.all([
      managerApi.getTeamLeaves(),
      expensesApi.getTeamExpenses()
    ]);
    leaves.value = Array.isArray(leavesData) ? leavesData : [];
    expenses.value = Array.isArray(expensesData) ? expensesData : [];
  } catch (e) {
    console.error(e);
    error.value = 'Failed to load data';
  } finally {
    loading.value = false;
  }
}

async function handleProcessLeave(appId: string, status: 'Approved' | 'Rejected') {
  if (processing.value) return;
  processing.value = appId;
  error.value = '';
  successMessage.value = '';

  try {
    const res = await managerApi.processLeave(appId, status);
    if (res.status === 'success' || res.success) {
      successMessage.value = `Leave ${status} successfully`;
      leaves.value = leaves.value.filter(a => a.name !== appId);
    } else {
      error.value = res.error || 'Action failed';
    }
  } catch (e: any) {
    error.value = e.message || 'Error processing request';
  } finally {
    processing.value = null;
    setTimeout(() => { successMessage.value = ''; error.value = ''; }, 3000);
  }
}

async function handleProcessExpense(appId: string, status: 'Approve' | 'Reject') {
  if (processing.value) return;
  processing.value = appId;
  error.value = '';
  successMessage.value = '';

  try {
    const res = await expensesApi.process(appId, status);
    if (res.status === 'success' || res.success) {
      successMessage.value = `Expense ${status}d successfully`;
      expenses.value = expenses.value.filter(a => a.name !== appId);
    } else {
      error.value = res.error || 'Action failed';
    }
  } catch (e: any) {
    error.value = e.message || 'Error processing request';
  } finally {
    processing.value = null;
    setTimeout(() => { successMessage.value = ''; error.value = ''; }, 3000);
  }
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString();
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <div>
    <div class="mb-8 animate-fade-in">
      <h1 class="text-2xl sm:text-3xl font-bold text-white">Team Approvals</h1>
      <p class="text-sm text-slate-500 mt-1">Manage requests from your team</p>
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-6 border-b border-white/5">
      <button 
        @click="activeTab = 'leave'"
        class="pb-2 text-sm font-medium transition-colors relative"
        :class="activeTab === 'leave' ? 'text-teal-400' : 'text-slate-500 hover:text-slate-300'"
      >
        Leave Requests
        <span v-if="activeTab === 'leave'" class="absolute bottom-0 left-0 w-full h-0.5 bg-teal-500 rounded-full"></span>
      </button>
      <button 
        @click="activeTab = 'expense'"
        class="pb-2 text-sm font-medium transition-colors relative"
        :class="activeTab === 'expense' ? 'text-teal-400' : 'text-slate-500 hover:text-slate-300'"
      >
        Expense Claims
        <span v-if="activeTab === 'expense'" class="absolute bottom-0 left-0 w-full h-0.5 bg-teal-500 rounded-full"></span>
      </button>
    </div>

    <!-- Alert Messages -->
    <div v-if="error" class="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm flex items-center gap-2">
      <AlertCircle :size="16" />
      {{ error }}
    </div>
    <div v-if="successMessage" class="mb-4 p-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg text-sm flex items-center gap-2">
      <CheckCircle :size="16" />
      {{ successMessage }}
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="space-y-4">
       <div v-for="i in 3" :key="i" class="glass-card p-6 animate-pulse">
         <div class="h-4 bg-white/10 w-1/3 mb-2 rounded"></div>
         <div class="h-4 bg-white/5 w-1/2 rounded"></div>
       </div>
    </div>

    <!-- Leave Tab -->
    <div v-else-if="activeTab === 'leave'">
        <div v-if="leaves.length === 0" class="glass-card p-12 flex flex-col items-center justify-center text-center">
          <div class="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4">
            <CheckCircle class="text-emerald-400" :size="32" />
          </div>
          <h3 class="text-lg font-medium text-white mb-1">No pending leaves</h3>
          <p class="text-slate-500">You're all caught up!</p>
        </div>

        <div v-else class="grid gap-4">
          <div v-for="app in leaves" :key="app.name" class="glass-card p-6 animate-slide-up group">
            <div class="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <div class="w-10 h-10 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-lg">
                    {{ app.employee_name.charAt(0) }}
                  </div>
                  <div>
                    <h3 class="text-lg font-medium text-white">{{ app.employee_name }}</h3>
                    <div class="flex items-center gap-2 text-xs text-slate-500">
                      <Briefcase :size="12" />
                      {{ app.leave_type }}
                      <span class="w-1 h-1 bg-slate-600 rounded-full"></span>
                      <Clock :size="12" />
                      Applied {{ formatDate(app.creation) }}
                    </div>
                  </div>
                </div>

                <div class="mt-4 pl-13 md:pl-0 grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div class="bg-white/5 p-3 rounded-lg text-center">
                    <p class="text-xs text-slate-500 mb-1">From</p>
                    <p class="text-sm font-medium text-slate-200">{{ formatDate(app.from_date) }}</p>
                  </div>
                  <div class="bg-white/5 p-3 rounded-lg text-center">
                    <p class="text-xs text-slate-500 mb-1">To</p>
                    <p class="text-sm font-medium text-slate-200">{{ formatDate(app.to_date) }}</p>
                  </div>
                  <div class="bg-white/5 p-3 rounded-lg text-center">
                    <p class="text-xs text-slate-500 mb-1">Days</p>
                    <p class="text-sm font-medium text-amber-400">{{ app.total_leave_days }}</p>
                  </div>
                </div>

                <div v-if="app.description" class="mt-4 p-3 bg-slate-900/30 rounded-lg border border-white/5">
                  <p class="text-sm text-slate-400 italic">"{{ app.description }}"</p>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex md:flex-col gap-2 min-w-[120px]">
                <button
                  @click="handleProcessLeave(app.name, 'Approved')"
                  :disabled="!!processing"
                  class="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
                >
                  <template v-if="processing === app.name">
                    <span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                  </template>
                  <template v-else>
                    <CheckCircle :size="16" />
                    Approve
                  </template>
                </button>
                
                <button
                  @click="handleProcessLeave(app.name, 'Rejected')"
                  :disabled="!!processing"
                  class="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50"
                >
                   <XCircle :size="16" />
                   Reject
                </button>
              </div>
            </div>
          </div>
        </div>
    </div>

    <!-- Expense Tab -->
    <div v-else-if="activeTab === 'expense'">
        <div v-if="expenses.length === 0" class="glass-card p-12 flex flex-col items-center justify-center text-center">
          <div class="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4">
            <CheckCircle class="text-emerald-400" :size="32" />
          </div>
          <h3 class="text-lg font-medium text-white mb-1">No pending expenses</h3>
          <p class="text-slate-500">You're all caught up!</p>
        </div>

        <div v-else class="grid gap-4">
          <div v-for="exp in expenses" :key="exp.name" class="glass-card p-6 animate-slide-up group">
            <div class="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <div class="w-10 h-10 rounded-full bg-pink-500/20 text-pink-400 flex items-center justify-center font-bold text-lg">
                    {{ exp.employee_name.charAt(0) }}
                  </div>
                  <div>
                    <h3 class="text-lg font-medium text-white">{{ exp.employee_name }}</h3>
                     <div class="flex items-center gap-2 text-xs text-slate-500">
                      <Receipt :size="12" />
                      Expense Claim
                      <span class="w-1 h-1 bg-slate-600 rounded-full"></span>
                      <Clock :size="12" />
                      {{ formatDate(exp.posting_date) }}
                    </div>
                  </div>
                </div>

                <div class="mt-4 pl-13 md:pl-0">
                  <p class="text-2xl font-bold text-white mb-1">{{ Number(exp.total_claimed_amount).toLocaleString() }}</p>
                  <p class="text-xs text-slate-500">Total Claimed Amount</p>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex md:flex-col gap-2 min-w-[120px]">
                <button
                  @click="handleProcessExpense(exp.name, 'Approve')"
                  :disabled="!!processing"
                  class="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
                >
                  <template v-if="processing === exp.name">
                    <span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                  </template>
                  <template v-else>
                    <CheckCircle :size="16" />
                    Approve
                  </template>
                </button>
                
                <button
                  @click="handleProcessExpense(exp.name, 'Reject')"
                  :disabled="!!processing"
                  class="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50"
                >
                   <XCircle :size="16" />
                   Reject
                </button>
              </div>
            </div>
          </div>
        </div>
    </div>
  </div>
</template>
