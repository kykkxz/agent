<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  Check,
  CheckCircle2,
  ClipboardCheck,
  FilePlus2,
  LoaderCircle,
  Sparkles,
  XCircle,
} from "lucide-vue-next";
import { http } from "../api/http";

const mode = ref<"review" | "create">("review");
const items = ref<any[]>([]);
const total = ref(0);
const pending = ref<any[]>([]);
const selectedId = ref<number | null>(null);
const loading = ref(false);
const actionLoading = ref(false);
const generating = ref(false);
const notice = ref("");
const error = ref("");
const form = reactive({
  type: "single_choice",
  content: "",
  options: { A: "", B: "", C: "", D: "" },
  answer: "A",
  explanation: "",
  score: 2,
  difficulty: "medium",
  category: "安全生产法",
  status: "published",
});
const current = computed(() => pending.value.find((item) => item.question_id === selectedId.value) || pending.value[0] || null);
const publishedCount = computed(() => items.value.filter((item) => item.status === "published").length);
const rejectedCount = computed(() => items.value.filter((item) => item.status === "rejected").length);
const typeLabels: Record<string, string> = { single_choice: "单选题", true_false: "判断题", multi_choice: "多选题", fill_blank: "填空题", essay: "简答题" };
const difficultyLabels: Record<string, string> = { easy: "简单", medium: "中等", hard: "困难" };

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [questionResponse, pendingResponse] = await Promise.all([
      http.get("/exam/questions?page_size=200"),
      http.get("/exam/review/pending"),
    ]);
    items.value = questionResponse.data.data.items;
    total.value = questionResponse.data.data.total;
    pending.value = pendingResponse.data.data;
    if (!pending.value.some((item) => item.question_id === selectedId.value)) {
      selectedId.value = pending.value[0]?.question_id || null;
    }
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "题库加载失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  form.type = "single_choice";
  form.content = "";
  Object.assign(form.options, { A: "", B: "", C: "", D: "" });
  form.answer = "A";
  form.explanation = "";
  form.score = 2;
  form.difficulty = "medium";
  form.category = "安全生产法";
}

async function create() {
  notice.value = "";
  error.value = "";
  if (!form.content.trim()) {
    error.value = "请先填写题干。";
    return;
  }
  actionLoading.value = true;
  try {
    await http.post("/exam/questions", {
      ...form,
      options: { ...form.options },
    });
    notice.value = "题目已保存并进入正式题库。";
    resetForm();
    await load();
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "题目保存失败，请检查填写内容。";
  } finally {
    actionLoading.value = false;
  }
}

async function generate() {
  generating.value = true;
  notice.value = "";
  error.value = "";
  try {
    await http.post("/exam/ai/generate", { knowledge_points: ["高处作业", "安全生产法"], count: 3 });
    mode.value = "review";
    notice.value = "已生成 3 道题目并加入待审核队列。";
    await load();
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "AI 出题失败，请稍后重试。";
  } finally {
    generating.value = false;
  }
}

async function review(result: "approved" | "rejected") {
  if (!current.value) return;
  actionLoading.value = true;
  notice.value = "";
  error.value = "";
  const reviewedContent = current.value.content;
  try {
    await http.post(`/exam/review/${current.value.question_id}`, { result });
    notice.value = result === "approved" ? `已通过：${reviewedContent}` : `已驳回：${reviewedContent}`;
    await load();
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "审核操作失败，请稍后重试。";
  } finally {
    actionLoading.value = false;
  }
}

function optionIsAnswer(key: string, value: string) {
  if (!current.value) return false;
  return String(current.value.answer).split(/[、,，]/).includes(key) || current.value.answer === value;
}

onMounted(load);
</script>

