const express = require("express");
const { Client, LocalAuth, MessageMedia } = require("whatsapp-web.js");
const qrcode = require("qrcode");
const http = require("http");
const fs = require("fs");
const path = require("path");

const app = express();
app.use(express.json({ limit: "100mb" }));

let qrCodeData = null;
let clientStatus = "disconnected";
let client = null;
let cachedFooter = "";
let startTime = Date.now();
let stuckCheckInterval = null;

function fetchFooter() {
    http.get("http://127.0.0.1:8000/api/config/footer", (res) => {
        let data = "";
        res.on("data", (chunk) => data += chunk);
        res.on("end", () => {
            try { cachedFooter = JSON.parse(data).texto || ""; } catch { cachedFooter = ""; }
        });
    }).on("error", () => { /* backend not ready yet */ });
}

// Refresh footer every 60s
fetchFooter();
setInterval(fetchFooter, 60000);

function destroyClient() {
    if (client) {
        try { client.removeAllListeners(); } catch (e) { /* ignore */ }
        try { client.destroy(); } catch (e) { /* ignore */ }
        client = null;
    }
}

function cleanStuckSession() {
    const sessionDir = path.join(__dirname, "data", "session");
    if (fs.existsSync(sessionDir)) {
        fs.rmSync(sessionDir, { recursive: true, force: true });
    }
    const cacheDir = path.join(__dirname, ".wwebjs_cache");
    if (fs.existsSync(cacheDir)) {
        fs.rmSync(cacheDir, { recursive: true, force: true });
    }
}

function initClient() {
    destroyClient();
    startTime = Date.now();

    client = new Client({
        authStrategy: new LocalAuth({ dataPath: "./data" }),
        puppeteer: {
            headless: true,
            args: [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        },
    });

    client.on("qr", async (qr) => {
        clientStatus = "awaiting_scan";
        try {
            qrCodeData = await qrcode.toDataURL(qr);
        } catch {
            qrCodeData = qr;
        }
    });

    client.on("ready", () => {
        clientStatus = "connected";
        qrCodeData = null;
    });

    client.on("disconnected", (reason) => {
        clientStatus = "disconnected";
        setTimeout(() => {
            initClient();
            client.initialize();
        }, 5000);
    });

    client.on("auth_failure", () => {
        clientStatus = "auth_failure";
    });

    client.initialize();
}

// Catch detached Frame / getChat errors and force restart
process.on("unhandledRejection", (err) => {
    const msg = String(err);
    if (msg.includes("detached") || msg.includes("Frame") || msg.includes("Session") || msg.includes("getChat") || msg.includes("getState") || msg.includes("No LID")) {
        console.error("Detected crash, restarting client...");
        clientStatus = "disconnected";
        setTimeout(() => {
            initClient();
            if (client) client.initialize();
        }, 2000);
    }
});

app.get("/api/status", async (req, res) => {
    let realStatus = clientStatus;
    if (client && clientStatus === "connected") {
        try {
            await client.getState();
        } catch {
            realStatus = "disconnected";
            clientStatus = "disconnected";
        }
    }
    // If stuck in disconnected for >30s with no QR, clean session and restart
    if (realStatus === "disconnected" && !qrCodeData && (Date.now() - startTime) > 30000) {
        console.log("Session stuck, cleaning and restarting...");
        cleanStuckSession();
        clientStatus = "disconnected";
        qrCodeData = null;
        startTime = Date.now();
        setTimeout(() => {
            initClient();
            if (client) client.initialize();
        }, 1000);
    }
    res.json({ status: realStatus, hasQr: !!qrCodeData });
});

app.get("/api/qr", (req, res) => {
    if (qrCodeData) {
        res.json({ qr: qrCodeData, status: clientStatus });
    } else {
        res.json({ qr: null, status: clientStatus });
    }
});

app.post("/api/send", async (req, res) => {
    const { telefono, mensaje, archivo_nombre, archivo_base64, archivo_mimetype } = req.body;

    if (!telefono) {
        return res.status(400).json({ error: "telefono is required" });
    }

    if (clientStatus !== "connected") {
        return res.status(503).json({ error: "WhatsApp not connected" });
    }

    try {
        if (!client) {
            return res.status(503).json({ error: "WhatsApp client not initialized" });
        }

        // Verify client is actually alive before sending
        try { await client.getState(); } catch (e) {
            clientStatus = "disconnected";
            setTimeout(() => { initClient(); if (client) client.initialize(); }, 1000);
            return res.status(503).json({ error: "WhatsApp reconectando, intenta de nuevo" });
        }

        const rawNumber = telefono.replace(/[^0-9]/g, "");
        const formattedNumber = (() => {
            if (rawNumber.startsWith("0") && rawNumber.length === 11) {
                return "58" + rawNumber.slice(1);
            }
            if (rawNumber.startsWith("0") && rawNumber.length === 10) {
                return "58" + rawNumber.slice(1);
            }
            if (rawNumber.startsWith("58") && rawNumber.length === 12) {
                return rawNumber;
            }
            return rawNumber;
        })();
        const chatId = formattedNumber.includes("@c.us")
            ? formattedNumber
            : `${formattedNumber}@c.us`;

        const footerText = cachedFooter ? `\n\n${cachedFooter}` : "";
        const msgConFooter = (mensaje || "") + footerText;

        if (archivo_base64 && archivo_nombre) {
            const media = new MessageMedia(archivo_mimetype || "application/octet-stream", archivo_base64, archivo_nombre);
            await client.sendMessage(chatId, media, { caption: msgConFooter });
        } else if (mensaje) {
            await client.sendMessage(chatId, msgConFooter);
        }

        res.json({ success: true });
    } catch (error) {
        console.error("Send error:", error.message);
        recentErrors.push({ time: new Date().toISOString(), error: error.message, stack: error.stack?.split("\n")?.slice(0,3)?.join("\n") });
        const msg = error.message || String(error);
        if (msg.includes("getChat") || msg.includes("detached")) {
            clientStatus = "disconnected";
            return res.status(503).json({ error: "WhatsApp reconectando, intenta de nuevo" });
        }
        if (msg.includes("No LID")) {
            clientStatus = "disconnected";
            setTimeout(() => { initClient(); if (client) client.initialize(); }, 2000);
            return res.status(503).json({ error: "WhatsApp reconectando, intenta de nuevo" });
        }
        res.status(500).json({ error: error.message });
    }
});

let recentErrors = [];

app.get("/api/errors", (req, res) => {
    res.json({ errors: recentErrors.slice(-20) });
});

app.post("/api/logout", async (req, res) => {
    try {
        if (client) {
            try { await client.logout(); } catch (e) { /* ignore */ }
            try { client.destroy(); } catch (e) { /* ignore */ }
            client = null;
        }
        // Delete session data so next QR scan is clean
        const sessionDir = path.join(__dirname, "data", "session");
        if (fs.existsSync(sessionDir)) {
            fs.rmSync(sessionDir, { recursive: true, force: true });
        }
        const cacheDir = path.join(__dirname, ".wwebjs_cache");
        if (fs.existsSync(cacheDir)) {
            fs.rmSync(cacheDir, { recursive: true, force: true });
        }
        clientStatus = "disconnected";
        qrCodeData = null;
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3001;
initClient();
app.listen(PORT, () => {
    console.log(`WhatsApp service running on port ${PORT}`);
});
