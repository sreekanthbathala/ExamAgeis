/**
 * Fullscreen Monitor for ExamAegis
 * Enforces fullscreen mode and flags when exiting fullscreen
 */
class FullscreenMonitor {
    constructor(socketClient) {
        this.socketClient = socketClient;
        this.handleFullscreenChange = this.handleFullscreenChange.bind(this);
        this.isActive = false;
    }

    /**
     * Attempts to request fullscreen mode
     */
    async requestFullscreen() {
        const elem = document.documentElement;
        try {
            if (elem.requestFullscreen) {
                await elem.requestFullscreen();
            } else if (elem.webkitRequestFullscreen) { /* Safari */
                await elem.webkitRequestFullscreen();
            } else if (elem.msRequestFullscreen) { /* IE11 */
                await elem.msRequestFullscreen();
            }
            console.log("Fullscreen Monitor: Entered fullscreen");
        } catch (err) {
            console.error("Fullscreen Monitor: Request failed", err);
        }
    }

    /**
     * Start monitoring fullscreen state changes
     */
    start() {
        if (this.isActive) return;
        this.isActive = true;
        document.addEventListener("fullscreenchange", this.handleFullscreenChange);
        document.addEventListener("webkitfullscreenchange", this.handleFullscreenChange);
        console.log("Fullscreen Monitor: Active");
    }

    /**
     * Stop monitoring fullscreen state changes
     */
    stop() {
        if (!this.isActive) return;
        this.isActive = false;
        document.removeEventListener("fullscreenchange", this.handleFullscreenChange);
        document.removeEventListener("webkitfullscreenchange", this.handleFullscreenChange);
        console.log("Fullscreen Monitor: Inactive");
        
        // Remove overlay if present
        const overlay = document.getElementById("fullscreen-overlay");
        if (overlay) overlay.remove();
    }

    handleFullscreenChange() {
        if (!this.isActive) return;
        const isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement);
        if (!isFullscreen) {
            this.triggerExitViolation();
        }
    }

    triggerExitViolation() {
        console.warn("Fullscreen Monitor: Exited fullscreen");
        
        if (this.socketClient && this.socketClient.socket && this.socketClient.socket.readyState === WebSocket.OPEN) {
            const payload = {
                type: "client_event",
                event: "fullscreen_exit",
                timestamp: new Date().toISOString()
            };
            this.socketClient.socket.send(JSON.stringify(payload));
        }

        this.showFullscreenRequiredOverlay();
    }

    showFullscreenRequiredOverlay() {
        let overlay = document.getElementById("fullscreen-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "fullscreen-overlay";
            overlay.style.position = "fixed";
            overlay.style.top = "0";
            overlay.style.left = "0";
            overlay.style.width = "100vw";
            overlay.style.height = "100vh";
            overlay.style.backgroundColor = "rgba(10, 10, 20, 0.95)";
            overlay.style.color = "white";
            overlay.style.display = "flex";
            overlay.style.flexDirection = "column";
            overlay.style.justifyContent = "center";
            overlay.style.alignItems = "center";
            overlay.style.zIndex = "999999";
            overlay.style.padding = "20px";
            overlay.style.textAlign = "center";

            overlay.innerHTML = `
                <div style="background: #1e2230; padding: 40px; border-radius: 12px; max-width: 500px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                    <h2 style="color: #ff4d6d; margin-bottom: 15px; font-size: 24px;">⚠️ Fullscreen Mode Required</h2>
                    <p style="margin-bottom: 25px; font-size: 15px; color: #ccc; line-height: 1.5;">
                        You have exited fullscreen mode. Exiting fullscreen is flagged as a proctoring violation. 
                        Please click the button below to re-enter fullscreen and continue your exam.
                    </p>
                    <button id="re-enter-fs-btn" class="btn" style="width: auto; padding: 12px 30px; background-color: #17b978; font-size: 16px;">Re-enter Fullscreen</button>
                </div>
            `;
            document.body.appendChild(overlay);

            document.getElementById("re-enter-fs-btn").addEventListener("click", async () => {
                await this.requestFullscreen();
                overlay.remove();
            });
        }
    }
}
window.FullscreenMonitor = FullscreenMonitor;
