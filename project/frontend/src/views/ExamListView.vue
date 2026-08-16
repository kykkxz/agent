<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import {
  BookOpenCheck,
  Check,
  ChevronRight,
  FileText,
  LoaderCircle,
  PencilLine,
  PlayCircle,
  Plus,
  Save,
  Sparkles,
  Upload,
} from "lucide-vue-next";
import { http } from "../api/http";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const exams = ref<any[]>([]);
const papers = ref<any[]>([]);
const generated = ref<any[]>([]);
const selectedPaperId = ref<number | null>(null);
const selectedStatus = ref("");
const generating = ref(false);
const saving = ref(false);
const loadingPaper = ref(false);
const notice = ref("");
const error = ref("");
const form = reactive({
  title: "施工安全知识专项测试",
  knowledge: "高处作业、安全生产法、临时用电",
  attachEvidence: true,
  counts: { single_choice: 10, true_false: 10, multi_choice: 8, fill_blank: 2, essay: 0 },
  scores: { single_choice: 2, true_false: 2, multi_choice: 5, fill_blank: 10, essay: 10 },
  duration: 45,
  passScore: 60,
});
const isManager = computed(() => ["Admin", "SafetyOfficer"].includes(auth.user?.role || ""));
const isPublished = computed(() => selectedStatus.value === "published");
const totalQuestions = computed(() => Object.values(form.counts).reduce((sum, value) => sum + value, 0));
const totalScore = computed(() => Object.keys(form.counts).reduce((sum, key) => sum + form.counts[key as keyof typeof form.counts] * form.scores[key as keyof typeof form.scores], 0));
const typeLabels: Record<string, string> = { single_choice: "单选题", true_false: "判断题", multi_choice: "多选题", fill_blank: "填空题", essay: "简答题" };

function resetCounts() {
  Object.keys(form.counts).forEach((type) => { form.counts[type as keyof typeof form.counts] = 0; });
}

function newTask() {
  selectedPaperId.value = null;
  selectedStatus.value = "";
  generated.value = [];
  form.title = "";
  form.knowledge = "高处作业、安全生产法、临时用电";
  form.duration = 45;
  form.passScore = 60;
  Object.assign(form.counts, { single_choice: 10, true_false: 10, multi_choice: 8, fill_blank: 2, essay: 0 });
  notice.value = "已创建空白组卷任务。";
  error.value = "";
}

async function load() {
  exams.value = (await http.get("/exam/my-exams")).data.data;
  if (isManager.value) papers.value = (await http.get("/exam/papers")).data.data;
}

async function openPaper(paper: any) {
  loadingPaper.value = true;
  notice.value = "";
  error.value = "";
  try {
    const detail = (await http.get(`/exam/papers/${paper.paper_id}`)).data.data;
    selectedPaperId.value = paper.paper_id;
    selectedStatus.value = detail.status;
    form.title = detail.title;
    form.knowledge = String(detail.description || "").replace(/^依据[：:]/, "") || "未填写出题依据";
    form.duration = detail.duration_minutes;
    form.passScore = detail.pass_score;
    generated.value = detail.questions || [];
    resetCounts();
    generated.value.forEach((question) => {
      const type = question.type as keyof typeof form.counts;
      if (type in form.counts) {
        form.counts[type] += 1;
        form.scores[type] = question.score || form.scores[type];
      }
    });
    notice.value = detail.status === "published" ? "已切换到已发布试卷，可查看结构或进入考试。" : "草稿已载入，可继续调整后保存。";
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "任务加载失败，请稍后重试。";
  } finally {
    loadingPaper.value = false;
  }
}

