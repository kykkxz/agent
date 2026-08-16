<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { http } from "../api/http";

const items = ref<any[]>([]);
const form = reactive({ username: "", name: "", password: "User@123456", role: "Employee", department: "", project: "成绵高速扩容项目" });

async function load() {
  items.value = (await http.get("/users")).data.data.items;
}
async function create() {
  await http.post("/users", form);
  await load();
}
onMounted(load);
</script>

<template>
  <div class="card">
    <h2 class="display">人员权限</h2>
    <div class="grid-3">
      <input v-model="form.username" placeholder="用户名" />
      <input v-model="form.name" placeholder="姓名" />
      <select v-model="form.role">
        <option>Employee</option>
        <option>SafetyOfficer</option>
        <option>Admin</option>
      </select>
    </div>
    <button class="btn" style="margin: 12px 0" @click="create">新增账号</button>
    <table class="table">
      <thead><tr><th>ID</th><th>姓名</th><th>角色</th><th>项目</th></tr></thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>{{ item.id }}</td>
          <td>{{ item.name }}</td>
          <td>{{ item.role }}</td>
          <td>{{ item.project }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>