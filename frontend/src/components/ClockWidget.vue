<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useAuthStore } from '../stores/auth';
import { attendanceApi } from '../services/api';

const auth = useAuthStore();
const loading = ref(false);
const error = ref('');
const isClockedIn = ref(false);
const clockInTime = ref<Date | null>(null);
const elapsed = ref(0); // seconds since clock-in
let timerInterval: ReturnType<typeof setInterval> | null = null;

const SHIFT_SECONDS = 8 * 60 * 60; // 8 hours

// Progress 0..1
const progress = computed(() => {
  if (!isClockedIn.value || elapsed.value === 0) return 0;
  return Math.min(elapsed.value / SHIFT_SECONDS, 1);
});

const shiftComplete = computed(() => progress.value >= 1);

// SVG ring math
const RADIUS = 82;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const dashOffset = computed(() => CIRCUMFERENCE * (1 - progress.value));

// Timer display HH:MM:SS
const timerDisplay = computed(() => {
  const h = Math.floor(elapsed.value / 3600);
  const m = Math.floor((elapsed.value % 3600) / 60);
  const s = elapsed.value % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
});

// Clock-in time formatted
const clockInTimeFormatted = computed(() => {
  if (!clockInTime.value) return '';
  return clockInTime.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
});

// Ring color
const ringColor = computed(() => {
  if (shiftComplete.value) return '#22c55e'; // green
  return '#14b8a6'; // teal
});

const glowColor = computed(() => {
  if (shiftComplete.value) return 'rgba(34, 197, 94, 0.35)';
  return 'rgba(20, 184, 166, 0.25)';
});

function startTimer() {
  stopTimer();
  timerInterval = setInterval(() => {
    if (clockInTime.value) {
      elapsed.value = Math.floor((Date.now() - clockInTime.value.getTime()) / 1000);
    }
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

async function fetchStatus() {
  try {
    const data = await attendanceApi.getTodayCheckin();
    if (data.clock_in && !data.clock_out) {
      isClockedIn.value = true;
      clockInTime.value = new Date(data.clock_in);
      elapsed.value = Math.floor((Date.now() - clockInTime.value.getTime()) / 1000);
      startTimer();
    } else {
      isClockedIn.value = false;
      clockInTime.value = data.clock_in ? new Date(data.clock_in) : null;
      if (data.clock_in && data.clock_out) {
        // Show total worked time
        elapsed.value = Math.floor(
          (new Date(data.clock_out).getTime() - new Date(data.clock_in).getTime()) / 1000
        );
      }
    }
  } catch {
    // Silently fail - will show default state
  }
}

async function handlePunch() {
  loading.value = true;
  error.value = '';
  try {
    const result = await attendanceApi.punch();
    if (result.status === 'success') {
      if (result.log_type === 'IN') {
        isClockedIn.value = true;
        clockInTime.value = new Date(result.time);
        elapsed.value = 0;
        startTimer();
      } else {
        isClockedIn.value = false;
        stopTimer();
        // Keep elapsed to show total worked
      }
    } else {
      error.value = result.error || 'Punch failed';
    }
  } catch (e: any) {
    error.value = e.message || 'Something went wrong';
  } finally {
    loading.value = false;
  }
}

onMounted(fetchStatus);
onUnmounted(stopTimer);

const emit = defineEmits<{ punched: [] }>();
watch(isClockedIn, () => emit('punched'));
</script>

<template>
  <div class="flex flex-col items-center">
    <!-- SVG Clock Ring -->
    <div class="relative mb-6">
      <svg width="200" height="200" class="transform -rotate-90">
        <!-- Background ring -->
        <circle
          :cx="100" :cy="100" :r="RADIUS"
          fill="none"
          class="clock-ring-bg"
          stroke-width="6"
        />
        <!-- Progress ring -->
        <circle
          :cx="100" :cy="100" :r="RADIUS"
          fill="none"
          :stroke="ringColor"
          stroke-width="6"
          stroke-linecap="round"
          class="clock-ring-progress"
          :stroke-dasharray="CIRCUMFERENCE"
          :stroke-dashoffset="dashOffset"
        />
      </svg>

      <!-- Center button -->
      <button
        @click="handlePunch"
        :disabled="loading"
        class="absolute inset-0 m-auto w-[140px] h-[140px] rounded-full
               flex flex-col items-center justify-center gap-1
               transition-all duration-500 focus:outline-none"
        :class="[
          isClockedIn
            ? (shiftComplete
                ? 'bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25'
                : 'bg-accent/10 text-accent hover:bg-accent/20')
            : 'bg-white/[0.05] text-slate-300 hover:bg-white/[0.08] hover:text-white'
        ]"
        :style="isClockedIn ? { boxShadow: `0 0 40px ${glowColor}` } : {}"
      >
        <div v-if="loading" class="w-6 h-6 border-2 border-current border-t-transparent rounded-full animate-spin" />
        <template v-else>
          <span class="text-[11px] font-semibold uppercase tracking-wider opacity-70">
            {{ isClockedIn ? 'Clock Out' : 'Clock In' }}
          </span>
          <span v-if="isClockedIn" class="text-2xl font-bold tabular-nums tracking-tight">
            {{ timerDisplay }}
          </span>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </template>
      </button>
    </div>

    <!-- Status text -->
    <div class="text-center space-y-1.5">
      <div v-if="shiftComplete" class="badge-success mb-2">
        Shift Complete
      </div>

      <p v-if="isClockedIn && clockInTimeFormatted" class="text-sm text-slate-400">
        Clocked in at <span class="text-white font-medium">{{ clockInTimeFormatted }}</span>
      </p>
      <p v-else-if="!isClockedIn && elapsed > 0" class="text-sm text-slate-400">
        Worked <span class="text-white font-medium">{{ timerDisplay }}</span> today
      </p>
      <p v-else class="text-sm text-slate-500">
        Tap to start your shift
      </p>
    </div>

    <p v-if="error" class="mt-3 text-xs text-red-400 text-center">{{ error }}</p>
  </div>
</template>
