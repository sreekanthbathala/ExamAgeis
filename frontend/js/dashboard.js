/**
 * Dashboard Logic for ExamAegis Admin Panel
 * Fetches sessions, renders violation timelines, aggregates stats, and handles exports
 */

document.addEventListener("DOMContentLoaded", () => {
    const adminToken = localStorage.getItem("admin_token");
    if (!adminToken) {
        // Not authenticated as admin, show login view or redirect
        showAdminLogin();
        return;
    }
    
    // Authenticated, initialize dashboard
    initDashboard();
});

function showAdminLogin() {
    // Inject HTML login container into layout
    document.getElementById("dashboard-app").innerHTML = `
        <div class="login-card">
            <h2>ExamAegis Admin Login</h2>
            <div id="login-error" style="color:red; margin-bottom:10px; display:none;"></div>
            <form id="admin-login-form">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="admin-username" class="form-control" required placeholder="admin">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="admin-password" class="form-control" required placeholder="admin123">
                </div>
                <button type="submit" class="btn">Access Dashboard</button>
            </form>
        </div>
    `;

    document.getElementById("admin-login-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("admin-username").value;
        const password = document.getElementById("admin-password").value;
        const errorDiv = document.getElementById("login-error");

        try {
            const response = await fetch("/api/auth/admin-login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem("admin_token", data.access_token);
                localStorage.setItem("admin_name", data.name);
                window.location.reload();
            } else {
                const errorData = await response.json();
                errorDiv.innerText = errorData.detail || "Authentication failed.";
                errorDiv.style.display = "block";
            }
        } catch (err) {
            console.error("Login request failed:", err);
            errorDiv.innerText = "Connection failed. Is the server running?";
            errorDiv.style.display = "block";
        }
    });
}