async function generate() {
  generating.value = true;
  notice.value = "";
  error.value = "";
  try {
    const points = form.knowledge.split(/[、,，\n]/).map((item) => item.trim()).filter(Boolean);
    const types = Object.entries(form.counts).filter(([, count]) => count > 0).map(([type]) => type);
    const count = Math.min(totalQuestions.value, 30);
    generated.value = (await http.post("/exam/ai/generate", { knowledge_points: points, types, count, difficulty: "mixed" })).data.data;
    notice.value = `已生成 ${generated.value.length} 道待审核题目，可保存当前试卷草稿。`;
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "题目生成失败，请检查出题依据。";
  } finally {
    generating.value = false;
  }
}

function paperPayload() {
  return {
    title: form.title,
    description: "依据：" + form.knowledge,
    duration_minutes: form.duration,
    pass_score: form.passScore,
    question_ids: generated.value.map((item) => item.question_id),
    max_attempts: 2,
  };
}

async function savePaper() {
  saving.value = true;
  notice.value = "";
  error.value = "";
  try {
    const response = selectedPaperId.value
      ? await http.put(`/exam/papers/${selectedPaperId.value}`, paperPayload())
      : await http.post("/exam/papers", paperPayload());
    selectedPaperId.value = response.data.data.paper_id;
    selectedStatus.value = "draft";
    notice.value = `草稿 #${selectedPaperId.value} 已保存。`;
    await load();
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "草稿保存失败，请稍后重试。";
  } finally {
    saving.value = false;
  }
}

async function publishPaper() {
  if (!selectedPaperId.value) return;
  saving.value = true;
  error.value = "";
  try {
    await http.post(`/exam/papers/${selectedPaperId.value}/publish`);
    selectedStatus.value = "published";
    notice.value = "试卷已发布，现在可以进入考试。";
    await load();
  } catch (reason: any) {
    error.value = reason.response?.data?.message || "发布失败，请稍后重试。";
  } finally {
    saving.value = false;
  }
}

async function enterExam(paperId: number | null) {
  if (!paperId) {
    error.value = "未找到可进入的考试，请重新选择任务。";
    return;
  }
  error.value = "";
  try {
    await router.push({ name: "exam-take", params: { paperId: String(paperId) } });
  } catch {
    error.value = "考试页面打开失败，请稍后重试。";
  }
}

onMounted(load);
</script>

