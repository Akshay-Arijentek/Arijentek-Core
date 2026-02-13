/**
 * Employee Portal – Desk Integration
 *
 * Adds a floating Portal icon button (bottom-right, to the right of Edit)
 * so System Users can return to the Employee Portal from the desk.
 *
 * Also adds to user dropdown and sidebar.
 * Loaded via app_include_js in hooks.py.
 */
(function () {
	'use strict';

	var PORTAL_URL = '/employee-portal';

	/* ── Theme styles: white in dark mode, black in light mode ── */
	function injectPortalStyles() {
		if (document.getElementById('ep-fab-styles')) return;
		var style = document.createElement('style');
		style.id = 'ep-fab-styles';
		style.textContent =
			'#ep-fab{background:#374151;color:#f3f4f6;border:1px solid rgba(255,255,255,0.08);}' +
			'#ep-fab:hover{background:#4b5563;}' +
			'[data-theme="dark"] #ep-fab,.dark #ep-fab,html.dark #ep-fab,' +
			'[data-theme="dark"] body #ep-fab{background:#e5e7eb;color:#1f2937;border-color:rgba(0,0,0,0.1);}' +
			'[data-theme="dark"] #ep-fab:hover,.dark #ep-fab:hover,html.dark #ep-fab:hover{background:#f3f4f6;}';
		document.head.appendChild(style);
	}

	/* ── 1. Floating icon button: right of Edit, aligned, theme-aware ── */
	function addFloatingButton() {
		if (document.getElementById('ep-fab')) return;

		injectPortalStyles();

		var fab = document.createElement('a');
		fab.id = 'ep-fab';
		fab.href = PORTAL_URL;
		fab.title = 'Open Employee Portal';

		fab.innerHTML =
			'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" ' +
			'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
			'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>' +
			'<circle cx="9" cy="7" r="4"/>' +
			'<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>' +
			'<path d="M16 3.13a4 4 0 0 1 0 7.75"/>' +
			'</svg>';

		fab.style.cssText = [
			'position:fixed',
			'bottom:24px',
			'right:24px',
			'z-index:1020',
			'display:flex',
			'align-items:center',
			'justify-content:center',
			'width:44px',
			'height:44px',
			'border-radius:12px',
			'text-decoration:none',
			'box-shadow:0 2px 8px rgba(0,0,0,0.15)',
			'transition:transform .2s, box-shadow .2s, background .2s, color .2s',
		].join(';');

		fab.addEventListener('mouseenter', function () {
			this.style.transform = 'translateY(-2px)';
			this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
		});
		fab.addEventListener('mouseleave', function () {
			this.style.transform = 'translateY(0)';
			this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
		});

		document.body.appendChild(fab);

		/* Align vertically with Frappe's .desktop-edit */
		setTimeout(function alignWithEdit() {
			var edit = document.querySelector('.desktop-edit');
			if (edit) {
				var rect = edit.getBoundingClientRect();
				fab.style.bottom = (window.innerHeight - rect.bottom) + 'px';
			}
		}, 500);
	}

	/* ── 2. User dropdown menu ────────────────────────────────────── */
	function addToUserMenu() {
		var menu = document.getElementById('toolbar-user');
		if (!menu || menu.querySelector('#ep-dropdown-link')) return;

		var link = document.createElement('a');
		link.id = 'ep-dropdown-link';
		link.className = 'dropdown-item';
		link.href = PORTAL_URL;
		link.innerHTML = '<span style="display:inline-flex;align-items:center;gap:8px;">' +
			'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
			'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>' +
			'<circle cx="9" cy="7" r="4"/>' +
			'<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>' +
			'<path d="M16 3.13a4 4 0 0 1 0 7.75"/>' +
			'</svg>Employee Portal</span>';

		menu.insertBefore(link, menu.firstChild);
		menu.insertBefore(document.createElement('div'), link.nextSibling).className = 'dropdown-divider';
	}

	/* ── 3. Sidebar items ─────────────────────────────────────────── */
	function addToSidebar() {
		var sidebar = document.querySelector('.body-sidebar-top .sidebar-items');
		if (!sidebar || sidebar.querySelector('#ep-sidebar-link')) return;

		var item = document.createElement('div');
		item.className = 'standard-sidebar-item';
		item.id = 'ep-sidebar-link';
		item.innerHTML = '<a class="item-anchor" href="' + PORTAL_URL + '" style="display:flex;align-items:center;gap:8px;">' +
			'<span class="sidebar-item-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
			'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>' +
			'<circle cx="9" cy="7" r="4"/>' +
			'<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>' +
			'<path d="M16 3.13a4 4 0 0 1 0 7.75"/>' +
			'</svg></span>' +
			'<span class="sidebar-item-label">Employee Portal</span></a>';

		sidebar.appendChild(item);
	}

	function setup() {
		addFloatingButton();
		addToUserMenu();
		addToSidebar();
	}

	function trySetup(attempts) {
		if (attempts <= 0) return;
		addFloatingButton();
		var sidebar = document.querySelector('.body-sidebar-top .sidebar-items');
		var menu = document.getElementById('toolbar-user');
		if (sidebar || menu) {
			addToUserMenu();
			addToSidebar();
		}
		if (attempts > 1) setTimeout(function () { trySetup(attempts - 1); }, 400);
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', function () { trySetup(10); });
	} else {
		trySetup(10);
	}

	if (typeof $ !== 'undefined') {
		$(document).on('page-change', function () { setTimeout(setup, 200); });
	}
})();
