export { };

declare global {
    interface Window {
        csrf_token: string;
        frappe: {
            session: {
                user: string;
                user_fullname: string;
            };
            // Add other frappe globals here as needed
        };
    }
}
