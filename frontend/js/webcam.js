/**
 * Webcam Utility for ExamAegis
 * Handles webcam stream init and frame capture
 */
class WebcamManager {
    constructor(videoElementId, canvasElementId) {
        self.video = document.getElementById(videoElementId);
        self.canvas = document.getElementById(canvasElementId);
        self.stream = null;
    }

    /**
     * Initializes the webcam stream using getUserMedia
     */
    async initialize() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error("Webcam access API (getUserMedia) not supported in this browser.");
        }

        try {
            // Request video only (audio is handled separately via Web Audio API)
            self.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: "user"
                },
                audio: false
            });
            
            // Set stream to HTML Video Element
            self.video.srcObject = self.stream;
            await self.video.play();
            console.log("Webcam initialized and playing.");
            return true;
        } catch (error) {
            console.error("Error accessing webcam:", error);
            throw new Error(`Webcam access error: ${error.message}. Please check permissions.`);
        }
    }

    /**
     * Captures a frame from the playing video, draws it to the hidden canvas,
     * and returns the base64-encoded JPEG image string.
     */
    captureFrame() {
        if (!self.stream || self.video.paused || self.video.ended) {
            return null;
        }

        const width = self.video.videoWidth;
        const height = self.video.videoHeight;
        
        if (width === 0 || height === 0) return null;

        // Sync canvas size with video resolution
        self.canvas.width = width;
        self.canvas.height = height;
        
        const ctx = self.canvas.getContext('2d');
        // Draw video frame to canvas
        ctx.drawImage(self.video, 0, 0, width, height);
        
        // Convert canvas drawing to base64 JPEG
        // Quality 0.7 balances detail and network payload size (approx 20-30KB per frame)
        return self.canvas.toDataURL('image/jpeg', 0.7);
    }

    /**
     * Stops the webcam stream and releases the camera
     */
    stop() {
        if (self.stream) {
            self.stream.getTracks().forEach(track => track.stop());
            self.video.srcObject = null;
            self.stream = null;
            console.log("Webcam stream stopped.");
        }
    }
}
window.WebcamManager = WebcamManager;
