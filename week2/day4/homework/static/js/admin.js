const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const loginForm = document.querySelector("#loginForm");
if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const body = Object.fromEntries(new FormData(loginForm).entries());
        const response = await fetch("/admin/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body),
        });
        const result = await response.json();
        document.querySelector("#loginToast").textContent = result.msg;
        if (response.ok) {
            location.reload();
        }
    });
}

async function loadNews() {
    const list = document.querySelector("#newsList");
    if (!list) {
        return;
    }

    const response = await fetch("/api/news");
    const result = await response.json();
    list.innerHTML = result.data.map((item) => `
        <div class="admin-row">
            <div>
                <span class="tag">${escapeHtml(item.category)}</span>
                <h3>${escapeHtml(item.title)}</h3>
                <div class="meta">${escapeHtml(item.published_at)} · #${escapeHtml(item.id)}</div>
            </div>
            <button class="danger" data-id="${escapeHtml(item.id)}">删除</button>
        </div>
    `).join("");

    list.querySelectorAll("button[data-id]").forEach((button) => {
        button.addEventListener("click", async () => {
            if (!confirm("确定删除这条新闻吗？")) {
                return;
            }

            await fetch(`/admin/news/${button.dataset.id}`, {method: "DELETE"});
            await loadNews();
        });
    });
}

const newsForm = document.querySelector("#newsForm");
if (newsForm) {
    newsForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const body = Object.fromEntries(new FormData(newsForm).entries());
        const response = await fetch("/admin/news", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body),
        });
        const result = await response.json();
        document.querySelector("#newsToast").textContent = result.msg;
        if (response.ok) {
            newsForm.reset();
            document.querySelector("#category").value = "公司公告";
            await loadNews();
        }
    });
    loadNews();
}