async function initDashboard() {
    const adminToken = localStorage.getItem("admin_token");
    const adminName = localStorage.getItem("admin_name") || "Administrator";

    // Setup main dashboard frame
    document.getElementById("dashboard-app").innerHTML = `
        <div class="flex-space" style="margin-bottom: 20px;">
            <div>
                <h1>🛡️ ExamAegis Proctor Control Center</h1>
                <p>Welcome, <span id="admin-name-span"></span></p>
            </div>
            <button id="logout-btn" class="btn btn-secondary" style="width: auto; padding: 8px 16px;">Logout</button>
        </div>
        
        <div class="dashboard-layout">
            <!-- Sidebar: Sessions List -->
            <div class="sidebar">
                <h3>Exam Sessions</h3>
                <div id="sessions-container">
                    <div class="text-center">Loading sessions...</div>
                </div>
            </div>
            
            <!-- Main Content Area -->
            <div class="main-content">
                <!-- Stats Summary -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div id="stat-high" class="value">0</div>
                        <div class="label">High Severity Incidents</div>
                    </div>
                    <div class="stat-card">
                        <div id="stat-medium" class="value" style="color: #ff9f43;">0</div>
                        <div class="label">Medium Severity Incidents</div>
                    </div>
                    <div class="stat-card">
                        <div id="stat-total" class="value" style="color: #2196f3;">0</div>
                        <div class="label">Total Violations</div>
                    </div>
                </div>
                
                <!-- Detailed Timeline -->
                <div class="timeline-card">
                    <div class="flex-space">
                        <h2 id="active-session-title">Select an active session to inspect</h2>
                        <button id="export-btn" class="btn" style="width: auto; padding: 6px 12px; display: none;">📥 Export Log (JSON)</button>
                    </div>
                    <p id="student-meta-desc" style="color:#666; margin-top:5px; font-size:14px;"></p>
                    
                    <div id="timeline-container" class="timeline">
                        <div class="text-center" style="color:#888; padding: 40px 0;">
                            Proctoring timeline and details will render here.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById("admin-name-span").innerText = adminName;
    document.getElementById("logout-btn").addEventListener("click", () => {
        localStorage.clear();
        window.location.reload();
    });

    await loadSessionsList(adminToken);
}

async function loadSessionsList(token) {
    const container = document.getElementById("sessions-container");
    try {
        const response = await fetch("/api/report/sessions", {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.reload();
            return;
        }

        if (response.ok) {
            const sessions = await response.json();
            
            if (sessions.length === 0) {
                container.innerHTML = `<div class="text-center" style="padding:20px; color:#888;">No proctored sessions found in database.</div>`;
                return;
            }

            container.innerHTML = "";
            sessions.forEach(sess => {
                const item = document.createElement("div");
                item.className = "session-item";
                if (sess.status === "active") {
                    item.style.borderRight = "5px solid #17b978";
                }
                
                const startTimeStr = new Date(sess.start_time).toLocaleString();
                
                item.innerHTML = `
                    <div class="name">${sess.student_name} (${sess.student_roll})</div>
                    <div class="meta">Exam ID: <strong>${sess.exam_id}</strong></div>
                    <div class="meta">Status: <strong>${sess.status.toUpperCase()}</strong></div>
                    <div class="meta" style="font-size:11px; margin-top:2px;">Started: ${startTimeStr}</div>
                `;
                
                item.addEventListener("click", () => {
                    // Highlight active selection
                    document.querySelectorAll(".session-item").forEach(el => el.classList.remove("active"));
                    item.classList.add("active");
                    
                    // Load details
                    inspectSession(sess.session_id, sess.student_name, sess.student_roll, sess.exam_id);
                });
                
                container.appendChild(item);
            });

        } else {
            container.innerHTML = `<div class="text-center" style="color:red;">Error loading sessions list.</div>`;
        }
    } catch (err) {
        console.error("Error loading sessions:", err);
        container.innerHTML = `<div class="text-center" style="color:red;">Failed to connect to server.</div>`;
    }
}

async function inspectSession(sessionId, studentName, rollNumber, examId) {
    const token = localStorage.getItem("admin_token");
    
    // Update Title Info
    document.getElementById("active-session-title").innerText = `Violation Log: ${studentName}`;
    document.getElementById("student-meta-desc").innerText = `Roll Number: ${rollNumber} | Exam ID: ${examId} | Session ID: ${sessionId}`;
    
    // Show Export Button
    const exportBtn = document.getElementById("export-btn");
    exportBtn.style.display = "block";
    
    // Replace export button listener
    const newExportBtn = exportBtn.cloneNode(true);
    exportBtn.parentNode.replaceChild(newExportBtn, exportBtn);
    newExportBtn.addEventListener("click", () => downloadLogs(sessionId, token));

    const timelineContainer = document.getElementById("timeline-container");
    timelineContainer.innerHTML = `<div class="text-center" style="padding: 40px 0;">Loading logs...</div>`;

    try {
        // Fetch logs
        const logsResponse = await fetch(`/api/report/violations/${sessionId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        
        if (!logsResponse.ok) throw new Error("Could not fetch violations");
        const logs = await logsResponse.json();

        // Calculate counts
        let highCount = 0;
        let mediumCount = 0;
        
        logs.forEach(l => {
            if (l.severity === "high") highCount++;
            if (l.severity === "medium") mediumCount++;
        });

        document.getElementById("stat-high").innerText = highCount;
        document.getElementById("stat-medium").innerText = mediumCount;
        document.getElementById("stat-total").innerText = logs.length;

        // Render Timeline
        if (logs.length === 0) {
            timelineContainer.innerHTML = `
                <div class="text-center" style="color:#17b978; padding: 40px 0; font-weight:600;">
                    ✅ No violations recorded. Candidate is following all rules.
                </div>
            `;
            return;
        }

        timelineContainer.innerHTML = "";
        logs.forEach(log => {
            const timeStr = new Date(log.timestamp).toLocaleTimeString();
            const item = document.createElement("div");
            item.className = `timeline-item severity-${log.severity}`;
            
            // Format nice label
            const displayLabel = log.violation_type.replace("_", " ").toUpperCase();
            
            item.innerHTML = `
                <div class="timeline-time">${timeStr} <span class="severity-tag severity-${log.severity}">${log.severity}</span></div>
                <div class="timeline-content">
                    <div class="timeline-title">${displayLabel}</div>
                    <div style="font-size: 13px; color:#555;">${log.details.message || 'Details not recorded.'}</div>
                </div>
            `;
            
            timelineContainer.appendChild(item);
        });

    } catch (err) {
        console.error("Error inspecting session:", err);
        timelineContainer.innerHTML = `<div class="text-center" style="color:red; padding: 40px 0;">Error retrieving timeline details.</div>`;
    }
}

async function downloadLogs(sessionId, token) {
    try {
        const response = await fetch(`/api/report/export/${sessionId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `examaegis_session_${sessionId}_violations.json`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else {
            alert("Failed to export logs. Ensure you have permissions.");
        }
    } catch (err) {
        console.error("Export request failed:", err);
        alert("Server communication error while exporting logs.");
    }
}
