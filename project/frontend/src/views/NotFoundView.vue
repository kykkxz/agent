<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<template>
  <main class="empty-page">
    <div class="card empty-state">
      <p class="eyebrow">404</p>
      <h1 class="display">页面未找到</h1>
      <p>当前地址无法访问，或该功能尚未为您的角色开放。</p>
      <button class="btn" @click="router.push({ name: 'dashboard' })">返回态势总览</button>
    </div>
  </main>
</template>
