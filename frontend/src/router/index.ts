import { createRouter, createWebHashHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/attendance',
      name: 'attendance',
      component: () => import('../views/AttendanceView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/leave',
      name: 'leave',
      component: () => import('../views/LeaveView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/payroll',
      name: 'payroll',
      component: () => import('../views/PayrollView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/manager',
      name: 'manager',
      component: () => import('../views/ManagerView.vue'),
      meta: { requiresAuth: true, requiresManager: true },
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('../views/ChangePasswordView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/expense',
      name: 'expense',
      component: () => import('../views/ExpenseView.vue'),
      meta: { requiresAuth: true },
    },
    // Catch-all → dashboard
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
});

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();

  // Wait until auth is initialised
  if (!auth.ready) {
    // auth.init() hasn't finished yet – main.ts ensures it completes
    // before mounting, but just in case:
    next();
    return;
  }

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next({ name: 'login' });
  } else if (to.meta.requiresManager && !auth.isManager) {
    next({ name: 'dashboard' });
  } else if (to.meta.guest && auth.isLoggedIn) {
    next({ name: 'dashboard' });
  } else {
    next();
  }
});

export default router;
