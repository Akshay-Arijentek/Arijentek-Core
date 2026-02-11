<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { LogIn, Loader2, AlertCircle } from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  error.value = ''

  try {
    const result = await authStore.login(username.value, password.value)

    if (result && result.success) {
      router.push('/')
    } else {
      const errObj = result?.error as any
      error.value = errObj?.message || errObj || 'Invalid credentials'
    }
  } catch (e: any) {
    error.value = e.message || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden px-4">
    <!-- Background gradient orbs -->
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-500/8 rounded-full blur-3xl" />

    <div class="w-full max-w-[420px] relative z-10 animate-fade-in">
      <!-- Logo -->
      <div class="text-center mb-10">
        <div class="w-14 h-14 rounded-2xl bg-accent/15 flex items-center justify-center mx-auto mb-5
                    ring-1 ring-accent/20">
          <span class="text-accent text-2xl font-bold">A</span>
        </div>
        <h1 class="text-3xl font-bold text-white tracking-tight">Employee Portal</h1>
        <p class="text-slate-500 mt-2 text-sm">Sign in to access your dashboard</p>
      </div>

      <!-- Card -->
      <div class="glass-card p-8">
        <form @submit.prevent="handleLogin" class="space-y-5">
          <!-- Username -->
          <div>
            <label for="username" class="block text-sm font-medium text-slate-400 mb-1.5">
              Username / Employee ID
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              class="input-dark"
              placeholder="Enter your username"
            />
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="block text-sm font-medium text-slate-400 mb-1.5">
              Password
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              class="input-dark"
              placeholder="Enter your password"
            />
          </div>

          <!-- Error -->
          <div v-if="error"
            class="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20
                   p-3 rounded-xl">
            <AlertCircle :size="16" class="mt-0.5 shrink-0" />
            <span>{{ error }}</span>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="loading || !username || !password"
            class="btn-accent w-full flex items-center justify-center gap-2 py-3.5"
          >
            <Loader2 v-if="loading" :size="18" class="animate-spin" />
            <LogIn v-else :size="18" />
            <span>{{ loading ? 'Signing in...' : 'Sign in' }}</span>
          </button>
        </form>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-slate-600 mt-8">
        Powered by <span class="text-slate-500">Arijentek Solutions</span>
      </p>
    </div>
  </div>
</template>
