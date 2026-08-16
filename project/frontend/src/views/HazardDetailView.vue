<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft } from "lucide-vue-next";
import { http } from "../api/http";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const detail = ref<any>(null);
const users = ref<any[]>([]);
const assign = reactive({ assignee_id: "U003", requirements: "立即整改并回传照片", deadline: "2026-08-18T18:00:00+08:00", priority: "high" });
const measures = ref("已按规范完成防护恢复，现场复查合格并拍照留存。");
const comment = ref("整改到位，同意闭环");
const statusLabels: Record<string, string> = { pending: "待派单", processing: "整改中", pending_review: "待验收", closed: "已闭环", rejected: "已驳回" };

function imageLabel(url: string, index: number) {
  if (url.includes("/original")) return "现场原图";
  if (url.includes("/annotated")) return "AI 批注图";
  return `现场图片 ${index + 1}`;
}

async function load() {
  detail.value = (await http.get(`/hazards/${route.params.id}`)).data.data;
  if (["Admin", "SafetyOfficer"].includes(auth.user?.role || "")) {
    users.value = (await http.get("/users/options")).data.data;
  }
}

async function doAssign() {
  await http.post(`/hazards/${route.params.id}/assign`, assign);
  await load();
}
async function doRectify() {
  await http.post(`/hazards/${route.params.id}/rectify-json`, { measures: measures.value });
  await load();
}
async function doReview(result: string) {
  await http.post(`/hazards/${route.params.id}/review`, { result, comment: comment.value });
  await load();
}

onMounted(load);
</script>

<template>
  <div class="page-actions">
    <button class="back-button" type="button" @click="router.push('/hazards')"><ArrowLeft :size="17" /> 返回隐患台账</button>
  </div>
  <div v-if="detail" class="grid-2">
    <div class="card">
      <h2 class="display">{{ detail.title }}</h2>
      <p><span class="badge" :class="detail.status">{{ statusLabels[detail.status] || detail.status }}</span> · {{ detail.hazard_id }}</p>
      <p class="hazard-description">{{ detail.description }}</p>
      <p>位置：{{ detail.location }} / {{ detail.project }}</p>
      <section v-if="detail.media?.images?.length" class="hazard-media" aria-labelledby="hazard-media-title">
        <h3 id="hazard-media-title">现场影像</h3>
        <div class="hazard-media-grid">
          <a
            v-for="(image, index) in detail.media.images"
            :key="image"
            :href="image"
            class="hazard-media-item"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img :src="image" :alt="`${imageLabel(image, index)}：${detail.title}`" />
            <span>{{ imageLabel(image, index) }}</span>
          </a>
        </div>
      </section>
      <h3>时间线</h3>
      <p v-for="(item, idx) in detail.timeline" :key="idx">{{ item.time }} · {{ item.node }} · {{ item.operator }} · {{ item.note }}</p>
    </div>
    <div class="card">
      <div v-if="detail.status === 'pending' && ['Admin','SafetyOfficer'].includes(auth.user?.role || '')">
        <h3>派单</h3>
        <select v-model="assign.assignee_id">
          <option v-for="user in users" :key="user.id" :value="user.id">{{ user.name }}</option>
        </select>
        <textarea v-model="assign.requirements" rows="3" />
        <input v-model="assign.deadline" />
        <button class="btn" @click="doAssign">确认派单</button>
      </div>
      <div v-else-if="detail.status === 'processing'">
        <h3>整改反馈</h3>
        <textarea v-model="measures" rows="4" />
        <button class="btn" @click="doRectify">提交整改</button>
      </div>
      <div v-else-if="detail.status === 'pending_review' && ['Admin','SafetyOfficer'].includes(auth.user?.role || '')">
        <h3>验收</h3>
        <textarea v-model="comment" rows="3" />
        <button class="btn" @click="doReview('approved')">通过闭环</button>
        <button class="btn ghost" @click="doReview('rejected')">驳回</button>
      </div>
      <div v-else>
        <h3>当前节点</h3>
        <p>该隐患当前状态为{{ statusLabels[detail.status] || detail.status }}。</p>
      </div>
    </div>
  </div>
</template>
