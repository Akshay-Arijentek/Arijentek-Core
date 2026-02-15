<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { expensesApi } from '../services/api';
import { 
  Receipt, 
  Plus, 
  Upload, 
  X, 
  DollarSign, 
  FileText, 
  CheckCircle, 
  AlertCircle,
  Clock
} from 'lucide-vue-next';

// Data types
interface Expense {
  name: string;
  total_claimed_amount: number;
  posting_date: string;
  approval_status: string;
  status: string;
}

const expenses = ref<Expense[]>([]);
const expenseTypes = ref<string[]>([]);
const loading = ref(true);
const showModal = ref(false);

// Form
const form = ref({
  expense_type: '',
  amount: '',
  description: '',
  proof: null as File | null
});
const submitting = ref(false);
const error = ref('');
const success = ref('');

// Upload
const fileInput = ref<HTMLInputElement | null>(null);

async function loadData() {
  loading.value = true;
  try {
    const [myExp, types] = await Promise.all([
      expensesApi.getMyExpenses(),
      expensesApi.getTypes()
    ]);
    expenses.value = Array.isArray(myExp) ? myExp : [];
    expenseTypes.value = Array.isArray(types) ? types : [];
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    form.value.proof = target.files[0];
  }
}

async function uploadFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file, file.name);
  formData.append('is_private', '1');
  
  // Standard Frappe upload
  const res = await fetch('/api/method/upload_file', {
    method: 'POST',
    headers: {
      'X-Frappe-CSRF-Token': (window as any).csrf_token || ''
    },
    body: formData
  });
  
  const data = await res.json();
  if (data.message && data.message.file_url) {
    return data.message.file_url;
  }
  throw new Error(data.message || "Upload failed");
}

async function submitExpense() {
  if (!form.value.expense_type || !form.value.amount || !form.value.description) {
    error.value = "Please fill all required fields";
    return;
  }

  submitting.value = true;
  error.value = '';
  
  try {
    let proofUrl = '';
    if (form.value.proof) {
       proofUrl = await uploadFile(form.value.proof);
    }

    const payload = {
      expense_type: form.value.expense_type,
      amount: form.value.amount,
      description: form.value.description,
      proof: proofUrl
    };

    const res = await expensesApi.submit(payload);
    if (res.success) {
      success.value = "Expense submitted successfully";
      showModal.value = false;
      // Reset form
      form.value = { expense_type: '', amount: '', description: '', proof: null };
      loadData();
    } else {
      error.value = res.error || "Submission failed";
    }
  } catch (e: any) {
    error.value = e.message || "Error occurred";
  } finally {
    submitting.value = false;
  }
}

function statusColor(status: string) {
  if (status === 'Approved' || status === 'Paid') return 'text-emerald-400 bg-emerald-500/10';
  if (status === 'Rejected') return 'text-red-400 bg-red-500/10';
  return 'text-amber-400 bg-amber-500/10';
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between animate-fade-in">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-white">Expenses</h1>
        <p class="text-sm text-slate-500 mt-1">Manage reimbursement claims</p>
      </div>
      <button @click="showModal = true"
        class="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-teal-500 to-emerald-500 text-white rounded-xl shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 transition-all active:scale-95">
        <Plus :size="18" />
        <span class="hidden sm:inline font-medium">New Claim</span>
      </button>
    </div>

    <!-- Alert -->
    <div v-if="success" class="p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 flex items-center gap-2">
      <CheckCircle :size="18" />
      {{ success }}
      <button @click="success = ''" class="ml-auto"><X :size="16" /></button>
    </div>

    <!-- List -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
       <div v-for="i in 3" :key="i" class="glass-card p-6 h-32 animate-pulse" />
    </div>
    
    <div v-else-if="expenses.length === 0" class="glass-card p-12 text-center text-slate-500 flex flex-col items-center">
       <Receipt :size="48" class="mb-4 opacity-20" />
       <p>No expense claims found</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-slide-up">
      <div v-for="exp in expenses" :key="exp.name" class="glass-card p-5 group hover:border-white/10 transition-colors">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 rounded-lg bg-indigo-500/10 text-indigo-400">
            <DollarSign :size="20" />
          </div>
          <span class="px-2.5 py-1 rounded-full text-xs font-medium border border-white/5" :class="statusColor(exp.approval_status)">
            {{ exp.approval_status }}
          </span>
        </div>
        
        <div class="mb-4">
           <p class="text-2xl font-bold text-white">{{ Number(exp.total_claimed_amount).toLocaleString() }}</p>
           <p class="text-xs text-slate-500 mt-1">{{ exp.name }}</p>
        </div>

        <div class="flex items-center justify-between text-xs text-slate-400 border-t border-white/5 pt-3">
           <div class="flex items-center gap-1.5">
             <Clock :size="14" />
             {{ new Date(exp.posting_date).toLocaleDateString() }}
           </div>
           
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showModal = false"></div>
      <div class="glass-card w-full max-w-lg p-6 relative animate-scale-in">
        <button @click="showModal = false" class="absolute right-4 top-4 text-slate-500 hover:text-white"><X :size="20" /></button>
        
        <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Receipt class="text-teal-400" /> New Expense Claim
        </h2>
        
        <form @submit.prevent="submitExpense" class="space-y-4">
           <!-- Error -->
           <div v-if="error" class="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
             <AlertCircle :size="16" /> {{ error }}
           </div>

           <div>
             <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Expense Type</label>
             <select v-model="form.expense_type" required class="w-full bg-slate-900/50 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-teal-500/50">
               <option value="" disabled>Select Type</option>
               <option v-for="t in expenseTypes" :key="t" :value="t">{{ t }}</option>
             </select>
           </div>

           <div>
             <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Amount</label>
             <input v-model="form.amount" type="number" step="0.01" required placeholder="0.00"
               class="w-full bg-slate-900/50 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-teal-500/50" />
           </div>

           <div>
             <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Description</label>
             <textarea v-model="form.description" rows="3" required placeholder="Reason for expense..."
               class="w-full bg-slate-900/50 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-teal-500/50"></textarea>
           </div>

           <div>
             <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Proof (Bill/Receipt)</label>
             <div class="relative border-2 border-dashed border-white/10 rounded-lg p-4 text-center hover:border-teal-500/30 transition-colors cursor-pointer"
               @click="fileInput?.click()">
               <input ref="fileInput" type="file" class="hidden" accept="image/*,.pdf" @change="handleFileSelect" />
               <Upload :size="24" class="mx-auto mb-2 text-slate-500" />
               <p class="text-sm text-slate-300">{{ form.proof ? form.proof.name : 'Click to upload proof' }}</p>
               <p class="text-xs text-slate-500 mt-1">Image or PDF</p>
             </div>
           </div>

           <button type="submit" :disabled="submitting"
             class="w-full mt-4 bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-white font-medium py-2.5 rounded-lg shadow-lg flex items-center justify-center gap-2">
             <span v-if="submitting" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
             <span v-else>Submit Claim</span>
           </button>
        </form>
      </div>
    </div>
  </div>
</template>
