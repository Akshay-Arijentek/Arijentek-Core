import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export const useThemeStore = defineStore('theme', () => {
    // Theme state: 'dark' or 'light'
    const theme = ref<'dark' | 'light'>('dark');

    // Initialize theme from localStorage or system preference
    function init() {
        const stored = localStorage.getItem('arijentek-theme');
        if (stored === 'light' || stored === 'dark') {
            theme.value = stored;
        } else {
            // Default to dark mode
            theme.value = 'dark';
        }
        applyTheme();
    }

    // Apply theme to document
    function applyTheme() {
        const root = document.documentElement;
        if (theme.value === 'light') {
            root.classList.add('light-mode');
            root.classList.remove('dark-mode');
        } else {
            root.classList.add('dark-mode');
            root.classList.remove('light-mode');
        }
    }

    // Toggle between dark and light
    function toggle() {
        theme.value = theme.value === 'dark' ? 'light' : 'dark';
        localStorage.setItem('arijentek-theme', theme.value);
        applyTheme();
    }

    // Set specific theme
    function setTheme(newTheme: 'dark' | 'light') {
        theme.value = newTheme;
        localStorage.setItem('arijentek-theme', newTheme);
        applyTheme();
    }

    // Watch for theme changes
    watch(theme, () => {
        applyTheme();
    });

    return {
        theme,
        init,
        toggle,
        setTheme,
    };
});
