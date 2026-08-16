<script setup lang="ts">
import { onMounted, ref } from "vue";
import { BookOpen, Database, FileSearch, Search, ShieldCheck } from "lucide-vue-next";
import { http } from "../api/http";

const keyword = ref("");
const items = ref<any[]>([]);
const hits = ref<any[]>([]);
const overview = ref<any>({});
const searching = ref(false);

async function load() { items.value = (await http.get("/knowledge/documents", { params: { keyword: keyword.value } })).data.data.items; }
async function search() {
  if (!keyword.value.trim()) return load();
  searching.value = true;
  try { hits.value = (await http.get("/knowledge/search", { params: { q: keyword.value, limit: 8 } })).data.data; }
  finally { searching.value = false; }
}
onMounted(async () => {
  const [overviewResult, documentResult] = await Promise.all([http.get("/knowledge/overview"), http.get("/knowledge/documents")]);
  overview.value = overviewResult.data.data;
  items.value = documentResult.data.data.items;
});
</script>

<template>
  <section class="knowledge-page">
    <header class="knowledge-header">
      <div><span class="eyebrow">VERIFIED KNOWLEDGE</span><h2>交通安全知识库</h2><p>所有回答和试题均从 database 中的正式依据层检索，业务库与知识库保持分离。</p></div>
      <div class="kb-status"><ShieldCheck :size="18" /><span><strong>只读连接正常</strong><small>transport_safety_kb.sqlite3</small></span></div>
    </header>
    <div class="kb-metrics">
      <article><Database :size="20" /><span>正式文档<b>{{ overview.documents || 0 }}</b></span></article>
      <article><BookOpen :size="20" /><span>知识条目<b>{{ overview.knowledge_entries || 0 }}</b></span></article>
      <article><FileSearch :size="20" /><span>证据单元<b>{{ overview.evidence_units || 0 }}</b></span></article>
    </div>
    <div class="knowledge-search"><Search :size="19" /><input v-model="keyword" placeholder="检索法规、条款、事故案例或应急预案" @keydown.enter="search" /><button :disabled="searching" @click="search">检索知识</button></div>
    <div v-if="hits.length" class="search-results">
      <div class="section-heading"><strong>检索结果</strong><span>{{ hits.length }} 条相关证据</span></div>
      <article v-for="(item, index) in hits" :key="item.knowledge_id" class="knowledge-hit">
        <span>[{{ index + 1 }}]</span><div><h3>{{ item.title }}</h3><p>{{ item.snippet }}</p><footer>{{ item.publisher }} · {{ item.document_type }} · {{ item.authority_level }}</footer></div>
      </article>
    </div>
    <div class="document-list">
      <div class="section-heading"><strong>已纳入文档</strong><span>{{ items.length }} 条当前页记录</span></div>
      <article v-for="item in items" :key="item.document_id" class="document-row">
        <FileSearch :size="19" /><div><strong>{{ item.title }}</strong><small>{{ item.document_id }} · {{ item.publisher }}</small></div><span>{{ item.document_type }}</span><b>{{ item.authority_level }}</b>
      </article>
    </div>
  </section>
</template>
