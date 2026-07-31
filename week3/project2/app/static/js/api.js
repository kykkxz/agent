const baseUrl = "/api/v1";
const cacheLifetime = 30_000;
const persistentCacheLifetime = 5 * 60_000;
const persistentCachePrefix = "insurance-insight-cache:";
const responseCache = new Map();
const pendingGets = new Map();
let cacheGeneration = 0;

const isPersistentPath = (path) => path.startsWith("/data/visualization/");
const persistentCacheKey = (path) => `${persistentCachePrefix}${path}`;

function readPersistentCache(path) {
    if (!isPersistentPath(path)) return null;

    try {
        const cached = JSON.parse(sessionStorage.getItem(persistentCacheKey(path)) || "null");
        if (!cached || Date.now() - cached.createdAt >= persistentCacheLifetime) {
            sessionStorage.removeItem(persistentCacheKey(path));
            return null;
        }
        return cached;
    } catch {
        return null;
    }
}

function writePersistentCache(path, cached) {
    if (!isPersistentPath(path)) return;

    try {
        sessionStorage.setItem(persistentCacheKey(path), JSON.stringify(cached));
    } catch {
        return;
    }
}

function clearPersistentCache() {
    try {
        for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
            const key = sessionStorage.key(index);
            if (key?.startsWith(persistentCachePrefix)) sessionStorage.removeItem(key);
        }
    } catch {
        return;
    }
}

const request = async (path, options = {}) => {
    const headers = new Headers(options.headers || {});
    const token = localStorage.getItem("insurance_token");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");

    const response = await fetch(`${baseUrl}${path}`, { ...options, headers });
    const payload = await response.json().catch(() => ({ code: 5000, message: "服务器响应无效" }));
    if (!response.ok || payload.code !== 0) {
        if (response.status === 401) localStorage.removeItem("insurance_token");
        throw new Error(payload.message || "请求失败");
    }
    return payload.data;
};

const download = async (path) => {
    const headers = new Headers();
    const token = localStorage.getItem("insurance_token");
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const response = await fetch(`${baseUrl}${path}`, { headers });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({ message: "下载失败" }));
        throw new Error(payload.message || "下载失败");
    }

    const filename = response.headers.get("Content-Disposition")?.match(/filename="?([^";]+)"?/i)?.[1] || "model.joblib";
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
};

async function get(path) {
    const cached = responseCache.get(path);
    if (cached && Date.now() - cached.createdAt < cacheLifetime) return cached.data;

    const persistentCached = readPersistentCache(path);
    if (persistentCached) {
        responseCache.set(path, persistentCached);
        return persistentCached.data;
    }

    if (pendingGets.has(path)) return pendingGets.get(path);

    const generation = cacheGeneration;
    const pending = request(path)
        .then((data) => {
            if (generation === cacheGeneration) {
                const cachedResponse = { data, createdAt: Date.now() };
                responseCache.set(path, cachedResponse);
                writePersistentCache(path, cachedResponse);
            }
            return data;
        })
        .finally(() => {
            if (pendingGets.get(path) === pending) pendingGets.delete(path);
        });
    pendingGets.set(path, pending);
    return pending;
}

async function mutate(path, options) {
    const data = await request(path, options);
    cacheGeneration += 1;
    responseCache.clear();
    pendingGets.clear();
    clearPersistentCache();
    return data;
}

export const api = {
    get,
    post: (path, data) => mutate(path, { method: "POST", body: data instanceof FormData ? data : JSON.stringify(data || {}) }),
    put: (path, data) => mutate(path, { method: "PUT", body: JSON.stringify(data) }),
    patch: (path, data) => mutate(path, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (path, data) => mutate(path, { method: "DELETE", body: data ? JSON.stringify(data) : undefined }),
    download,
};
