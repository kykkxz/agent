import { defineStore } from "pinia";
import { http } from "../api/http";

export interface UserInfo {
  id: string;
  username: string;
  name: string;
  role: string;
  department: string;
  project: string;
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("access_token") || "",
    user: JSON.parse(localStorage.getItem("user") || "null") as UserInfo | null,
  }),
  actions: {
    async login(username: string, password: string) {
      const { data } = await http.post("/auth/login", { username, password });
      this.token = data.data.access_token;
      this.user = data.data.user;
      localStorage.setItem("access_token", this.token);
      localStorage.setItem("user", JSON.stringify(this.user));
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
    },
  },
});