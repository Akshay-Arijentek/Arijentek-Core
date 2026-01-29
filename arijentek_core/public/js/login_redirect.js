// Employee Portal Login Redirect Fix
// This script patches Frappe's login handler to properly redirect employees

(function () {
    // Wait for Frappe to be ready
    if (typeof frappe === 'undefined') {
        document.addEventListener('DOMContentLoaded', initEmployeeRedirect);
    } else {
        initEmployeeRedirect();
    }

    function initEmployeeRedirect() {
        // Patch the login success handler
        if (window.login && window.login.login_handlers) {
            var originalHandler = window.login.login_handlers[200];

            window.login.login_handlers[200] = function (data) {
                // If redirect_to is set and message is "No App", use redirect_to
                if (data.message == "No App" && data.redirect_to) {
                    window.login.set_status("Success", 'green');
                    document.body.innerHTML = document.body.innerHTML.includes('splash')
                        ? document.body.innerHTML
                        : '<div style="text-align:center;padding:50px;">Redirecting...</div>';
                    window.location.href = data.redirect_to;
                    return;  // Prevent further navigation
                }
                // Otherwise use original handler
                return originalHandler(data);
            };
        }
    }
})();