<template>
  <section class="question-page">
    <header class="question-toolbar">
      <div>
        <span class="eyebrow">QUESTION GOVERNANCE</span>
        <h2>题库审核工作台</h2>
        <p>先处理待审核题目，需要补充内容时再切换到手工录入。</p>
      </div>
      <div class="question-metrics" aria-label="题库统计">
        <span>待审核<b>{{ pending.length }}</b></span>
        <span>已发布<b>{{ publishedCount }}</b></span>
        <span>题库总量<b>{{ total }}</b></span>
      </div>
    </header>

    <div class="question-controls">
      <div class="segmented-control" aria-label="题库工作模式">
        <button :class="{ active: mode === 'review' }" :aria-pressed="mode === 'review'" @click="mode = 'review'"><ClipboardCheck :size="16" /> 待审核队列</button>
        <button :class="{ active: mode === 'create' }" :aria-pressed="mode === 'create'" @click="mode = 'create'"><FilePlus2 :size="16" /> 手工录入</button>
      </div>
      <button class="secondary-button" :disabled="generating" @click="generate"><LoaderCircle v-if="generating" class="spin" :size="16" /><Sparkles v-else :size="16" /> AI 生成 3 题</button>
    </div>

    <p v-if="notice" class="success-banner"><Check :size="17" />{{ notice }}</p>
    <p v-if="error" class="error-banner">{{ error }}</p>

    <div v-if="mode === 'review'" class="question-review-layout">
      <aside class="review-queue" aria-label="待审核题目列表">
        <header><strong>审核队列</strong><span>{{ pending.length }} 道</span></header>
        <div v-if="loading" class="inline-loading"><LoaderCircle class="spin" :size="17" /> 正在加载</div>
        <button
          v-for="(item, index) in pending"
          :key="item.question_id"
          class="review-queue-item"
          :class="{ active: current?.question_id === item.question_id }"
          :aria-pressed="current?.question_id === item.question_id"
          @click="selectedId = item.question_id"
        >
          <span>{{ String(index + 1).padStart(2, "0") }}</span>
          <div><strong>{{ item.content }}</strong><small>{{ typeLabels[item.type] || item.type }} · {{ item.category }}</small></div>
        </button>
        <div v-if="!loading && !pending.length" class="review-empty"><CheckCircle2 :size="28" /><strong>审核队列已清空</strong><span>可使用 AI 出题或切换到手工录入。</span></div>
      </aside>

      <main class="review-detail">
        <template v-if="current">
          <header class="review-detail-header">
            <div><span class="eyebrow">CURRENT QUESTION</span><h3>当前审核题目</h3></div>
            <div class="question-tags"><span>{{ typeLabels[current.type] || current.type }}</span><span>{{ difficultyLabels[current.difficulty] || current.difficulty }}</span><span>{{ current.score }} 分</span></div>
          </header>
          <div class="question-copy">
            <small>{{ current.category }} · 编号 #{{ current.question_id }}</small>
            <h2>{{ current.content }}</h2>
          </div>
          <div v-if="current.options && Object.keys(current.options).length" class="review-options">
            <div v-for="(value, key) in current.options" :key="key" :class="{ answer: optionIsAnswer(String(key), String(value)) }">
              <b>{{ key }}</b><span>{{ value }}</span><small v-if="optionIsAnswer(String(key), String(value))">正确答案</small>
            </div>
          </div>
          <div class="answer-rationale">
            <span>答案依据</span>
            <p>{{ current.explanation || "暂无解析，请审核题干与答案后决定是否通过。" }}</p>
          </div>
          <div class="review-actions">
            <button class="secondary-button danger" :disabled="actionLoading" @click="review('rejected')"><XCircle :size="17" /> 驳回题目</button>
            <button class="primary-action compact" :disabled="actionLoading" @click="review('approved')"><LoaderCircle v-if="actionLoading" class="spin" :size="17" /><CheckCircle2 v-else :size="17" /> 通过并审核下一题</button>
          </div>
        </template>
        <div v-else class="review-detail-empty"><CheckCircle2 :size="36" /><h3>没有待审核题目</h3><p>当前正式题库共 {{ total }} 道，已驳回 {{ rejectedCount }} 道。</p></div>
      </main>
    </div>

    <form v-else class="question-create-form" @submit.prevent="create">
      <header><div><span class="eyebrow">MANUAL ENTRY</span><h3>录入正式题目</h3></div><p>手工录入的题目保存后直接进入正式题库。</p></header>
      <div class="question-form-grid">
        <label><span>题型</span><select v-model="form.type"><option value="single_choice">单选题</option><option value="true_false">判断题</option><option value="multi_choice">多选题</option><option value="fill_blank">填空题</option></select></label>
        <label><span>分类</span><input v-model="form.category" /></label>
        <label><span>难度</span><select v-model="form.difficulty"><option value="easy">简单</option><option value="medium">中等</option><option value="hard">困难</option></select></label>
        <label><span>分值</span><input v-model.number="form.score" type="number" min="1" max="20" /></label>
      </div>
      <label class="question-form-full"><span>题干</span><textarea v-model="form.content" rows="4" placeholder="输入完整、无歧义的题目"></textarea></label>
      <div v-if="['single_choice','multi_choice'].includes(form.type)" class="option-entry-grid">
        <label v-for="key in ['A','B','C','D']" :key="key"><span>选项 {{ key }}</span><input v-model="form.options[key as keyof typeof form.options]" :placeholder="`输入选项 ${key}`" /></label>
      </div>
      <label class="question-form-full"><span>正确答案</span><input v-model="form.answer" placeholder="单选填 A，多选可填 A,B，判断题填 正确/错误" /></label>
      <label class="question-form-full"><span>答案解析</span><textarea v-model="form.explanation" rows="3" placeholder="说明依据条款和判断理由"></textarea></label>
      <div class="builder-actions"><button class="primary-action compact" type="submit" :disabled="actionLoading"><LoaderCircle v-if="actionLoading" class="spin" :size="17" /><FilePlus2 v-else :size="17" /> 保存到正式题库</button></div>
    </form>
  </section>
</template>
