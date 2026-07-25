const API_URL = "http://127.0.0.1:8000/activities";
let tracker = {};
let activeTabId = null;
let activeStartedAt = null;

const DISTRACTING_DOMAINS = new Set([
    "youtube.com", "www.youtube.com", "facebook.com", "www.facebook.com",
    "twitter.com", "x.com", "www.x.com", "instagram.com", "www.instagram.com",
    "tiktok.com", "www.tiktok.com", "reddit.com", "www.reddit.com",
    "netflix.com", "www.netflix.com", "twitch.tv", "www.twitch.tv",
    "discord.com", "www.discord.com"
]);

let domainUsage = {};
let lastNotificationTimes = {};

function logExt(...args) {
    console.log("[FocusGuard BG]", ...args);
}

function now(){
    return Date.now();
}
function iso(time){
    return new Date(time).toISOString();
}
function getDomain(url){
    try{
        return new URL(url).hostname;
    }
    catch{
        return "";
    }
}
function generateSession(){
    return crypto.randomUUID();
}
async function attemptReauth(){
    logExt("attemptReauth start");
    const storage = await chrome.storage.local.get(["saved_username", "saved_password"]);
    if (!storage.saved_username || !storage.saved_password) {
        logExt("attemptReauth no saved credentials");
        return false;
    }
    try {
        const response = await fetch(API_URL.replace(/\/activities$/, "") + "/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: storage.saved_username,
                password: storage.saved_password
            })
        });
        if (!response.ok) {
            logExt("attemptReauth failed", response.status);
            return false;
        }
        const result = await response.json();
        await chrome.storage.local.set({
            token: result.access_token,
            username: storage.saved_username
        });
        logExt("attemptReauth success");
        return true;
    } catch (e) {
        logExt("attemptReauth error", e);
        return false;
    }
}
async function sendActivity(data){
    logExt("sendActivity start", JSON.stringify(data));
    const storage =
        await chrome.storage.local.get(
            ["token"]
        );
    if(!storage.token){
        logExt("JWT missing");
        return;
    }
    const payload = {
        event_type:
            data.event_type,
        tab_id:
            data.tab_id,
        url:
            data.url || "",
        title:
            data.title || "",
        domain:
            getDomain(data.url),
        start_time:
            data.start_time || iso(now()),
        end_time:
            data.end_time || null,
        duration:
            data.duration || 0,
        active_duration:
            data.active_duration || 0,
        session_id:
            data.session_id
    };
    logExt("sendActivity payload", JSON.stringify(payload));
    try{
        const response =
            await fetch(
                API_URL,
                {
                    method:"POST",
                    headers:{
                        "Content-Type":
                            "application/json",
                        "Authorization":
                            `Bearer ${storage.token}`
                    },
                    body:
                        JSON.stringify(payload)
                }
            );
        logExt("sendActivity status", response.status);
        if(response.status === 401){
            logExt("JWT expired - attempting silent re-auth");
            const reauth = await attemptReauth();
            if (reauth) {
                logExt("Silent re-auth succeeded, retrying activity");
                return sendActivity(data);
            }
            logExt("Silent re-auth failed - clearing token");
            await chrome.storage.local.set({ token: null, username: null, saved_username: null, saved_password: null });
            try {
                const tabs = await chrome.tabs.query({});
                tabs.forEach(t => chrome.tabs.sendMessage(t.id, { type: "AUTH_EXPIRED" }).catch(() => {}));
            } catch (e) {}
            return;
        }
        const result =
            await response.json();
        logExt("sendActivity response", JSON.stringify(result));
        await chrome.storage.local.set({ lastSyncAt: Date.now() });
    }
    catch(error){
        logExt("sendActivity error", error);
    }
}
function createTracker(tab){
    return {
        id:
            tab.id,
        session_id:
            generateSession(),
        url:
            tab.url || "",
        title:
            tab.title || "",
        openedAt:
            now(),
        activeSeconds:
            0,
        lastHeartbeat:
            now()
    };
}
chrome.tabs.onCreated.addListener(
async tab=>{
    logExt("onCreated", tab.id, tab.url);
    tracker[tab.id] =
        createTracker(tab);
    await sendActivity({
        event_type:
            "tab_opened",
        tab_id:
            tab.id,
        url:
            tab.url,
        title:
            tab.title,
        start_time:
            iso(
                tracker[tab.id].openedAt
            ),
        session_id:
            tracker[tab.id].session_id
    });
    saveTracker();
});
chrome.tabs.onActivated.addListener(
async info=>{
    logExt("onActivated", info.tabId, "previous activeTabId=" + activeTabId);
    const current =
        now();
    if(
        activeTabId &&
        tracker[activeTabId]
    ){
        const seconds =
            Math.floor(
                (
                    current -
                    activeStartedAt
                ) / 1000
            );
        tracker[activeTabId]
            .activeSeconds += seconds;
        logExt("onActivated previous tab seconds", seconds, "new activeSeconds", tracker[activeTabId].activeSeconds);
    }
    activeTabId =
        info.tabId;
    activeStartedAt =
        current;
    const tab =
        await chrome.tabs.get(
            info.tabId
        );
    if(!tracker[tab.id]){
        tracker[tab.id] =
            createTracker(tab);
    }
    tracker[tab.id].url =
        tab.url || "";
    tracker[tab.id].title =
        tab.title || "";
    await sendActivity({
        event_type:
            "tab_active",
        tab_id:
            tab.id,
        url:
            tab.url,
        title:
            tab.title,
        duration:
            0,
        active_duration:
            tracker[tab.id].activeSeconds,
        session_id:
            tracker[tab.id].session_id
    });
    saveTracker();
});
chrome.tabs.onUpdated.addListener(
async(
    tabId,
    changeInfo,
    tab
)=>{
    logExt("onUpdated", tabId, JSON.stringify(changeInfo));
    if(!tracker[tabId]){
        tracker[tabId] =
            createTracker(tab);
    }
    if(changeInfo.url){
        tracker[tabId].url =
            changeInfo.url;
        await sendActivity({
            event_type:
                "url_changed",
            tab_id:
                tabId,
            url:
                changeInfo.url,
            title:
                tab.title,
            session_id:
                tracker[tabId].session_id
        });
    }
    if(changeInfo.title){
        tracker[tabId].title =
            changeInfo.title;
    }
    saveTracker();
});
setInterval(
async()=>{
    logExt("heartbeat tick activeTabId=" + activeTabId);
    if(
        !activeTabId ||
        !tracker[activeTabId]
    )
        return;
    const tab =
        tracker[activeTabId];
    const current =
        now();
    const seconds =
        Math.floor(
            (
                current -
                tab.lastHeartbeat
            ) / 1000
        );
    if(seconds <=0)
        return;
    tab.lastHeartbeat =
        current;
    tab.activeSeconds += seconds;
    await updateDomainUsage();
    await sendActivity({
        event_type:
            "heartbeat",
        tab_id:
            tab.id,
        url:
            tab.url,
        title:
            tab.title,
        duration:
            seconds,
        active_duration:
            tab.activeSeconds,
        session_id:
            tab.session_id
    });
    saveTracker();
},
10000);
chrome.tabs.onRemoved.addListener(
async tabId=>{
    logExt("onRemoved", tabId);
    const tab =
        tracker[tabId];
    if(!tab)
        return;
    const end =
        now();
    const total =
        Math.floor(
            (
                end -
                tab.openedAt
            ) / 1000
        );
    logExt("onRemoved sending tab_closed", "total=" + total, "activeSeconds=" + tab.activeSeconds);
    await sendActivity({
        event_type:
            "tab_closed",
        tab_id:
            tabId,
        url:
            tab.url,
        title:
            tab.title,
        start_time:
            iso(tab.openedAt),
        end_time:
            iso(end),
        duration:
            total,
        active_duration:
            tab.activeSeconds,
        session_id:
            tab.session_id
    });
    delete tracker[tabId];
    saveTracker();
});
function saveTracker(){
    chrome.storage.local.set({
        tracker
    });
}

