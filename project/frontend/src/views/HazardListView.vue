<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { AlertTriangle, CheckCircle2, ChevronRight, FileImage, ImagePlus, LoaderCircle, Plus, ScanSearch } from "lucide-vue-next";
import { http } from "../api/http";

const router = useRouter();
const items = ref<any[]>([]);
const selectedFile = ref<File | null>(null);
const previewUrl = ref("");
const result = ref<any>(null);
const analyzing = ref(false);
const error = ref("");
const success = ref("");
const elapsedSeconds = ref(0);
const prompt = ref("识别图中全部施工安全隐患，按风险等级标注并给出处置建议。");
const fileInput = ref<HTMLInputElement | null>(null);
let analysisTimer: number | undefined;
const levelLabels: Record<string, string> = { critical: "重大", major: "较大", minor: "一般", trivial: "轻微" };
const risks = computed(() => result.value?.items || []);
const createdHazard = computed(() => result.value?.created_hazard || null);
const waitingCopy = computed(() => {
  if (elapsedSeconds.value < 20) return "正在上传图片并请求视觉模型";
  if (elapsedSeconds.value < 60) return "模型正在逐项定位隐患，请耐心等待";
  return "复杂现场需要更长分析时间，任务仍在处理中";
});

async function load() {
  items.value = (await http.get("/hazards", { params: { page_size: 20 } })).data.data.items;
}
function chooseFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  selectedFile.value = file;
  previewUrl.value = URL.createObjectURL(file);
  result.value = null;
  error.value = "";
  success.value = "";
}
function startWaitingTimer() {
  elapsedSeconds.value = 0;
  analysisTimer = window.setInterval(() => { elapsedSeconds.value += 1; }, 1000);
}
function stopWaitingTimer() {
  if (analysisTimer !== undefined) window.clearInterval(analysisTimer);
  analysisTimer = undefined;
}
async function analyze() {
  if (!selectedFile.value) { fileInput.value?.click(); return; }
  analyzing.value = true;
  error.value = "";
  success.value = "";
  startWaitingTimer();
  const body = new FormData();
  body.append("image", selectedFile.value);
  body.append("prompt", prompt.value);
  try {
    result.value = (await http.post("/hazard-analysis/analyze", body)).data.data;
    await load();
    success.value = createdHazard.value
      ? `分析完成，已自动新增台账 ${createdHazard.value.hazard_id}`
      : "分析完成，未识别到明确隐患，因此没有新增台账。";
  }
  catch (exc: any) { error.value = exc.response?.data?.message || "图片分析失败，请检查模型配置后重试。"; }
  finally { analyzing.value = false; stopWaitingTimer(); }
}
onMounted(load);
onBeforeUnmount(() => {
  stopWaitingTimer();
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
});
</script>

<template>
  <section class="workspace hazard-workspace">
    <aside class="work-rail">
      <button class="primary-action" @click="router.push('/hazards/create')"><Plus :size="18" /> 上报新隐患</button>
      <div class="rail-heading">隐患台账 <span>{{ items.length }}</span></div>
      <button v-for="item in items" :key="item.hazard_id" class="history-item hazard-history" @click="router.push('/hazards/' + item.hazard_id)">
        <div><strong>{{ item.title }}</strong><b class="risk-pill" :class="item.level">{{ levelLabels[item.level] || item.level }}</b></div>
        <span>{{ item.location }} · {{ item.hazard_id }}</span>
      </button>
    </aside>

    <main class="hazard-stage">
      <header class="stage-header">
        <div><span class="eyebrow">VISUAL INSPECTION</span><h2>现场隐患智能批注</h2></div>
        <button class="secondary-button" :disabled="analyzing" @click="fileInput?.click()"><ImagePlus :size="17" /> 选择现场图片</button>
      </header>
      <input ref="fileInput" hidden type="file" accept="image/png,image/jpeg,image/webp" @change="chooseFile" />
      <div class="inspection-canvas" :class="{ empty: !previewUrl }" @click="!previewUrl && fileInput?.click()">
        <template v-if="previewUrl">
          <img :src="result?.image_url || previewUrl" alt="现场隐患分析图片" />
          <div v-if="analyzing" class="analysis-overlay"><LoaderCircle class="spin" :size="30" /><strong>{{ waitingCopy }}</strong><span>已等待 {{ elapsedSeconds }} 秒 · 请勿重复提交或关闭页面</span></div>
        </template>
        <div v-else class="upload-empty"><FileImage :size="42" /><h3>上传现场照片开始识别</h3><p>支持 JPG、PNG、WEBP，单张不超过 15MB</p></div>
      </div>
      <div class="analysis-prompt">
        <textarea v-model="prompt" rows="2" aria-label="图片分析要求"></textarea>
        <button class="primary-action compact" :disabled="analyzing" @click="analyze"><ScanSearch :size="18" /> {{ selectedFile ? "开始智能分析" : "选择图片" }}</button>
      </div>
      <p v-if="error" class="error-banner"><AlertTriangle :size="17" />{{ error }}</p>
      <div v-if="success" class="success-banner"><CheckCircle2 :size="17" /><span>{{ success }}</span><button v-if="createdHazard" @click="router.push('/hazards/' + createdHazard.hazard_id)">查看台账 <ChevronRight :size="14" /></button></div>
      <div class="detected-strip">
        <div><strong>检出要素</strong><span>{{ risks.length ? "已识别 " + risks.length + " 项隐患" : "分析结果将在此处汇总" }}</span></div>
        <button v-for="(risk, index) in risks" :key="index" class="detected-item" :disabled="!createdHazard" @click="createdHazard && router.push('/hazards/' + createdHazard.hazard_id)"><span class="risk-dot" :class="risk.risk === '高' ? 'high' : risk.risk === '中' ? 'medium' : 'low'"></span>{{ risk.label || "未命名隐患" }}<ChevronRight :size="14" /></button>
      </div>
    </main>

    <aside class="report-panel">
      <div class="panel-title"><ScanSearch :size="18" /><div><strong>分析报告</strong><small>{{ result ? result.model + " · " + result.count + " 项" : "等待图片分析" }}</small></div></div>
      <div v-if="!risks.length" class="evidence-empty">上传现场照片后，这里会按风险等级列出隐患名称、判断依据和整改建议。</div>
      <article v-for="(risk, index) in risks" :key="index" class="risk-report">
        <header><span>{{ String(index + 1).padStart(2, "0") }}</span><div><strong>{{ risk.label || "现场隐患" }}</strong><small>{{ risk.risk || "待定" }}风险</small></div></header>
        <p>{{ risk.description || risk.reason || risk.note || "已在图片中完成区域批注，请结合现场条件复核。" }}</p>
        <div v-if="risk.fix || risk.suggestion"><b>处置建议</b>{{ risk.fix || risk.suggestion }}</div>
      </article>
    </aside>
  </section>
</template>
