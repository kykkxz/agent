export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

export const escape = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    "\"": "&quot;",
})[character]);

export const number = (value) => Number(value ?? 0).toLocaleString();
export const percent = (value, digits = 1) => value == null ? "-" : `${(Number(value) * 100).toFixed(digits)}%`;
export const date = (value) => value ? new Date(value).toLocaleString() : "-";

export function notice(message, isError = false) {
    const target = $("#toast");
    target.textContent = message;
    target.className = `toast ${isError ? "error" : "success"}`;
    window.setTimeout(() => {
        if (target.textContent === message) target.textContent = "";
    }, 4500);
}

export function pageHeader(title, eyebrow, action = "") {
    return `<div class="page-head"><div><p class="eyebrow">${escape(eyebrow)}</p><h1>${escape(title)}</h1></div>${action}</div>`;
}

export function panel(title, body, actions = "") {
    return `<section class="panel"><div class="panel-head"><h2>${escape(title)}</h2>${actions}</div>${body}</section>`;
}

export function table(headers, rows) {
    if (!rows.length) return '<p class="empty">暂无记录</p>';
    return `<div class="table-wrap"><table><thead><tr>${headers.map((header) => `<th>${escape(header)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}

export function chartImage(title, data) {
    return `<figure class="chart-panel"><figcaption>${escape(title)}</figcaption><img class="chart" src="data:image/png;base64,${data.image_base64}" alt="${escape(title)}"></figure>`;
}
