<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import {
  LayoutDashboard,
  CalendarCheck,
  Palmtree,
  Wallet,
  LogOut,
  Menu,
  X,
  ChevronRight,
  ExternalLink,
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const mobileOpen = ref(false);

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Attendance', path: '/attendance', icon: CalendarCheck },
  { name: 'Leave', path: '/leave', icon: Palmtree },
  { name: 'Payroll', path: '/payroll', icon: Wallet },
];

const currentNav = computed(() =>
  navItems.find(n => n.path === route.path)?.name || 'Dashboard'
);

function navigate(path: string) {
  router.push(path);
  mobileOpen.value = false;
}

function goToDesk() {
  window.location.href = '/app';
}

const initials = computed(() => {
  const name = auth.fullName || 'U';
  const parts = name.split(' ');
  return parts.length > 1
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
});
</script>

<template>
  <div class="min-h-screen flex">
    <!-- ====== Desktop Sidebar ====== -->
    <aside class="hidden lg:flex flex-col w-[260px] fixed inset-y-0 left-0 z-30
                   bg-surface border-r border-white/[0.06]">
      <!-- Logo -->
      <div class="h-16 flex items-center px-6 border-b border-white/[0.06]">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
            <span class="text-accent font-bold text-sm">A</span>
          </div>
          <span class="text-lg font-semibold text-white tracking-tight">Arijentek</span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-6 px-3 space-y-1">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200"
          :class="route.path === item.path
            ? 'bg-accent/10 text-accent'
            : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'"
        >
          <component :is="item.icon" :size="20" :stroke-width="1.8" />
          <span>{{ item.name }}</span>
          <ChevronRight v-if="route.path === item.path" :size="16" class="ml-auto opacity-60" />
        </button>

        <!-- Desk link for system users -->
        <button
          v-if="auth.hasDeskAccess"
          @click="goToDesk"
          class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                 text-slate-500 hover:text-white hover:bg-white/[0.04] transition-all duration-200 mt-4
                 border border-dashed border-white/[0.06]"
        >
          <ExternalLink :size="20" :stroke-width="1.8" />
          <span>Open Desk</span>
        </button>
      </nav>

      <!-- User section -->
      <div class="p-4 border-t border-white/[0.06]">
        <div class="flex items-center gap-3 px-2 mb-3">
          <div class="w-9 h-9 rounded-full bg-accent/20 flex items-center justify-center
                      text-accent text-xs font-bold shrink-0">
            {{ initials }}
          </div>
          <div class="min-w-0">
            <p class="text-sm font-medium text-white truncate">{{ auth.fullName }}</p>
            <p class="text-xs text-slate-500 truncate">{{ auth.user }}</p>
          </div>
        </div>
        <button
          @click="auth.logout()"
          class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium
                 text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
        >
          <LogOut :size="18" :stroke-width="1.8" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>

    <!-- ====== Mobile header ====== -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 h-14 bg-surface/90 backdrop-blur-xl
                border-b border-white/[0.06] flex items-center justify-between px-4">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg bg-accent/20 flex items-center justify-center">
          <span class="text-accent font-bold text-xs">A</span>
        </div>
        <span class="font-semibold text-white text-sm">{{ currentNav }}</span>
      </div>
      <button @click="mobileOpen = !mobileOpen" class="text-slate-400 p-1">
        <Menu v-if="!mobileOpen" :size="22" />
        <X v-else :size="22" />
      </button>
    </div>

    <!-- Mobile slide-out menu -->
    <transition name="modal">
      <div v-if="mobileOpen" class="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
           @click="mobileOpen = false">
        <div class="modal-content absolute right-0 top-0 bottom-0 w-64 bg-surface border-l border-white/[0.06] p-4 pt-16"
             @click.stop>
          <nav class="space-y-1 mb-6">
            <button
              v-for="item in navItems"
              :key="item.path"
              @click="navigate(item.path)"
              class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all"
              :class="route.path === item.path
                ? 'bg-accent/10 text-accent'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'"
            >
              <component :is="item.icon" :size="20" :stroke-width="1.8" />
              <span>{{ item.name }}</span>
            </button>
            <button v-if="auth.hasDeskAccess" @click="goToDesk"
              class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                     text-slate-500 hover:text-white hover:bg-white/[0.04] transition-all mt-2
                     border border-dashed border-white/[0.06]">
              <ExternalLink :size="20" :stroke-width="1.8" />
              <span>Open Desk</span>
            </button>
          </nav>
          <div class="border-t border-white/[0.06] pt-4">
            <div class="flex items-center gap-3 px-2 mb-3">
              <div class="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center
                          text-accent text-xs font-bold">{{ initials }}</div>
              <p class="text-sm font-medium text-white truncate">{{ auth.fullName }}</p>
            </div>
            <button @click="auth.logout()"
              class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm
                     text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all">
              <LogOut :size="18" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Mobile bottom nav -->
    <div class="lg:hidden fixed bottom-0 left-0 right-0 z-30 h-16 bg-surface/90 backdrop-blur-xl
                border-t border-white/[0.06] flex items-center justify-around px-2">
      <button
        v-for="item in navItems"
        :key="item.path"
        @click="navigate(item.path)"
        class="flex flex-col items-center gap-1 py-1 px-3 rounded-xl transition-all"
        :class="route.path === item.path ? 'text-accent' : 'text-slate-500'"
      >
        <component :is="item.icon" :size="20" :stroke-width="1.8" />
        <span class="text-[10px] font-medium">{{ item.name }}</span>
      </button>
    </div>

    <!-- ====== Main content ====== -->
    <main class="flex-1 lg:ml-[260px] pt-14 pb-20 lg:pt-0 lg:pb-0 min-h-screen">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
        <slot />
      </div>
    </main>
  </div>
</template>
