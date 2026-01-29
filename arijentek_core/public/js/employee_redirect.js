// Employee Portal Redirect Script
// Redirects employees (Website Users) to the employee portal if they try to access desk

frappe.ready(function () {
    // Only run this check on desk pages
    if (window.location.pathname.startsWith('/desk') || window.location.pathname.startsWith('/app')) {
        // Check if user is an employee
        frappe.call({
            method: 'arijentek_core.api.check_employee_redirect',
            async: false,
            callback: function (r) {
                if (r.message && r.message.redirect) {
                    window.location.href = r.message.redirect_to;
                }
            }
        });
    }
});
