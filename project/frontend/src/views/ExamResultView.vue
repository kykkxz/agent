<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { http } from "../api/http";

const route = useRoute();
const result = ref<any>(null);

onMounted(async () => {
  result.value = (await http.get(`/exam/attempts/${route.params.attemptId}/result`)).data.data;
});
</script>

<template>
  <div v-if="result" class="card">
    <h2 class="display">{{ result.title }}</h2>
    <p>得分 {{ result.score }} · {{ result.passed ? "通过" : "未通过" }}</p>
    <div v-for="item in result.items" :key="item.question_id" class="field">
      <strong>{{ item.content }}</strong>
      <div>你的答案：{{ item.user_answer }} / 正确答案：{{ item.answer }}</div>
      <div style="color: var(--muted)">{{ item.explanation }}</div>
    </div>
  </div>
</template>