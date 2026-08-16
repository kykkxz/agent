<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { AlertTriangle, BookOpen, Bot, CheckCircle2, ChevronRight, MessageSquarePlus, Send, Sparkles, ThumbsDown, ThumbsUp } from "lucide-vue-next";
import { http } from "../api/http";

type Citation = { knowledge_id: string; title: string; snippet: string; publisher: string; authority_level: string; source_uri: string };
type Message = { message_id: number; role: string; content: string; citations?: Citation[]; feedback?: string };

const sessions = ref<any[]>([]);
const current = ref("");
const messages = ref<Message[]>([]);
const question = ref("");
const quick = ref<any[]>([]);
const capabilities = ref<any>({});
const sending = ref(false);
const sendError = ref("");
const elapsedSeconds = ref(0);
const activeCitations = ref<Citation[]>([]);
const messagePane = ref<HTMLElement | null>(null);
let sendTimer: number | undefined;
const currentTitle = computed(() => sessions.value.find((item) => item.session_id === current.value)?.title || "新对话");
const waitingCopy = computed(() => {
  if (elapsedSeconds.value < 15) return "正在检索并整理依据";
  if (elapsedSeconds.value < 45) return "Agent 正在核对文档并组织引用";
  return "模型仍在生成，请耐心等待";
});

async function loadSessions() { sessions.value = (await http.get("/ai/sessions")).data.data; }
async function loadMessages(id: string) {
  current.value = id;
  messages.value = (await http.get("/ai/sessions/" + id + "/messages")).data.data;
  const lastAnswer = [...messages.value].reverse().find((item) => item.role === "assistant");
  activeCitations.value = lastAnswer?.citations || [];
  await nextTick();
  messagePane.value?.scrollTo({ top: messagePane.value.scrollHeight, behavior: "smooth" });
}
async function newSession() {
  const { data } = await http.post("/ai/sessions", { title: "新会话" });
  await loadSessions();
  await loadMessages(data.data.session_id);
}
async function send(text?: string) {
  const content = (text || question.value).trim();
  if (!content || sending.value) return;
  question.value = "";
  messages.value.push({ message_id: Date.now(), role: "user", content });
  sending.value = true;
  sendError.value = "";
  elapsedSeconds.value = 0;
  sendTimer = window.setInterval(() => { elapsedSeconds.value += 1; }, 1000);
  try {
    const { data } = await http.post("/ai/chat/sync", { question: content, session_id: current.value || null });
    current.value = data.data.session_id;
    await loadSessions();
    await loadMessages(current.value);
  } catch (exc: any) {
    sendError.value = exc.response?.data?.message || "回答生成失败，请稍后重试。";
  } finally {
    sending.value = false;
    if (sendTimer !== undefined) window.clearInterval(sendTimer);
    sendTimer = undefined;
  }
}
async function feedback(message: Message, value: string) {
  await http.post("/ai/messages/" + message.message_id + "/feedback", { feedback: value });
  message.feedback = value;
}
function showSources(message: Message) { activeCitations.value = message.citations || []; }
function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); }
}
onMounted(async () => {
  const [sessionResult, quickResult, capabilityResult] = await Promise.all([
    http.get("/ai/sessions"), http.get("/ai/quick-questions"), http.get("/ai/capabilities"),
  ]);
  sessions.value = sessionResult.data.data;
  quick.value = quickResult.data.data;
  capabilities.value = capabilityResult.data.data;
  if (sessions.value[0]) await loadMessages(sessions.value[0].session_id);
});
onBeforeUnmount(() => {
  if (sendTimer !== undefined) window.clearInterval(sendTimer);
});
</script>

<template>
  <section class="workspace ai-workspace">
    <aside class="work-rail">
      <button class="primary-action" @click="newSession"><MessageSquarePlus :size="18" /> 新建对话</button>
      <div class="rail-heading">历史会话 <span>{{ sessions.length }}</span></div>
      <button v-for="item in sessions" :key="item.session_id" class="history-item" :class="{ selected: item.session_id === current }" @click="loadMessages(item.session_id)">
        <strong>{{ item.title }}</strong><span>{{ item.last_message || "等待提问" }}</span>
      </button>
      <div class="agent-state"><span class="state-dot"></span><div><strong>{{ capabilities.model }}</strong><small>{{ capabilities.agent }} · 知识库已连接</small></div></div>
    </aside>

    <main class="chat-stage">
      <header class="stage-header">
        <div><span class="eyebrow">SAFETY COPILOT</span><h2>{{ currentTitle }}</h2></div>
        <span class="verified"><CheckCircle2 :size="15" /> 基于正式依据层回答</span>
      </header>
      <div ref="messagePane" class="message-pane">
        <div v-if="!messages.length" class="welcome-state">
          <div class="assistant-mark"><Bot :size="30" /></div>
          <h1>今天需要核查什么安全问题？</h1>
          <p>我会先检索项目知识库，再给出带来源编号的回答。关键结论可在右侧逐条复核。</p>
          <div class="quick-grid">
            <button v-for="item in quick.slice(0, 4)" :key="item.id" @click="send(item.question)">
              <Sparkles :size="16" /><span><small>{{ item.category }}</small>{{ item.question }}</span><ChevronRight :size="16" />
            </button>
          </div>
        </div>
        <article v-for="item in messages" :key="item.message_id" class="message" :class="item.role">
          <div class="message-avatar"><Bot v-if="item.role === 'assistant'" :size="17" /><span v-else>我</span></div>
          <div class="message-body">
            <div class="message-copy">{{ item.content }}</div>
            <div v-if="item.role === 'assistant'" class="message-meta">
              <button v-if="item.citations?.length" @click="showSources(item)"><BookOpen :size="14" /> {{ item.citations.length }} 条文档依据</button>
              <span></span>
              <button :class="{ chosen: item.feedback === 'up' }" aria-label="回答有帮助" @click="feedback(item, 'up')"><ThumbsUp :size="14" /></button>
              <button :class="{ chosen: item.feedback === 'down' }" aria-label="回答需改进" @click="feedback(item, 'down')"><ThumbsDown :size="14" /></button>
            </div>
          </div>
        </article>
        <div v-if="sending" class="thinking"><span></span><span></span><span></span> {{ waitingCopy }} · {{ elapsedSeconds }} 秒</div>
      </div>
      <div class="composer-wrap">
        <p v-if="sendError" class="error-banner"><AlertTriangle :size="16" />{{ sendError }}</p>
        <div class="composer"><textarea v-model="question" rows="2" placeholder="询问法规条款、现场处置或作业要求…" @keydown="handleKeydown"></textarea><button class="send-button" :disabled="sending || !question.trim()" aria-label="发送问题" @click="send()"><Send :size="19" /></button></div>
        <small>AI 回答仅作安全管理辅助，现场处置应结合有效制度和专业人员判断。</small>
      </div>
    </main>

    <aside class="evidence-panel">
      <div class="panel-title"><BookOpen :size="18" /><div><strong>引用依据</strong><small>当前回答的可追溯来源</small></div></div>
      <div v-if="!activeCitations.length" class="evidence-empty">选择一条 AI 回答，可在这里查看引用的法规、规程和事故资料。</div>
      <article v-for="(cite, index) in activeCitations" :key="cite.knowledge_id" class="evidence-card">
        <div class="citation-index">[{{ index + 1 }}]</div><h3>{{ cite.title }}</h3><p>{{ cite.snippet }}</p>
        <footer><span>{{ cite.publisher || "发布机构未标注" }}</span><b>{{ cite.authority_level }}</b></footer>
      </article>
    </aside>
  </section>
</template>
