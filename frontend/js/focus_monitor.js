/**
 * Focus Monitor for ExamAegis
 * Listens for tab switching (visibilitychange) and window focus loss (blur)
 */
class FocusMonitor {
    constructor(socketClient) {
        this.socketClient = socketClient;
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
        this.handleBlur = this.handleBlur.bind(this);
        this.isActive = false;
    }

    /**
     * Start monitoring focus events
     */
    start() {
        if (this.isActive) return;
        this.isActive = true;
        document.addEventListener("visibilitychange", this.handleVisibilityChange);
        window.addEventListener("blur", this.handleBlur);
        console.log("Focus Monitor: Active");
    }

    /**
     * Stop monitoring focus events
     */
    stop() {
        if (!this.isActive) return;
        this.isActive = false;
        document.removeEventListener("visibilitychange", this.handleVisibilityChange);
        window.removeEventListener("blur", this.handleBlur);
        console.log("Focus Monitor: Inactive");
    }

    handleVisibilityChange() {
        if (document.hidden) {
            this.sendViolationEvent("tab_switch");
        }
    }

    handleBlur() {
        this.sendViolationEvent("tab_switch");
    }

    sendViolationEvent(eventName) {
        if (!this.isActive) return;
        console.warn(`Focus Monitor: Triggered event - ${eventName}`);
        
        if (this.socketClient && this.socketClient.socket && this.socketClient.socket.readyState === WebSocket.OPEN) {
            const payload = {
                type: "client_event",
                event: eventName,
                timestamp: new Date().toISOString()
            };
            this.socketClient.socket.send(JSON.stringify(payload));
        }
    }
}
window.FocusMonitor = FocusMonitor;
