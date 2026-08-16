import { createRouter, createWebHashHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

type UserRole = "Admin" | "SafetyOfficer" | "Employee";

const router = createRouter({
  history: createWebHashHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/login", name: "login", component: () => import("../views/LoginView.vue"), meta: { title: "登录" } },
    {
      path: "/",
      component: () => import("../layouts/AppShell.vue"),
      children: [
        { path: "", name: "ai", component: () => import("../views/AiChatView.vue"), meta: { title: "AI 安全助手" } },
        { path: "overview", name: "dashboard", component: () => import("../views/DashboardView.vue"), meta: { title: "态势总览" } },
        { path: "hazards", name: "hazards", component: () => import("../views/HazardListView.vue"), meta: { title: "隐患提示" } },
        { path: "hazards/create", name: "hazard-create", component: () => import("../views/HazardCreateView.vue"), meta: { title: "上报隐患" } },
        { path: "hazards/:id", name: "hazard-detail", component: () => import("../views/HazardDetailView.vue"), meta: { title: "隐患详情" } },
        { path: "ai", redirect: "/" },
        { path: "exams", name: "exams", component: () => import("../views/ExamListView.vue"), meta: { title: "考试工坊" } },
        { path: "exams/take/:paperId", name: "exam-take", component: () => import("../views/ExamTakeView.vue"), meta: { title: "在线考试" } },
        { path: "exams/result/:attemptId", name: "exam-result", component: () => import("../views/ExamResultView.vue"), meta: { title: "考试结果" } },
        { path: "questions", name: "questions", component: () => import("../views/QuestionBankView.vue"), meta: { title: "题库审核", roles: ["Admin", "SafetyOfficer"] satisfies UserRole[] } },
        { path: "knowledge", name: "knowledge", component: () => import("../views/KnowledgeView.vue"), meta: { title: "知识库", roles: ["Admin", "SafetyOfficer"] satisfies UserRole[] } },
        { path: "users", name: "users", component: () => import("../views/UsersView.vue"), meta: { title: "人员权限", roles: ["Admin"] satisfies UserRole[] } },
      ],
    },
    { path: "/:pathMatch(.*)*", name: "not-found", component: () => import("../views/NotFoundView.vue"), meta: { title: "页面未找到" } },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.name !== "login" && !auth.token) return { name: "login", query: { redirect: to.fullPath } };
  if (to.name === "login" && auth.token) return { name: "ai" };
  const allowedRoles = to.meta.roles as UserRole[] | undefined;
  if (allowedRoles && (!auth.user || !allowedRoles.includes(auth.user.role as UserRole))) {
    return { name: "ai" };
  }
  return true;
});

router.afterEach((to) => {
  document.title = `${to.meta.title || "蜀道安全助手"} | 蜀道安全助手`;
});

export default router;
