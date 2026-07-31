import { api } from "./api.js";
import { $, $$, chartImage, date, escape, notice, number, pageHeader, panel, percent, table } from "./ui.js";

(() => {
    const state = {
        user: null,
        route: "overview",
        customerFilters: {},
        customerPage: 1,
        recordPage: 1,
        renderId: 0,
    };
    const routeNames = {
        overview: "数据概览",
        customers: "客户数据",
        insights: "数据洞察",
        prediction: "概率预测",
        email: "营销邮件",
        records: "邮件记录",
        prompt: "Prompt 模板",
        models: "模型中心",
        metrics: "模型分析",
        modelFiles: "模型资产",
        logs: "操作日志",
    };
    const navItems = [
        ["overview", "数据概览"],
        ["customers", "客户数据"],
        ["insights", "数据洞察"],
        ["prediction", "概率预测"],
        ["email", "营销邮件"],
        ["records", "邮件记录"],
        ["prompt", "Prompt 模板"],
        ["models", "模型中心", "admin"],
        ["metrics", "模型分析", "admin"],
        ["modelFiles", "模型资产", "admin"],
        ["logs", "操作日志", "admin"],
    ];
    const adminRoutes = new Set(navItems.filter((item) => item[2] === "admin").map(([route]) => route));
    const page = (title, action = "") => pageHeader(title, routeNames[state.route] || "", action);
    const isCurrentRender = (renderId) => state.renderId === renderId;

    function bindRoutes(root = document) {
        $$("[data-route]", root).forEach((button) => {
            button.addEventListener("click", () => {
                location.hash = button.dataset.route;
            });
        });
    }

    function renderNavigation() {
        $("#navigation").innerHTML = navItems
            .filter(([, , role]) => !role || state.user.role === role)
            .map(([route, label]) => `<button class="nav-item ${route === state.route ? "active" : ""}" data-route="${route}"><span>${label}</span></button>`)
            .join("");
        bindRoutes($("#navigation"));
    }

    function shell() {
        $("#login-shell").hidden = true;
        $("#app-shell").hidden = false;
        $("#current-user").textContent = `${state.user.username} / ${state.user.role}`;
        renderNavigation();
    }

    async function login(username, password, register = false) {
        const data = await api.post(`/auth/${register ? "register" : "login"}`, { username, password });
        localStorage.setItem("insurance_token", data.access_token);
        state.user = data.user;
        shell();
        history.replaceState(null, "", "#overview");
        await render();
    }

    function pager(data, prefix) {
        if (data.pages <= 1) return "";
        return `<div class="pager"><span>第 ${data.page} / ${data.pages} 页，共 ${number(data.total)} 条</span><div class="actions"><button class="secondary" type="button" id="${prefix}-prev" ${data.page <= 1 ? "disabled" : ""}>上一页</button><button class="secondary" type="button" id="${prefix}-next" ${data.page >= data.pages ? "disabled" : ""}>下一页</button></div></div>`;
    }

    async function overview(renderId) {
        const view = $("#view");
        view.innerHTML = page("客户资产") + '<p class="empty">正在读取数据...</p>';
        const data = await api.get("/data/statistics");
        if (!isCurrentRender(renderId)) return;
        const male = data.gender_distribution.Male || 0;
        const female = data.gender_distribution.Female || 0;
        const positive = data.response_distribution["1"] || 0;
        view.innerHTML = page("客户资产", '<button class="primary" data-route="customers">导入数据</button>')
            + stats([
                ["客户总数", number(data.total), "已入库"],
                ["潜在转化", number(positive), "Response = 1"],
                ["男性客户", number(male), "Gender = Male"],
                ["女性客户", number(female), "Gender = Female"],
            ])
            + `<div class="grid split">${panel("年龄区间", `<strong class="large-number">${data.age_stats.min ?? "-"} <span class="muted">至</span> ${data.age_stats.max ?? "-"}</strong><p class="muted">平均 ${data.age_stats.avg?.toFixed(1) ?? "-"} 岁</p>`)}${panel("响应构成", `<div class="progress"><span style="width:${data.total ? positive / data.total * 100 : 0}%"></span></div><p class="muted">正样本占比 ${data.total ? (positive / data.total * 100).toFixed(1) : 0}%</p>`)}</div>`;
        bindRoutes(view);
    }

    function stats(cards) {
        return `<div class="grid stats">${cards.map(([label, value, detail]) => `<div class="stat"><small>${label}</small><strong>${value}</strong><span class="muted">${detail}</span></div>`).join("")}</div>`;
    }

    async function customers(renderId) {
        const view = $("#view");
        view.innerHTML = page("客户数据")
            + panel("导入客户数据", '<form id="upload-form" class="upload-drop"><strong>选择 Excel 文件</strong><input type="file" accept=".xlsx,.xls" name="file" required><button class="primary" type="submit">覆盖导入</button><p id="upload-status" class="upload-status" role="status" aria-live="polite"></p></form>')
            + panel("客户列表", '<form id="customer-filter" class="inline-form"><label>性别<select name="gender"><option value="">全部</option><option>Male</option><option>Female</option></select></label><label>年龄下限<input name="age_min" type="number" min="0"></label><label>年龄上限<input name="age_max" type="number" min="0"></label><label>既往投保<select name="previously_insured"><option value="">全部</option><option value="1">已投保</option><option value="0">未投保</option></select></label><label>客户 ID<input name="keyword" inputmode="numeric"></label><button class="secondary">筛选</button></form><div id="customer-table" class="empty">正在读取...</div><div id="customer-pagination"></div>');
        $("#upload-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const button = form.querySelector("button[type=submit]");
            const fileInput = form.elements.file;
            const uploadStatus = $("#upload-status");
            const formData = new FormData(form);
            button.disabled = true;
            fileInput.disabled = true;
            button.textContent = "正在导入...";
            uploadStatus.textContent = "正在上传并写入客户数据，请勿离开此页面。";
            form.setAttribute("aria-busy", "true");
            try {
                const result = await api.post("/data/upload", formData);
                notice(`已导入 ${number(result.imported_count)} 条数据`);
                state.customerFilters = {};
                await loadCustomers(1, renderId);
            } catch (error) {
                notice(error.message, true);
            } finally {
                form.removeAttribute("aria-busy");
                button.disabled = false;
                fileInput.disabled = false;
                button.textContent = "覆盖导入";
                uploadStatus.textContent = "";
            }
        });
        $("#customer-filter").addEventListener("submit", async (event) => {
            event.preventDefault();
            state.customerFilters = Object.fromEntries([...new FormData(event.currentTarget)].filter(([, value]) => value !== ""));
            await loadCustomers(1);
        });
        await loadCustomers(state.customerPage, renderId);
    }

    async function loadCustomers(pageNumber = state.customerPage, renderId = state.renderId) {
        state.customerPage = pageNumber;
        const params = new URLSearchParams({ ...state.customerFilters, page: String(pageNumber), per_page: "20" });
        const data = await api.get(`/data/customers?${params}`);
        if (!isCurrentRender(renderId)) return;
        $("#customer-table").innerHTML = table(
            ["ID", "性别", "年龄", "既往投保", "车龄", "年保费", "响应", "预测概率"],
            data.items.map((row) => `<tr><td>${row.id}</td><td>${row.gender}</td><td>${row.age}</td><td>${row.previously_insured ? "是" : "否"}</td><td>${escape(row.vehicle_age)}</td><td>${number(row.annual_premium)}</td><td>${row.response}</td><td>${percent(row.predicted_prob)}</td></tr>`),
        );
        $("#customer-pagination").innerHTML = pager(data, "customer");
        $("#customer-prev")?.addEventListener("click", () => loadCustomers(data.page - 1));
        $("#customer-next")?.addEventListener("click", () => loadCustomers(data.page + 1));
    }

    async function insights(renderId) {
        const view = $("#view");
        view.innerHTML = page("数据洞察") + '<p class="empty">正在生成质量报告与图表...</p>';
        const chartTypes = [
            ["response_distribution", "响应分布"],
            ["gender_response", "性别与响应"],
            ["age_distribution", "年龄分布"],
            ["premium_distribution", "年保费分布"],
        ];
        const [quality, ...charts] = await Promise.all([
            api.get("/data/quality"),
            ...chartTypes.map(([type]) => api.get(`/data/visualization/${type}`)),
        ]);
        if (!isCurrentRender(renderId)) return;
        const missing = Object.entries(quality.missing_values).filter(([, value]) => value > 0);
        view.innerHTML = page("数据洞察")
            + stats([
                ["数据行数", number(quality.total_rows), "客户记录"],
                ["字段数量", number(quality.total_cols), "分析字段"],
                ["缺失单元", number(missing.reduce((sum, [, value]) => sum + value, 0)), "需关注"],
                ["重复记录", number(quality.duplicates), "全行重复"],
            ])
            + panel("字段质量", table(["字段", "类型", "缺失值"], Object.entries(quality.dtypes).map(([field, type]) => `<tr><td>${escape(field)}</td><td>${escape(type)}</td><td>${quality.missing_values[field]}</td></tr>`)))
            + panel("探索性分析", `<div class="chart-grid">${charts.map((chart, index) => chartImage(chartTypes[index][1], chart)).join("")}</div>`);
    }

    async function models(renderId) {
        const view = $("#view");
        view.innerHTML = page("模型中心")
            + panel("训练实验", '<form id="train-form"><div class="form-grid"><fieldset class="check-group"><legend>训练算法</legend><label><input type="checkbox" name="models" value="logistic_regression" checked> Logistic Regression</label><label><input type="checkbox" name="models" value="xgboost" checked> XGBoost</label><label><input type="checkbox" name="models" value="random_forest" checked> Random Forest</label></fieldset><label>测试集比例<input name="test_size" type="number" min="0.1" max="0.4" step="0.05" value="0.2"></label><label>随机种子<input name="random_state" type="number" value="42"></label></div><div class="actions"><button class="primary" type="submit">开始训练</button><span id="train-result" class="muted"></span></div></form>')
            + panel("实验记录", '<div id="experiments" class="empty">正在读取...</div>');
        $("#train-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const selected = form.getAll("models");
            if (!selected.length) {
                notice("请至少选择一个算法", true);
                return;
            }
            const button = event.currentTarget.querySelector("button[type=submit]");
            button.disabled = true;
            try {
                const result = await api.post("/model/train", {
                    models: selected.length === 3 ? null : selected,
                    test_size: Number(form.get("test_size")),
                    random_state: Number(form.get("random_state")),
                });
                $("#train-result").textContent = `最佳模型：${result.best_model}`;
                notice("模型训练完成");
                await loadExperiments(renderId);
            } catch (error) {
                notice(error.message, true);
            } finally {
                button.disabled = false;
            }
        });
        await loadExperiments(renderId);
    }

    async function loadExperiments(renderId = state.renderId) {
        const data = await api.get("/model/experiments?per_page=50");
        if (!isCurrentRender(renderId)) return;
        $("#experiments").innerHTML = table(
            ["模型", "ROC-AUC", "Precision", "Recall", "F1", "状态", "时间"],
            data.items.map((row) => `<tr><td>${escape(row.model_name)}</td><td>${row.roc_auc.toFixed(4)}</td><td>${row.precision.toFixed(4)}</td><td>${row.recall.toFixed(4)}</td><td>${row.f1_score.toFixed(4)}</td><td>${row.is_best ? '<span class="badge">最佳</span>' : "-"}</td><td>${date(row.created_at)}</td></tr>`),
        );
    }

    async function metrics(renderId) {
        const view = $("#view");
        view.innerHTML = page("模型分析") + '<p class="empty">正在读取实验记录...</p>';
        const experiments = (await api.get("/model/experiments?per_page=100")).items;
        if (!isCurrentRender(renderId)) return;
        const models = [...new Set(experiments.map((item) => item.model_name))];
        if (!models.length) {
            view.innerHTML = page("模型分析") + panel("模型评估", '<p class="empty">请先在模型中心完成训练。</p>');
            return;
        }
        view.innerHTML = page("模型分析")
            + panel("评估图表", `<form id="metrics-form" class="inline-form"><label>图表<select name="chart_type"><option value="metrics_comparison">模型对比</option><option value="roc_curve">ROC 曲线</option><option value="confusion_matrix">混淆矩阵</option><option value="feature_importance">特征重要性</option></select></label><label>模型<select name="model">${models.map((name) => `<option value="${escape(name)}">${escape(name)}</option>`).join("")}</select></label><button class="secondary">更新图表</button></form><div id="metrics-chart" class="empty">正在生成图表...</div>`);
        const form = $("#metrics-form");
        const loadChart = async () => {
            const data = new FormData(form);
            const chartType = data.get("chart_type");
            const params = chartType === "metrics_comparison" ? "" : `?model=${encodeURIComponent(data.get("model"))}`;
            $("#metrics-chart").innerHTML = '<p class="empty">正在生成图表...</p>';
            try {
                const chart = await api.get(`/model/visualization/${chartType}${params}`);
                if (!isCurrentRender(renderId)) return;
                $("#metrics-chart").innerHTML = chartImage("模型评估", chart);
            } catch (error) {
                if (!isCurrentRender(renderId)) return;
                $("#metrics-chart").innerHTML = `<p class="error">${escape(error.message)}</p>`;
            }
        };
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            loadChart();
        });
        form.elements.chart_type.addEventListener("change", () => {
            form.elements.model.disabled = form.elements.chart_type.value === "metrics_comparison";
        });
        form.elements.model.disabled = true;
        await loadChart();
    }

    async function modelFiles(renderId) {
        const view = $("#view");
        view.innerHTML = page("模型资产") + '<p class="empty">正在读取可用模型...</p>';
        const experiments = (await api.get("/model/experiments?per_page=100")).items;
        if (!isCurrentRender(renderId)) return;
        const models = [...new Set(experiments.map((item) => item.model_name))];
        view.innerHTML = page("模型资产")
            + panel("导出模型", models.length
                ? `<form id="export-form" class="inline-form"><label>模型<select name="model_name">${models.map((name) => `<option value="${escape(name)}">${escape(name)}</option>`).join("")}</select></label><button class="secondary">下载 .joblib</button></form>`
                : '<p class="empty">暂无可导出的训练模型。</p>')
            + panel("导入模型", '<form id="import-form" class="inline-form"><label>模型文件<input type="file" name="file" accept=".joblib" required></label><button class="primary">导入模型</button></form><p id="import-result" class="muted"></p>');
        $("#export-form")?.addEventListener("submit", async (event) => {
            event.preventDefault();
            const modelName = new FormData(event.currentTarget).get("model_name");
            try {
                await api.download(`/model/export/${encodeURIComponent(modelName)}`);
                notice("模型下载已开始");
            } catch (error) {
                notice(error.message, true);
            }
        });
        $("#import-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            try {
                const result = await api.post("/model/import", new FormData(event.currentTarget));
                $("#import-result").textContent = `已导入 ${result.model_name}`;
                notice("模型导入完成");
            } catch (error) {
                notice(error.message, true);
            }
        });
    }

    async function prediction(renderId) {
        const view = $("#view");
        view.innerHTML = page("概率预测") + '<p class="empty">正在读取最佳模型...</p>';
        const [best, experiments] = await Promise.all([
            api.get("/model/best"),
            api.get("/model/experiments?per_page=100"),
        ]);
        if (!isCurrentRender(renderId)) return;
        const models = [...new Set(experiments.items.map((item) => item.model_name))];
        const options = models.map((name) => `<option value="${escape(name)}" ${name === best.model_name ? "selected" : ""}>${escape(name)}</option>`).join("");
        view.innerHTML = page("概率预测")
            + panel("当前最佳模型", `<strong class="large-number">${escape(best.model_name)}</strong><p class="muted">ROC-AUC ${best.roc_auc.toFixed(4)}</p>`)
            + panel("全量概率回写", `<form id="predict-form" class="inline-form"><label>预测模型<select name="model_name"><option value="">使用最佳模型</option>${options}</select></label><button class="primary">回写全部客户概率</button></form><p id="predict-result" class="muted"></p>`)
            + panel("上传数据预测", '<form id="predict-upload-form" class="inline-form"><label>Excel 文件<input type="file" name="file" accept=".xlsx,.xls" required></label><label>预测模型<select name="model"><option value="">使用最佳模型</option>' + options + '</select></label><button class="secondary">生成预测结果</button></form><div id="upload-predictions"></div>')
            + panel("高潜客户", '<form id="targets-form" class="inline-form"><label>分位阈值<input name="percentile" type="number" min="0.01" max="0.99" step="0.01" value="0.9"></label><button class="secondary">筛选高潜客户</button></form><div id="targets" class="empty">设置阈值后查看客户。</div>');
        $("#predict-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const button = event.currentTarget.querySelector("button");
            button.disabled = true;
            try {
                const result = await api.post("/model/predict", { model_name: new FormData(event.currentTarget).get("model_name") || null });
                $("#predict-result").textContent = `已使用 ${result.model_name} 回写 ${number(result.predicted_count)} 条客户概率。`;
                notice("全量预测完成");
            } catch (error) {
                notice(error.message, true);
            } finally {
                button.disabled = false;
            }
        });
        $("#predict-upload-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            try {
                const result = await api.post("/model/predict_upload", new FormData(event.currentTarget));
                $("#upload-predictions").innerHTML = stats([
                    ["预测客户", number(result.total_count), result.model_name],
                    ["最低概率", percent(result.statistics.min, 2), ""],
                    ["平均概率", percent(result.statistics.avg, 2), ""],
                    ["最高概率", percent(result.statistics.max, 2), ""],
                ]) + table(["客户 ID", "预测概率"], result.predictions.slice(0, 20).map((item) => `<tr><td>${item.id}</td><td>${percent(item.predicted_prob, 2)}</td></tr>`));
            } catch (error) {
                notice(error.message, true);
            }
        });
        $("#targets-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            await loadTargets(Number(new FormData(event.currentTarget).get("percentile")), renderId);
        });
    }

    async function loadTargets(percentileValue = 0.9, renderId = state.renderId) {
        $("#targets").innerHTML = '<p class="empty">正在筛选高潜客户...</p>';
        try {
            const data = await api.get(`/email/targets?percentile=${percentileValue}&per_page=20`);
            if (!isCurrentRender(renderId)) return;
            $("#targets").innerHTML = `<p class="muted">分位阈值 ${percent(data.threshold, 2)}，命中 ${number(data.total)} 位客户。</p>`
                + table(["客户", "性别", "年龄", "年保费", "预测概率"], data.customers.map((row) => `<tr><td>${row.id}</td><td>${row.gender}</td><td>${row.age}</td><td>${number(row.annual_premium)}</td><td>${percent(row.predicted_prob, 2)}</td></tr>`));
        } catch (error) {
            if (!isCurrentRender(renderId)) return;
            $("#targets").innerHTML = `<p class="error">${escape(error.message)}</p>`;
        }
    }

    async function email(renderId) {
        const view = $("#view");
        view.innerHTML = page("营销邮件")
            + panel("高潜客户", '<div id="email-targets" class="empty">正在读取高潜客户...</div>')
            + panel("生成邮件", '<form id="email-form" class="inline-form"><label>自动生成数量<input name="limit" type="number" min="1" max="100" value="5"></label><button class="primary">生成高潜邮件</button></form><p class="muted">勾选客户后，会优先为勾选客户生成邮件。</p><div id="email-result"></div>');
        $("#email-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const selected = $$("[name=email-target]:checked").map((input) => Number(input.value));
            const button = event.currentTarget.querySelector("button");
            button.disabled = true;
            try {
                const result = await api.post("/email/generate", selected.length ? { customer_ids: selected } : { limit: Number(new FormData(event.currentTarget).get("limit")) });
                $("#email-result").innerHTML = `<p class="${result.failed_count ? "error" : "success"}">成功 ${result.generated_count} / 失败 ${result.failed_count}</p>`
                    + table(["客户", "状态", "主题"], result.records.map((row) => `<tr><td>${row.customer_id}</td><td><span class="badge ${row.status === "failed" ? "failed" : ""}">${row.status}</span></td><td>${escape(row.subject)}</td></tr>`));
                notice("邮件生成请求已完成");
            } catch (error) {
                notice(error.message, true);
            } finally {
                button.disabled = false;
            }
        });
        await loadEmailTargets(renderId);
    }

    async function loadEmailTargets(renderId = state.renderId) {
        try {
            const data = await api.get("/email/targets?per_page=20");
            if (!isCurrentRender(renderId)) return;
            $("#email-targets").innerHTML = `<p class="muted">默认取预测概率前 10%，当前阈值 ${percent(data.threshold, 2)}。</p>`
                + table(["选择", "客户", "年龄", "年保费", "预测概率"], data.customers.map((row) => `<tr><td><input type="checkbox" name="email-target" value="${row.id}" aria-label="选择客户 ${row.id}"></td><td>${row.id}</td><td>${row.age}</td><td>${number(row.annual_premium)}</td><td>${percent(row.predicted_prob, 2)}</td></tr>`));
        } catch (error) {
            if (!isCurrentRender(renderId)) return;
            $("#email-targets").innerHTML = `<p class="error">${escape(error.message)}</p>`;
        }
    }

    async function records(renderId) {
        const view = $("#view");
        view.innerHTML = page("邮件记录", '<button id="batch-delete" class="danger" type="button">删除选中</button>')
            + panel("历史记录", '<form id="record-filter" class="inline-form"><label>状态<select name="status"><option value="">全部</option><option value="generated">generated</option><option value="sent">sent</option><option value="failed">failed</option></select></label><button class="secondary">筛选</button></form><div id="records-table" class="empty">正在读取...</div><div id="records-pagination"></div>');
        $("#record-filter").addEventListener("submit", async (event) => {
            event.preventDefault();
            state.recordStatus = new FormData(event.currentTarget).get("status");
            await loadRecords(1);
        });
        $("#batch-delete").addEventListener("click", batchDeleteRecords);
        await loadRecords(state.recordPage, renderId);
    }

    async function loadRecords(pageNumber = state.recordPage, renderId = state.renderId) {
        state.recordPage = pageNumber;
        const params = new URLSearchParams({ page: String(pageNumber), per_page: "30" });
        if (state.recordStatus) params.set("status", state.recordStatus);
        const data = await api.get(`/email/records?${params}`);
        if (!isCurrentRender(renderId)) return;
        $("#records-table").innerHTML = table(
            ["选择", "客户", "创建人", "主题", "状态", "时间", "操作"],
            data.items.map((row) => `<tr><td><input type="checkbox" name="record-select" value="${row.id}" aria-label="选择邮件 ${row.id}"></td><td>${row.customer_id}</td><td>${escape(row.created_by_username || "-")}</td><td>${escape(row.subject)}</td><td><span class="badge ${row.status === "failed" ? "failed" : ""}">${escape(row.status)}</span></td><td>${date(row.created_at)}</td><td><button class="text-button" type="button" data-view-record="${row.id}">查看与编辑</button></td></tr>`),
        );
        $$("[data-view-record]").forEach((button) => button.addEventListener("click", () => showRecord(Number(button.dataset.viewRecord))));
        $("#records-pagination").innerHTML = pager(data, "records");
        $("#records-prev")?.addEventListener("click", () => loadRecords(data.page - 1));
        $("#records-next")?.addEventListener("click", () => loadRecords(data.page + 1));
    }

    async function showRecord(recordId) {
        const record = await api.get(`/email/records/${recordId}`);
        const backdrop = document.createElement("div");
        backdrop.className = "modal-backdrop";
        backdrop.innerHTML = `<article class="modal"><header><div><p class="eyebrow">邮件记录 #${record.id}</p><h2>编辑邮件</h2></div><button class="icon-button" type="button" data-close-modal aria-label="关闭">×</button></header><form id="record-edit-form" class="modal-form"><label>主题<input name="email_subject" maxlength="300" value="${escape(record.subject)}"></label><label>正文<textarea name="email_content" rows="12">${escape(record.content)}</textarea></label><label>状态<select name="status"><option value="generated" ${record.status === "generated" ? "selected" : ""}>generated</option><option value="sent" ${record.status === "sent" ? "selected" : ""}>sent</option><option value="failed" ${record.status === "failed" ? "selected" : ""}>failed</option></select></label><div class="actions"><button class="primary" type="submit">保存内容</button><button class="secondary" type="button" data-mark-record>更新状态</button><button class="danger" type="button" data-delete-record>删除邮件</button></div></form></article>`;
        document.body.append(backdrop);
        const close = () => backdrop.remove();
        $("[data-close-modal]", backdrop).addEventListener("click", close);
        backdrop.addEventListener("click", (event) => {
            if (event.target === backdrop) close();
        });
        $("#record-edit-form", backdrop).addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            try {
                await api.put(`/email/records/${recordId}`, {
                    email_subject: form.get("email_subject"),
                    email_content: form.get("email_content"),
                });
                notice("邮件内容已保存");
                close();
                await loadRecords();
            } catch (error) {
                notice(error.message, true);
            }
        });
        $("[data-mark-record]", backdrop).addEventListener("click", async () => {
            try {
                const status = new FormData($("#record-edit-form", backdrop)).get("status");
                await api.patch(`/email/records/${recordId}`, { status });
                notice("邮件状态已更新");
                close();
                await loadRecords();
            } catch (error) {
                notice(error.message, true);
            }
        });
        $("[data-delete-record]", backdrop).addEventListener("click", async () => {
            if (!window.confirm("确定删除这封邮件吗？")) return;
            try {
                await api.delete(`/email/records/${recordId}`);
                notice("邮件已删除");
                close();
                await loadRecords();
            } catch (error) {
                notice(error.message, true);
            }
        });
    }

    async function batchDeleteRecords() {
        const recordIds = $$("[name=record-select]:checked").map((input) => Number(input.value));
        if (!recordIds.length) {
            notice("请先选择邮件记录", true);
            return;
        }
        if (!window.confirm(`确定删除选中的 ${recordIds.length} 封邮件吗？`)) return;
        try {
            const result = await api.delete("/email/records", { record_ids: recordIds });
            notice(`已删除 ${result.deleted_count} 封邮件`);
            await loadRecords();
        } catch (error) {
            notice(error.message, true);
        }
    }

    async function prompt(renderId) {
        const view = $("#view");
        view.innerHTML = page("Prompt 模板") + panel("当前模板", '<form id="prompt-form"><label class="stacked-label">模板内容<textarea name="content" rows="15" required></textarea></label><div class="actions"><button class="primary">保存模板</button></div></form>');
        const data = await api.get("/email/prompt");
        if (!isCurrentRender(renderId)) return;
        $("#prompt-form textarea").value = data.content;
        $("#prompt-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            try {
                await api.put("/email/prompt", { content: new FormData(event.currentTarget).get("content") });
                notice("模板已保存");
            } catch (error) {
                notice(error.message, true);
            }
        });
    }

    async function logs(renderId) {
        const view = $("#view");
        view.innerHTML = page("操作日志") + panel("审计记录", '<form id="log-filter" class="inline-form"><label>用户 ID<input name="user_id" type="number" min="1"></label><label>操作<select name="action"><option value="">全部</option><option value="model_training">model_training</option><option value="prediction">prediction</option><option value="model_import">model_import</option><option value="email_generation">email_generation</option><option value="email_update">email_update</option><option value="email_mark">email_mark</option><option value="email_delete">email_delete</option></select></label><button class="secondary">筛选</button></form><div id="log-table" class="empty">正在读取...</div>');
        const loadLogs = async (filters = {}) => {
            const params = new URLSearchParams({ per_page: "50", ...filters });
            const data = await api.get(`/logs?${params}`);
            if (!isCurrentRender(renderId)) return;
            $("#log-table").innerHTML = table(["用户", "动作", "详情", "时间"], data.items.map((row) => `<tr><td>${row.user_id}</td><td>${escape(row.action)}</td><td>${escape(row.details)}</td><td>${date(row.created_at)}</td></tr>`));
        };
        $("#log-filter").addEventListener("submit", (event) => {
            event.preventDefault();
            const filters = Object.fromEntries([...new FormData(event.currentTarget)].filter(([, value]) => value !== ""));
            loadLogs(filters);
        });
        await loadLogs();
    }

    async function render() {
        const renderId = ++state.renderId;
        state.route = location.hash.replace("#", "") || "overview";
        if (!routeNames[state.route] || (adminRoutes.has(state.route) && state.user.role !== "admin")) {
            state.route = "overview";
        }
        $("#page-kicker").textContent = routeNames[state.route].toUpperCase();
        renderNavigation();
        $("#view").setAttribute("aria-busy", "true");
        try {
            await ({ overview, customers, insights, prediction, email, records, prompt, models, metrics, modelFiles, logs }[state.route])(renderId);
        } catch (error) {
            if (!isCurrentRender(renderId)) return;
            $("#view").innerHTML = page("请求失败") + `<p class="error">${escape(error.message)}</p>`;
            if (!localStorage.getItem("insurance_token")) location.reload();
        } finally {
            if (isCurrentRender(renderId)) $("#view").setAttribute("aria-busy", "false");
        }
    }

    $("#login-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            await login($("#username").value, $("#password").value);
        } catch (error) {
            $("#login-error").hidden = false;
            $("#login-error").textContent = error.message;
        }
    });
    $("#register-button").addEventListener("click", async () => {
        try {
            await login($("#username").value, $("#password").value, true);
        } catch (error) {
            $("#login-error").hidden = false;
            $("#login-error").textContent = error.message;
        }
    });
    $("#logout-button").addEventListener("click", () => {
        localStorage.removeItem("insurance_token");
        location.reload();
    });
    window.addEventListener("hashchange", render);
    (async () => {
        if (!localStorage.getItem("insurance_token")) return;
        try {
            state.user = await api.get("/auth/me");
            shell();
            await render();
        } catch {
            localStorage.removeItem("insurance_token");
        }
    })();
})();
