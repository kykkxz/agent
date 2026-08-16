<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { http } from "../api/http";

const router = useRouter();
const error = ref("");
const form = reactive({
  title: "",
  description: "",
  level: "major",
  category: "edge_protection",
  location: "",
  project: "成绵高速扩容项目",
  occurred_at: new Date().toISOString(),
});

async function submit() {
  error.value = "";
  try {
    const { data } = await http.post("/hazards/json", form);
    router.push(`/hazards/${data.data.hazard_id}`);
  } catch (err: any) {
    error.value = err.response?.data?.message || "上报失败";
  }
}
</script>

<template>
  <form class="card" @submit.prevent="submit">
    <h2 class="display">隐患上报</h2>
    <div class="field"><label>标题</label><input v-model="form.title" required /></div>
    <div class="field"><label>描述</label><textarea v-model="form.description" rows="5" required /></div>
    <div class="grid-2">
      <div class="field">
        <label>等级</label>
        <select v-model="form.level">
          <option value="critical">重大</option>
          <option value="major">较大</option>
          <option value="minor">一般</option>
          <option value="trivial">轻微</option>
        </select>
      </div>
      <div class="field">
        <label>类别</label>
        <select v-model="form.category">
          <option value="edge_protection">临边防护</option>
          <option value="height_work">高处作业</option>
          <option value="temp_electricity">临时用电</option>
          <option value="fire_safety">消防</option>
          <option value="machinery">机械</option>
        </select>
      </div>
    </div>
    <div class="field"><label>位置</label><input v-model="form.location" required /></div>
    <div class="field"><label>项目</label><input v-model="form.project" required /></div>
    <p v-if="error" style="color: var(--signal)">{{ error }}</p>
    <button class="btn">提交上报</button>
  </form>
</template>