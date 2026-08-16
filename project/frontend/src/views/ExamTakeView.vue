<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { http } from "../api/http";

const route = useRoute();
const router = useRouter();
const paper = ref<any>(null);
const answers = reactive<Record<string, string>>({});

onMounted(async () => {
  paper.value = (await http.post(`/exam/my-exams/${route.params.paperId}/start`)).data.data;
});

async function submit() {
  const { data } = await http.post(`/exam/attempts/${paper.value.attempt_id}/submit`, { answers });
  router.push(`/exams/result/${data.data.attempt_id}`);
}
</script>

<template>
  <div v-if="paper" class="card">
    <h2 class="display">{{ paper.title }}</h2>
    <div v-for="(question, index) in paper.questions" :key="question.question_id" class="field">
      <label>{{ index + 1 }}. {{ question.content }}</label>
      <div v-if="question.options && Object.keys(question.options).length">
        <label v-for="(text, key) in question.options" :key="key" style="display:block">
          <input type="radio" :name="String(question.question_id)" :value="key" v-model="answers[question.question_id]" />
          {{ key }}. {{ text }}
        </label>
      </div>
      <input v-else v-model="answers[question.question_id]" />
    </div>
    <button class="btn" @click="submit">交卷</button>
  </div>
</template>