async function loadNotificationSettings(){
    const data = await chrome.storage.local.get([
        "notificationThreshold",
        "notificationCooldown",
        "notificationsEnabled"
    ]);
    return {
        enabled: data.notificationsEnabled !== false,
        threshold: data.notificationThreshold || 1200,
        cooldown: data.notificationCooldown || 900
    };
}

async function saveNotificationState(){
    await chrome.storage.local.set({
        lastNotificationTimes
    });
}

async function isDistractionDomain(url){
    if (!url) return false;
    try {
        const hostname = new URL(url).hostname;
        return DISTRACTING_DOMAINS.has(hostname);
    } catch (e) {
        return false;
    }
}

async function checkDistraction(url){
    if (!url) return;
    const settings = await loadNotificationSettings();
    if (!settings.enabled) return;

    let domain = "";
    try {
        domain = new URL(url).hostname;
    } catch (e) {
        return;
    }
    if (!DISTRACTING_DOMAINS.has(domain)) return;

    const now = Date.now();
    const usage = domainUsage[domain] || 0;
    const lastNotified = lastNotificationTimes[domain] || 0;

    if (usage >= settings.threshold && (now - lastNotified) >= settings.cooldown * 1000){
        const minutes = Math.floor(usage / 60);
        const messages = [
            `You have spent ${minutes} minutes on ${domain}. Return to your work.`,
            `FocusGuard detected prolonged distraction on ${domain}. Let's get back to coding.`,
            `${domain} has been calling your name for ${minutes} minutes. Time to refocus!`
        ];
        const message = messages[Math.floor(Math.random() * messages.length)];

        await chrome.notifications.create(`distraction-${domain}-${now}`, {
            type: "basic",
            iconUrl: "icon.png",
            title: "FocusGuard Distraction Alert",
            message: message,
            priority: 2
        });

        lastNotificationTimes[domain] = now;
        saveNotificationState();
    }
}

async function updateDomainUsage(){
    if (!activeTabId || !tracker[activeTabId]) return;
    const tab = tracker[activeTabId];
    const current = now();
    const seconds = Math.floor((current - tab.lastHeartbeat) / 1000);
    if (seconds <= 0) return;

    const domain = getDomain(tab.url);
    if (domain && DISTRACTING_DOMAINS.has(domain)) {
        domainUsage[domain] = (domainUsage[domain] || 0) + seconds;
        checkDistraction(tab.url);
    }
}
async function loadTabs(){
    const saved =
        await chrome.storage.local.get(
            ["tracker"]
        );
    if(saved.tracker){
        tracker =
            saved.tracker;
    }
    const notifState = await chrome.storage.local.get([
        "domainUsage", "lastNotificationTimes"
    ]);
    if (notifState.domainUsage) domainUsage = notifState.domainUsage;
    if (notifState.lastNotificationTimes) lastNotificationTimes = notifState.lastNotificationTimes;

    const tabs =
        await chrome.tabs.query({});
    tabs.forEach(tab=>{
        if(!tracker[tab.id]){
            tracker[tab.id] =
                createTracker(tab);
        }
    });
    saveTracker();
}
chrome.runtime.onStartup.addListener(
    loadTabs
);
chrome.runtime.onInstalled.addListener(
()=>{
    loadTabs();
    console.log(
        "FocusGuard Started"
    );
});