<template>
  <section v-if="isManager" class="workspace exam-workspace">
    <aside class="work-rail">
      <button class="primary-action" @click="newTask"><Plus :size="18" /> 新建组卷任务</button>
      <div class="rail-heading">组卷任务 <span>{{ papers.length }}</span></div>
      <button
        v-for="paper in papers"
        :key="paper.paper_id"
        class="history-item exam-task-item"
        :class="{ selected: selectedPaperId === paper.paper_id }"
        :aria-pressed="selectedPaperId === paper.paper_id"
        @click="openPaper(paper)"
      >
        <span class="task-row"><strong>{{ paper.title }}</strong><ChevronRight :size="15" /></span>
        <span>{{ paper.question_count }} 题 · {{ paper.status === "published" ? "已发布" : "草稿" }}</span>
      </button>
      <div v-if="!papers.length" class="rail-empty">暂无历史任务，从新建任务开始组卷。</div>
    </aside>

    <main class="exam-builder">
      <header class="stage-header">
        <div><span class="eyebrow">AI EXAM STUDIO</span><h2>{{ selectedPaperId ? "任务详情" : "智能组卷" }}</h2></div>
        <span class="verified"><Sparkles :size="15" /> 知识库依据生成</span>
      </header>
      <div v-if="selectedPaperId" class="editing-context">
        <span><PencilLine :size="15" /> 当前任务 #{{ selectedPaperId }}</span>
        <b :class="selectedStatus">{{ isPublished ? "已发布" : "草稿" }}</b>
      </div>
      <div v-if="loadingPaper" class="inline-loading"><LoaderCircle class="spin" :size="17" /> 正在载入任务</div>
      <label class="builder-field"><span>试卷名称</span><input v-model="form.title" :disabled="isPublished" maxlength="32" placeholder="输入便于识别的试卷名称" /><small>{{ form.title.length }}/32</small></label>
      <label class="builder-field"><span>出题依据</span><textarea v-model="form.knowledge" :disabled="isPublished" rows="5" placeholder="输入知识点、章节或培训内容"></textarea></label>
      <div class="attachment-row"><FileText :size="22" /><div><strong>正式知识库</strong><small>题目解析会引用 database 中的安全知识条目</small></div><Check :size="18" /></div>
      <div class="config-heading"><strong>题型配置</strong><label><input v-model="form.attachEvidence" :disabled="isPublished" type="checkbox" /> 附带出题依据条款</label><span>试卷总分 {{ totalScore }}</span></div>
      <div class="question-config-grid">
        <article v-for="(_, type) in form.counts" :key="type" class="question-config">
          <header><strong>{{ typeLabels[type] }}</strong><span>每题 <input v-model.number="form.scores[type]" :disabled="isPublished" type="number" min="1" max="20" /> 分</span></header>
          <label>数量 <input v-model.number="form.counts[type]" :disabled="isPublished" type="range" min="0" max="20" /><b>{{ form.counts[type] }} 题</b></label>
        </article>
      </div>
      <div class="builder-actions">
        <button v-if="isPublished" class="primary-action compact" @click="enterExam(selectedPaperId)"><PlayCircle :size="18" /> 进入考试</button>
        <template v-else>
          <button class="secondary-button" :disabled="generating || loadingPaper" @click="generate"><LoaderCircle v-if="generating" class="spin" :size="17" /><Sparkles v-else :size="17" /> 生成预览</button>
          <button class="primary-action compact" :disabled="saving || !form.title || loadingPaper" @click="savePaper"><Save :size="18" /> {{ selectedPaperId ? "保存草稿修改" : "保存试卷草稿" }}</button>
          <button v-if="selectedPaperId" class="secondary-button" :disabled="saving || !generated.length" @click="publishPaper"><Upload :size="17" /> 发布试卷</button>
        </template>
      </div>
      <p v-if="notice" class="success-banner"><Check :size="17" />{{ notice }}</p>
      <p v-if="error" class="error-banner">{{ error }}</p>
    </main>

    <aside class="exam-preview">
      <div class="panel-title"><BookOpenCheck :size="18" /><div><strong>任务预览</strong><small>当前组卷结构与分值</small></div></div>
      <div class="preview-title"><small>{{ selectedPaperId ? `任务 #${selectedPaperId}` : "新任务" }}</small><strong>{{ form.title || "未命名试卷" }}</strong></div>
      <div class="preview-section"><strong>结构大纲</strong><div v-for="(count, type) in form.counts" :key="type"><span>{{ typeLabels[type] }}</span><b>{{ count }} 题</b><small>{{ count * form.scores[type] }} 分</small></div></div>
      <div class="preview-score"><span>题目总数<b>{{ totalQuestions }}</b></span><span>试卷总分<b>{{ totalScore }}</b></span><span>考试时长<b>{{ form.duration }} 分</b></span><span>及格分<b>{{ form.passScore }}</b></span></div>
      <div v-if="generated.length" class="generated-preview"><strong>题目预览</strong><p v-for="item in generated.slice(0, 5)" :key="item.question_id">{{ item.content }}</p></div>
    </aside>
  </section>

  <section v-else class="exam-list-page">
    <header class="stage-header"><div><span class="eyebrow">MY EXAMS</span><h2>我的考试</h2></div></header>
    <article v-for="item in exams" :key="item.paper_id" class="exam-card">
      <div><small>待完成考试</small><h3>{{ item.title }}</h3><p>{{ item.duration_minutes }} 分钟 · 及格线 {{ item.pass_score }} · 已考 {{ item.attempt_count }}/{{ item.max_attempts }} 次</p></div>
      <button class="primary-action compact" @click="enterExam(item.paper_id)">进入考试 <ChevronRight :size="17" /></button>
    </article>
  </section>
</template>
