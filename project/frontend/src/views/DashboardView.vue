<script setup lang="ts">
import { onMounted, ref } from "vue";
import { http } from "../api/http";

const overview = ref<any>({});
const exams = ref<any>({});
const kb = ref<any>({});

const statusLabels: Record<string, string> = {
  pending: "待派单",
  processing: "整改中",
  pending_review: "待验收",
  closed: "已闭环",
  rejected: "已驳回",
};

function formatStatus(status: string) {
  return statusLabels[status] || status;
}

onMounted(async () => {
  overview.value = (await http.get("/statistics/hazards/overview")).data.data;
  exams.value = (await http.get("/statistics/exams/overview")).data.data;
  kb.value = (await http.get("/knowledge/overview")).data.data;
});
</script>

<template>
  <div class="grid-3">
    <div class="card kpi">
      <span>隐患总数 / 闭环率</span>
      <b>{{ overview.total || 0 }} · {{ overview.closure_rate || 0 }}%</b>
    </div>
    <div class="card kpi">
      <span>考试通过率</span>
      <b>{{ exams.pass_rate || 0 }}%</b>
    </div>
    <div class="card kpi">
      <span>正式知识条目</span>
      <b>{{ kb.knowledge_entries || 0 }}</b>
    </div>
  </div>
  <div class="grid-2" style="margin-top: 16px">
    <div class="card">
      <h3 class="display">状态分布</h3>
      <p v-for="(count, key) in overview.by_status || {}" :key="key">{{ formatStatus(String(key)) }} · {{ count }}</p>
    </div>
    <div class="card">
      <h3 class="display">知识库覆盖</h3>
      <p v-for="(count, key) in kb.document_types || {}" :key="key">{{ key }} · {{ count }}</p>
    </div>
  </div>
</template>
