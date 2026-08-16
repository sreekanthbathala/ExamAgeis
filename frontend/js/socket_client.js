/**
 * WebSocket and Audio Client for ExamAegis
 * Manages WebSocket communication, records audio chunks, and triggers warnings.
 */
class ProctorSocketClient {
    constructor(sessionId, token, webcamManager, alertElementId, statusElementId, metricsElementId) {
        self.sessionId = sessionId;
        self.token = token;
        self.webcam = webcamManager;
        self.alertBox = document.getElementById(alertElementId);
        self.statusBadge = document.getElementById(statusElementId);
        self.metricsBox = document.getElementById(metricsElementId);
        
        self.socket = null;
        self.audioStream = null;
        self.mediaRecorder = null;
        self.frameInterval = null;
    }

    /**
     * Connects to the backend WebSocket
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/api/monitor/ws/${self.sessionId}?token=${self.token}`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);
        self.socket = new WebSocket(wsUrl);

        // Tell websocket to process binary frames as ArrayBuffer or Blob
        self.socket.binaryType = "blob";

        self.socket.onopen = () => {
            console.log("WebSocket connection established.");
            self.updateStatus(true);
            
            // Start video streaming (every 1.5 seconds)
            self.startFrameStreaming(1500);
            
            // Start audio recording and streaming
            self.startAudioStreaming(1000);
        };

        self.socket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === "proctor_result") {
                    self.handleProctorResult(message);
                } else if (message.type === "error") {
                    alert(`Proctoring Error: ${message.message}`);
                    self.disconnect();
                }
            } catch (err) {
                console.error("Error parsing socket message:", err);
            }
        };

        self.socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            self.updateStatus(false);
        };

        self.socket.onclose = (event) => {
            console.log("WebSocket connection closed.", event);
            self.updateStatus(false);
            self.stopStreaming();
        };
    }

    /**
     * Periodically captures frames and sends them over WebSocket
     */
    startFrameStreaming(intervalMs) {
        if (self.frameInterval) clearInterval(self.frameInterval);
        
        self.frameInterval = setInterval(() => {
            if (self.socket && self.socket.readyState === WebSocket.OPEN) {
                const frameData = self.webcam.captureFrame();
                if (frameData) {
                    const message = {
                        type: "frame",
                        data: frameData
                    };
                    self.socket.send(JSON.stringify(message));
                }
            }
        }, intervalMs);
    }

    /**
     * Accesses microphone and streams audio chunks as raw binary bytes
     */
    async startAudioStreaming(timesliceMs) {
        try {
            self.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            console.log("Microphone access granted.");

            // Use MediaRecorder to slice audio recordings
            self.mediaRecorder = new MediaRecorder(self.audioStream);
            
            self.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0 && self.socket && self.socket.readyState === WebSocket.OPEN) {
                    // Send binary audio blob directly over the socket
                    self.socket.send(event.data);
                }
            };

            // Start recording, generating chunks of audio every `timesliceMs`
            self.mediaRecorder.start(timesliceMs);
            console.log(`Audio recording started with ${timesliceMs}ms timeslices.`);
        } catch (err) {
            console.error("Failed to access microphone for proctoring:", err);
            self.showWarning("Microphone access is required for this exam! Please enable permissions.");
        }
    }

    /**
     * Renders warnings and metrics on the webpage in real-time
     */
    handleProctorResult(result) {
        const alerts = result.alerts || [];
        const metrics = result.metrics || {};

        // 1. Show / Hide Alert warnings
        if (alerts.length > 0) {
            // Find highest severity alert to show
            const highestAlert = alerts.reduce((prev, current) => {
                const priorities = { "low": 1, "medium": 2, "high": 3 };
                return (priorities[current.severity] > priorities[prev.severity]) ? current : prev;
            }, alerts[0]);

            self.showWarning(highestAlert.message);
        } else {
            self.hideWarning();
        }

        // 2. Render diagnostic metrics for feedback
        if (self.metricsBox) {
            self.metricsBox.innerHTML = `
                <div><strong>Faces Counted:</strong> ${metrics.face_count}</div>
                <div><strong>Gaze Deviation:</strong> ${metrics.gaze_ratio} (Normal: 0.35 - 0.65)</div>
                <div><strong>Eye Closure (EAR):</strong> ${metrics.ear} (Closed < 0.20)</div>
                <div><strong>Head Pose:</strong> Yaw: ${metrics.head_pose.yaw}°, Pitch: ${metrics.head_pose.pitch}°</div>
                <div><strong>Mouth Opening (MAR):</strong> ${metrics.mar} (Talking > 0.50)</div>
                <div><strong>Objects:</strong> ${metrics.objects_detected.length > 0 ? metrics.objects_detected.join(", ") : 'None'}</div>
            `;
        }
    }

    showWarning(msg) {
        if (self.alertBox) {
            self.alertBox.innerText = `⚠️ WARN: ${msg}`;
            self.alertBox.style.display = "block";
        }
    }

    hideWarning() {
        if (self.alertBox) {
            self.alertBox.style.display = "none";
        }
    }

    updateStatus(isConnected) {
        if (self.statusBadge) {
            if (isConnected) {
                self.statusBadge.innerText = "PROCTORING ACTIVE";
                self.statusBadge.className = "status-badge status-connected";
            } else {
                self.statusBadge.innerText = "DISCONNECTED";
                self.statusBadge.className = "status-badge status-disconnected";
            }
        }
    }

    stopStreaming() {
        if (self.frameInterval) {
            clearInterval(self.frameInterval);
            self.frameInterval = null;
        }
        if (self.mediaRecorder && self.mediaRecorder.state !== "inactive") {
            self.mediaRecorder.stop();
        }
        if (self.audioStream) {
            self.audioStream.getTracks().forEach(track => track.stop());
            self.audioStream = null;
        }
        self.mediaRecorder = null;
        console.log("Proctoring streams stopped.");
    }

    disconnect() {
        self.stopStreaming();
        if (self.socket) {
            self.socket.close();
            self.socket = null;
        }
        self.updateStatus(false);
    }
}
window.ProctorSocketClient = ProctorSocketClient;
