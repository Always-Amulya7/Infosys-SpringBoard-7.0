document.addEventListener("DOMContentLoaded", () => {

    const API_URL = "http://127.0.0.1:8000";

    const loginDiv = document.getElementById("login");
    const dashboardDiv = document.getElementById("dashboard");

    const username = document.getElementById("username");
    const password = document.getElementById("password");

    const loginBtn = document.getElementById("loginBtn");
    const logoutBtn = document.getElementById("logoutBtn");

    const message = document.getElementById("message");
    const website = document.getElementById("website");
    const focusTime = document.getElementById("focusTime");
    const currentUser = document.getElementById("currentUser");

    const notificationsEnabled = document.getElementById("notificationsEnabled");
    const notificationThreshold = document.getElementById("notificationThreshold");
    const notificationCooldown = document.getElementById("notificationCooldown");

    const saveNotifBtn = document.getElementById("saveNotifBtn");
    const notifMessage = document.getElementById("notifMessage");

    async function checkLogin() {
        const data = await chrome.storage.local.get([
            "token",
            "username"
        ]);

        if (data.token) {
            loginDiv.style.display = "none";
            dashboardDiv.style.display = "block";
            currentUser.innerText = data.username || "User";
            loadCurrentTab();
            loadTracker();
        }
    }

    loginBtn?.addEventListener("click", async () => {

        message.innerText = "";

        if (
            username.value.trim() === "" ||
            password.value.trim() === ""
        ) {
            message.innerText = "Enter username & password";
            return;
        }

        try {

            const response = await fetch(API_URL + "/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username.value,
                    password: password.value
                })
            });

            const result = await response.json();

            if (!response.ok) {
                message.innerText = result.detail || "Login Failed";
                return;
            }

            await chrome.storage.local.set({
                token: result.access_token,
                username: username.value
            });

            const remember = document.getElementById("rememberMe")?.checked;
            if (remember) {
                await chrome.storage.local.set({
                    saved_username: username.value,
                    saved_password: password.value
                });
            }

            loginDiv.style.display = "none";
            dashboardDiv.style.display = "block";
            currentUser.innerText = username.value;

            loadCurrentTab();
            loadTracker();
            loadNotificationSettings();

        } catch (err) {

            console.error(err);
            message.innerText = "Server not reachable";

        }

    });

    logoutBtn?.addEventListener("click", async () => {

        const storage = await chrome.storage.local.get("token");

        if (storage.token) {

            try {
                await fetch(API_URL + "/logout", {
                    method: "POST",
                    headers: {
                        "Authorization": "Bearer " + storage.token
                    }
                });
            } catch (e) {
                console.log(e);
            }

        }

        await chrome.storage.local.clear();
        location.reload();

    });

    async function loadCurrentTab() {

        const tabs = await chrome.tabs.query({
            active: true,
            currentWindow: true
        });

        if (tabs.length && website) {
            website.innerText = tabs[0].url || "";
        }

    }

    async function loadTracker() {

        const data = await chrome.storage.local.get("tracker");

        if (!data.tracker) {
            if (focusTime) focusTime.innerText = "0 sec";
            return;
        }

        let total = 0;

        Object.values(data.tracker).forEach(tab => {
            total += tab.activeSeconds || 0;
        });

        if (focusTime) {
            focusTime.innerText = total + " sec";
        }

    }

    async function loadNotificationSettings() {
        const data = await chrome.storage.local.get([
            "notificationThreshold",
            "notificationCooldown",
            "notificationsEnabled"
        ]);

        if (notificationThreshold) {
            notificationThreshold.value =
                data.notificationThreshold !== undefined
                    ? Math.floor(data.notificationThreshold / 60)
                    : 20;
        }

        if (notificationCooldown) {
            notificationCooldown.value =
                data.notificationCooldown !== undefined
                    ? Math.floor(data.notificationCooldown / 60)
                    : 15;
        }

        if (notificationsEnabled) {
            notificationsEnabled.checked =
                data.notificationsEnabled !== false;
        }

    }

    async function saveNotificationSettings() {

        const threshold =
            parseInt(notificationThreshold?.value, 10) || 20;

        const cooldown =
            parseInt(notificationCooldown?.value, 10) || 15;

        await chrome.storage.local.set({

            notificationsEnabled:
                notificationsEnabled?.checked ?? true,

            notificationThreshold:
                threshold * 60,

            notificationCooldown:
                cooldown * 60

        });

        if (notifMessage) {

            notifMessage.style.display = "block";
            notifMessage.innerText = "Settings Saved";

            setTimeout(() => {
                notifMessage.style.display = "none";
            }, 2000);

        }

    }

    saveNotifBtn?.addEventListener(
        "click",
        saveNotificationSettings
    );

    checkLogin();
    loadNotificationSettings();

    setInterval(() => {
        checkLogin();
    }, 3000);

    chrome.runtime.onMessage.addListener((msg) => {
        if (msg && msg.type === "AUTH_EXPIRED") {
            loginDiv.style.display = "block";
            dashboardDiv.style.display = "none";
        }
    });

    setInterval(() => {
        loadCurrentTab();
        loadTracker();
    }, 1000);

});