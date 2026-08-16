<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { http } from "../api/http";
import { useAuthStore } from "../stores/auth";
import { Bot, BookOpen, ClipboardCheck, LayoutDashboard, LogOut, Menu, SearchCheck, ShieldAlert, Users } from "lucide-vue-next";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const unread = ref(0);
const navigationOpen = ref(false);

const menus = [
  { to: "/", label: "AI 安全助手", icon: Bot },
  { to: "/hazards", label: "隐患提示", icon: ShieldAlert },
  { to: "/exams", label: "考试工坊", icon: ClipboardCheck },
  { to: "/knowledge", label: "知识库", icon: BookOpen, roles: ["Admin", "SafetyOfficer"] },
  { to: "/overview", label: "态势总览", icon: LayoutDashboard },
  { to: "/questions", label: "题库审核", icon: SearchCheck, roles: ["Admin", "SafetyOfficer"] },
  { to: "/users", label: "人员权限", icon: Users, roles: ["Admin"] },
];

const visibleMenus = computed(() => menus.filter((item) => !item.roles || item.roles.includes(auth.user?.role || "")));
const pageTitle = computed(() => String(route.meta.title || "安全生产指挥台"));

onMounted(async () => {
  try {
    const { data } = await http.get("/notifications/unread-count");
    unread.value = data.data.count;
  } catch {
    unread.value = 0;
  }
});

function logout() {
  auth.logout();
  router.push({ name: "login" });
}

function closeNavigation() {
  navigationOpen.value = false;
}
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="brand">
        <small>SHUDAO SAFETY</small>
        <strong class="display">蜀道安全助手</strong>
      </div>
      <nav class="primary-nav" aria-label="主功能导航">
        <router-link v-for="item in visibleMenus" :key="item.to" class="nav-link" :class="{ active: item.to === '/' ? route.path === '/' : route.path.startsWith(item.to) }" :to="item.to">
          <component :is="item.icon" :size="17" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="account-tools">
        <span>{{ auth.user?.name }} / {{ auth.user?.role }}</span>
        <button class="icon-btn" title="退出登录" aria-label="退出登录" @click="logout"><LogOut :size="18" /></button>
      </div>
      <button class="mobile-menu icon-btn" :aria-expanded="navigationOpen" aria-label="切换导航" @click="navigationOpen = !navigationOpen"><Menu :size="20" /></button>
    </header>
    <section class="main">
      <div class="topbar">
        <div>
          <div class="display topbar-title">{{ pageTitle }}</div>
          <div style="color: var(--muted)">未读消息 {{ unread }} · {{ auth.user?.project }}</div>
        </div>
      </div>
      <nav v-if="navigationOpen" class="mobile-nav" aria-label="移动端导航">
        <router-link v-for="item in visibleMenus" :key="item.to" :to="item.to" @click="closeNavigation">{{ item.label }}</router-link>
      </nav>
      <router-view />
    </section>
  </div>
</template>
