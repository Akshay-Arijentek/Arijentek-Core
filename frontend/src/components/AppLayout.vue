<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
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
  Sun,
  Moon,
  Users,
  Lock,
  DollarSign,
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();
const mobileOpen = ref(false);

onMounted(() => {
  theme.init();
});

const navItems = computed(() => {
  const items = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Attendance', path: '/attendance', icon: CalendarCheck },
    { name: 'Leave', path: '/leave', icon: Palmtree },
    { name: 'Expense', path: '/expense', icon: DollarSign },
    { name: 'Payroll', path: '/payroll', icon: Wallet },
  ];
  if (auth.isManager) {
    items.push({ name: 'Team', path: '/manager', icon: Users });
  }
  return items;
});

const currentNav = computed(() =>
  navItems.value.find(n => n.path === route.path)?.name || 'Dashboard'
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
  <div class="min-h-screen flex" :style="{ backgroundColor: 'var(--bg)' }">
    <!-- ====== Desktop Sidebar ====== -->
    <aside class="hidden lg:flex flex-col w-[260px] fixed inset-y-0 left-0 z-30"
      :style="{
        backgroundColor: 'var(--surface)',
        borderRight: '1px solid var(--border-color)',
      }">
      <!-- Logo -->
      <div class="h-16 flex items-center px-6"
        :style="{ borderBottom: '1px solid var(--border-color)' }">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center"
            :style="{ backgroundColor: 'rgba(20,184,166,0.15)' }">
            <span class="font-bold text-sm" :style="{ color: 'var(--accent)' }">A</span>
          </div>
          <span class="text-lg font-semibold tracking-tight" :style="{ color: 'var(--heading-color)' }">Arijentek</span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-6 px-3 space-y-1">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-150"
          :style="{
            backgroundColor: route.path === item.path ? 'rgba(20,184,166,0.1)' : 'transparent',
            color: route.path === item.path ? 'var(--accent)' : 'var(--text-secondary)',
          }"
        >
          <component :is="item.icon" :size="20" :stroke-width="1.8" />
          <span>{{ item.name }}</span>
          <ChevronRight v-if="route.path === item.path" :size="16" class="ml-auto opacity-60" />
        </button>

        <!-- Desk link -->
        <button
          v-if="auth.hasDeskAccess"
          @click="goToDesk"
          class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium mt-4 transition-all duration-150"
          :style="{
            color: 'var(--text-tertiary)',
            border: '1px dashed var(--border-color)',
          }"
        >
          <ExternalLink :size="20" :stroke-width="1.8" />
          <span>Open Desk</span>
        </button>
      </nav>

      <!-- ── Bottom section: theme + user + sign out ── -->
      <div class="px-3 pb-4 space-y-1" :style="{ borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }">
        <!-- Theme toggle -->
        <button
          @click="theme.toggle()"
          class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150"
          :style="{
            backgroundColor: theme.theme === 'light' ? 'rgba(20,184,166,0.08)' : 'var(--glass-bg)',
            color: theme.theme === 'light' ? 'var(--accent)' : 'var(--text-secondary)',
          }"
        >
          <transition name="theme-icon" mode="out-in">
            <Moon v-if="theme.theme === 'dark'" :key="'dark'" :size="18" :stroke-width="1.8" />
            <Sun v-else :key="'light'" :size="18" :stroke-width="1.8" />
          </transition>
          <span>{{ theme.theme === 'dark' ? 'Dark Mode' : 'Light Mode' }}</span>
        </button>

        <!-- User -->
        <div class="flex items-center gap-3 px-4 py-2.5">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            :style="{ backgroundColor: 'rgba(20,184,166,0.15)', color: 'var(--accent)' }">
            {{ initials }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium truncate" :style="{ color: 'var(--heading-color)' }">{{ auth.fullName }}</p>
            <p class="text-xs truncate" :style="{ color: 'var(--text-tertiary)' }">{{ auth.user }}</p>
          </div>
        </div>

        <!-- Change Password -->
        <button
          @click="navigate('/change-password')"
          class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150"
          :style="{ color: 'var(--text-secondary)' }"
          @mouseenter="($event.target as HTMLElement).style.color = 'var(--accent)'; ($event.target as HTMLElement).style.backgroundColor = 'var(--glass-bg)'"
          @mouseleave="($event.target as HTMLElement).style.color = 'var(--text-secondary)'; ($event.target as HTMLElement).style.backgroundColor = 'transparent'"
        >
          <Lock :size="18" :stroke-width="1.8" />
          <span>Change Password</span>
        </button>

        <!-- Sign out -->
        <button
          @click="auth.logout()"
          class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150"
          :style="{ color: 'var(--text-secondary)' }"
          @mouseenter="($event.target as HTMLElement).style.color = 'var(--danger-text)'; ($event.target as HTMLElement).style.backgroundColor = 'var(--danger-bg)'"
          @mouseleave="($event.target as HTMLElement).style.color = 'var(--text-secondary)'; ($event.target as HTMLElement).style.backgroundColor = 'transparent'"
        >
          <LogOut :size="18" :stroke-width="1.8" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>

    <!-- ====== Mobile header ====== -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 h-14 flex items-center justify-between px-4"
      :style="{
        backgroundColor: 'var(--surface)',
        borderBottom: '1px solid var(--border-color)',
        backdropFilter: 'blur(16px)',
      }">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg flex items-center justify-center"
          :style="{ backgroundColor: 'rgba(20,184,166,0.15)' }">
          <span class="font-bold text-xs" :style="{ color: 'var(--accent)' }">A</span>
        </div>
        <span class="font-semibold text-sm" :style="{ color: 'var(--heading-color)' }">{{ currentNav }}</span>
      </div>
      <button @click="mobileOpen = !mobileOpen" :style="{ color: 'var(--text-secondary)' }" class="p-1">
        <Menu v-if="!mobileOpen" :size="22" />
        <X v-else :size="22" />
      </button>
    </div>

    <!-- Mobile slide-out menu -->
    <transition name="modal">
      <div v-if="mobileOpen" class="lg:hidden fixed inset-0 z-40 backdrop-blur-sm"
        :style="{ backgroundColor: 'var(--overlay-bg)' }"
        @click="mobileOpen = false">
        <div class="modal-content absolute right-0 top-0 bottom-0 w-64 p-4 pt-16"
          :style="{
            backgroundColor: 'var(--surface)',
            borderLeft: '1px solid var(--border-color)',
          }"
          @click.stop>
          <nav class="space-y-1 mb-6">
            <button
              v-for="item in navItems"
              :key="item.path"
              @click="navigate(item.path)"
              class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all"
              :style="{
                backgroundColor: route.path === item.path ? 'rgba(20,184,166,0.1)' : 'transparent',
                color: route.path === item.path ? 'var(--accent)' : 'var(--text-secondary)',
              }"
            >
              <component :is="item.icon" :size="20" :stroke-width="1.8" />
              <span>{{ item.name }}</span>
            </button>
            <button v-if="auth.hasDeskAccess" @click="goToDesk"
              class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium mt-2 transition-all"
              :style="{ color: 'var(--text-tertiary)', border: '1px dashed var(--border-color)' }">
              <ExternalLink :size="20" :stroke-width="1.8" />
              <span>Open Desk</span>
            </button>
          </nav>

          <div :style="{ borderTop: '1px solid var(--border-color)' }" class="pt-4 space-y-1">
            <!-- Mobile theme toggle -->
            <button
              @click="theme.toggle()"
              class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
              :style="{ color: 'var(--text-secondary)', backgroundColor: 'var(--glass-bg)' }"
            >
              <Moon v-if="theme.theme === 'dark'" :size="18" />
              <Sun v-else :size="18" />
              <span>{{ theme.theme === 'dark' ? 'Dark Mode' : 'Light Mode' }}</span>
            </button>

            <div class="flex items-center gap-3 px-4 py-2.5">
              <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                :style="{ backgroundColor: 'rgba(20,184,166,0.15)', color: 'var(--accent)' }">
                {{ initials }}
              </div>
              <p class="text-sm font-medium truncate" :style="{ color: 'var(--heading-color)' }">{{ auth.fullName }}</p>
            </div>

            <button @click="navigate('/change-password')"
              class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all"
              :style="{ color: 'var(--text-secondary)' }">
              <Lock :size="18" />
              <span>Change Password</span>
            </button>

            <button @click="auth.logout()"
              class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all"
              :style="{ color: 'var(--text-secondary)' }">
              <LogOut :size="18" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Mobile bottom nav -->
    <div class="lg:hidden fixed bottom-0 left-0 right-0 z-30 h-16 flex items-center justify-around px-2"
      :style="{
        backgroundColor: 'var(--surface)',
        borderTop: '1px solid var(--border-color)',
        backdropFilter: 'blur(16px)',
      }">
      <button
        v-for="item in navItems"
        :key="item.path"
        @click="navigate(item.path)"
        class="flex flex-col items-center gap-1 py-1 px-3 rounded-xl transition-all"
        :style="{ color: route.path === item.path ? 'var(--accent)' : 'var(--text-tertiary)' }"
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
