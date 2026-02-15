import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import { attendanceApi } from '../services/api';

interface PendingPunch {
    id: string; // unique ID for deduping
    timestamp: string; // ISO string
    type: 'IN' | 'OUT'; // informational
}

export const useOfflineStore = defineStore('offline', () => {
    const pendingPunches = ref<PendingPunch[]>([]);
    const isSyncing = ref(false);
    const lastSyncError = ref('');

    // Load from localStorage on init
    const stored = localStorage.getItem('arijentek_offline_punches');
    if (stored) {
        try {
            pendingPunches.value = JSON.parse(stored);
        } catch (e) {
            console.error('Failed to parse offline punches', e);
        }
    }

    // Persist to localStorage whenever changed
    watch(pendingPunches, (val) => {
        localStorage.setItem('arijentek_offline_punches', JSON.stringify(val));
    }, { deep: true });

    // Add a punch to the queue
    function addPunch() {
        pendingPunches.value.push({
            id: crypto.randomUUID(),
            timestamp: new Date().toISOString(),
            type: 'IN' // Defaulting to IN for type safety, though resolved by server
        });
    }

    // Sync pending punches
    async function sync() {
        if (pendingPunches.value.length === 0) return;
        if (isSyncing.value) return;

        isSyncing.value = true;
        lastSyncError.value = '';

        const queue = [...pendingPunches.value];
        // Sort by time to ensure correct order
        queue.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

        try {
            for (const punch of queue) {
                console.log(`Syncing punch from ${punch.timestamp}...`);
                const result = await attendanceApi.punch(punch.timestamp);

                if (result.status === 'success' || (result.error && result.error.includes('already clocked'))) {
                    // Success or benign error -> Remove from queue
                    pendingPunches.value = pendingPunches.value.filter(p => p.id !== punch.id);
                } else {
                    // Real error -> Stop syncing and keep in queue to retry later
                    console.error('Sync failed for punch', punch, result.error);
                    lastSyncError.value = result.error || 'Sync failed';
                    break;
                }
            }
        } catch (e: any) {
            lastSyncError.value = e.message || 'Network error during sync';
        } finally {
            isSyncing.value = false;
        }
    }

    return {
        pendingPunches,
        isSyncing,
        lastSyncError,
        addPunch,
        sync
    };
});
