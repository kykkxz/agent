<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const username = ref("admin");
const password = ref("Admin@123456");
const error = ref("");
const loading = ref(false);
const auth = useAuthStore();
const router = useRouter();

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    await auth.login(username.value, password.value);
    const redirect = router.currentRoute.value.query.redirect;
    router.replace(typeof redirect === "string" && redirect.startsWith("/") ? redirect : "/");
  } catch (err: any) {
    error.value = err.response?.data?.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <form class="card login-card" @submit.prevent="submit">
      <small style="color: var(--amber); letter-spacing: 0.3em">TRAFFIC SAFETY OS</small>
      <h1 class="display">夜巡上线<br />先把隐患闭环</h1>
      <div class="field">
        <label for="username">工号 / 用户名</label>
        <input id="username" v-model="username" autocomplete="username" />
      </div>
      <div class="field">
        <label for="password">密码</label>
        <input id="password" v-model="password" type="password" autocomplete="current-password" />
      </div>
      <p v-if="error" style="color: var(--signal)">{{ error }}</p>
      <button class="btn" :disabled="loading">{{ loading ? "正在核验..." : "进入指挥台" }}</button>
      <p style="color: var(--muted); margin-top: 18px; font-size: 13px">
        演示账号 admin / safety / worker，密码分别为 Admin@123456、Safety@123456、Worker@123456
      </p>
    </form>
  </div>
</template>
