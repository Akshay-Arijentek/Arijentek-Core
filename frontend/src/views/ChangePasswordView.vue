<script setup lang="ts">
import { ref } from 'vue';
import { authApi } from '../services/api';
import { Lock, Key, AlertCircle, CheckCircle, Eye, EyeOff } from 'lucide-vue-next';

const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);
const error = ref('');
const success = ref('');

const showOld = ref(false);
const showNew = ref(false);
const showConfirm = ref(false);

async function handleChangePassword() {
  error.value = '';
  success.value = '';

  if (newPassword.value !== confirmPassword.value) {
    error.value = "New passwords don't match";
    return;
  }

  // Frontend validation for immediate feedback (backend also validates)
  if (newPassword.value.length < 8) {
     error.value = "Password must be at least 8 characters long";
     return;
  }

  loading.value = true;
  try {
    const res = await authApi.changePassword(oldPassword.value, newPassword.value);
    if (res.success) {
      success.value = "Password changed successfully";
      oldPassword.value = '';
      newPassword.value = '';
      confirmPassword.value = '';
    } else {
      error.value = res.error || "Failed to change password";
    }
  } catch (e: any) {
    error.value = e.message || "An error occurred";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="max-w-md mx-auto">
    <div class="mb-8 animate-fade-in text-center">
      <h1 class="text-2xl sm:text-3xl font-bold text-white">Security</h1>
      <p class="text-sm text-slate-500 mt-1">Update your password</p>
    </div>

    <div class="glass-card p-6 animate-slide-up">
      <form @submit.prevent="handleChangePassword" class="space-y-4">
        
        <div v-if="error" class="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle :size="16" />
          {{ error }}
        </div>
        
        <div v-if="success" class="p-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg text-sm flex items-center gap-2">
          <CheckCircle :size="16" />
          {{ success }}
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Current Password</label>
          <div class="relative group">
            <input
              v-model="oldPassword"
              :type="showOld ? 'text' : 'password'"
              required
              class="w-full bg-slate-900/50 border border-white/10 rounded-lg px-4 py-2.5 pl-10 pr-16 text-white focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-all placeholder:text-slate-600"
              placeholder="Enter current password"
            />
            <Key :size="18" class="absolute left-3 top-2.5 text-slate-500 group-focus-within:text-teal-400 transition-colors" />
            
            <button type="button" @click="showOld = !showOld" 
              class="absolute right-12 top-2.5 text-slate-500 hover:text-white transition-colors focus:outline-none">
              <EyeOff v-if="showOld" :size="18" />
              <Eye v-else :size="18" />
            </button>
          </div>
        </div>

        <div>
           <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">New Password</label>
           <div class="relative group">
            <input
              v-model="newPassword"
              :type="showNew ? 'text' : 'password'"
              required
              class="w-full bg-slate-900/50 border border-white/10 rounded-lg px-4 py-2.5 pl-10 pr-16 text-white focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-all placeholder:text-slate-600"
              placeholder="Min 8 chars, uppercase, digit, special"
            />
            <Lock :size="18" class="absolute left-3 top-2.5 text-slate-500 group-focus-within:text-teal-400 transition-colors" />
            
            <button type="button" @click="showNew = !showNew" 
              class="absolute right-12 top-2.5 text-slate-500 hover:text-white transition-colors focus:outline-none">
              <EyeOff v-if="showNew" :size="18" />
              <Eye v-else :size="18" />
            </button>
          </div>
        </div>

        <div>
           <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Confirm New Password</label>
           <div class="relative group">
            <input
              v-model="confirmPassword"
              :type="showConfirm ? 'text' : 'password'"
              required
              class="w-full bg-slate-900/50 border border-white/10 rounded-lg px-4 py-2.5 pl-10 pr-16 text-white focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-all placeholder:text-slate-600"
              placeholder="Confirm new password"
            />
            <Lock :size="18" class="absolute left-3 top-2.5 text-slate-500 group-focus-within:text-teal-400 transition-colors" />
            
            <button type="button" @click="showConfirm = !showConfirm" 
              class="absolute right-12 top-2.5 text-slate-500 hover:text-white transition-colors focus:outline-none">
              <EyeOff v-if="showConfirm" :size="18" />
              <Eye v-else :size="18" />
            </button>
          </div>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full mt-6 bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-white font-medium py-2.5 rounded-lg shadow-lg shadow-teal-500/20 transition-all active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="loading" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          <span v-else>Update Password</span>
        </button>
      </form>
    </div>
  </div>
</template>
