<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { attendanceApi } from '../services/api';

const auth = useAuthStore();
const loading = ref(false);
const error = ref('');
const isClockedIn = ref(false);
const isCompleted = ref(false); // both IN and OUT done for the day
const clockInTime = ref<Date | null>(null);
const elapsed = ref(0); // seconds since clock-in
let timerInterval: ReturnType<typeof setInterval> | null = null;

const SHIFT_SECONDS = 8 * 60 * 60; // 8 hours
const MAX_SHIFT_SECONDS = 12 * 60 * 60; // 12 hours max

// Progress 0..1
const progress = computed(() => {
  if (elapsed.value === 0) return 0;
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

// Ring color: RED before 8 hrs → GREEN after 8 hrs (safe to clock out)
const ringColor = computed(() => {
  if (isCompleted.value) return '#22c55e'; // green – day complete
  if (shiftComplete.value) return '#22c55e'; // green – safe to clock out
  return '#ef4444'; // red – shift not complete
});

const glowColor = computed(() => {
  if (isCompleted.value) return 'rgba(34, 197, 94, 0.35)';
  if (shiftComplete.value) return 'rgba(34, 197, 94, 0.35)';
  return 'rgba(239, 68, 68, 0.25)';
});

// Button label
const buttonLabel = computed(() => {
  if (isCompleted.value) return 'Day Complete';
  if (isClockedIn.value) return 'Clock Out';
  return 'Clock In';
});

// Whether the button is disabled
const isButtonDisabled = computed(() => {
  return loading.value || isCompleted.value;
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

let fetchStatusCalled = false;
async function fetchStatus() {
  if (fetchStatusCalled) return;
  fetchStatusCalled = true;
  try {
    const data = await attendanceApi.getTodayCheckin();
    if (data.clock_in && data.clock_out) {
      // Day is complete — both IN and OUT exist
      isCompleted.value = true;
      isClockedIn.value = false;
      clockInTime.value = new Date(data.clock_in);
      elapsed.value = Math.floor(
        (new Date(data.clock_out).getTime() - new Date(data.clock_in).getTime()) / 1000
      );
      stopTimer();
    } else if (data.clock_in && !data.clock_out) {
      isClockedIn.value = true;
      isCompleted.value = false;
      clockInTime.value = new Date(data.clock_in);
      elapsed.value = Math.floor((Date.now() - clockInTime.value.getTime()) / 1000);
      startTimer();
    } else {
      isClockedIn.value = false;
      isCompleted.value = false;
      clockInTime.value = null;
      elapsed.value = 0;
    }
  } catch {
    // Silently fail - will show default state
  }
}

async function handlePunch() {
  if (isCompleted.value) return;
  loading.value = true;
  error.value = '';
  try {
    const result = await attendanceApi.punch();
    if (result.status === 'success') {
      if (result.log_type === 'IN') {
        isClockedIn.value = true;
        isCompleted.value = false;
        clockInTime.value = new Date(result.time);
        elapsed.value = 0;
        startTimer();
      } else {
        isClockedIn.value = false;
        isCompleted.value = true;
        stopTimer();
        // Keep elapsed to show total worked
      }
      emit('punched');
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
        :disabled="isButtonDisabled"
        class="absolute inset-0 m-auto w-[140px] h-[140px] rounded-full
               flex flex-col items-center justify-center gap-1
               transition-all duration-500 focus:outline-none"
        :class="[
          isCompleted
            ? 'bg-emerald-500/15 text-emerald-400 cursor-default'
            : isClockedIn
              ? (shiftComplete
                  ? 'bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25'
                  : 'bg-red-500/10 text-red-400 hover:bg-red-500/20')
              : 'bg-white/[0.05] text-slate-300 hover:bg-white/[0.08] hover:text-white'
        ]"
        :style="(isClockedIn || isCompleted) ? { boxShadow: `0 0 40px ${glowColor}` } : {}"
      >
        <div v-if="loading" class="w-6 h-6 border-2 border-current border-t-transparent rounded-full animate-spin" />
        <template v-else>
          <span class="text-[11px] font-semibold uppercase tracking-wider opacity-70">
            {{ buttonLabel }}
          </span>
          <span v-if="isClockedIn || isCompleted" class="text-2xl font-bold tabular-nums tracking-tight">
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
      <div v-if="isCompleted" class="badge-success mb-2">
        Day Complete
      </div>
      <div v-else-if="shiftComplete && isClockedIn" class="badge-success mb-2">
        Shift Complete
      </div>

      <p v-if="isCompleted && clockInTimeFormatted" class="text-sm text-slate-400">
        Worked <span class="text-white font-medium">{{ timerDisplay }}</span> today
      </p>
      <p v-else-if="isClockedIn && clockInTimeFormatted" class="text-sm text-slate-400">
        Clocked in at <span class="text-white font-medium">{{ clockInTimeFormatted }}</span>
      </p>
      <p v-else class="text-sm text-slate-500">
        Tap to start your shift
      </p>
    </div>

    <p v-if="error" class="mt-3 text-xs text-red-400 text-center max-w-[220px]">{{ error }}</p>
  </div>
</template>
