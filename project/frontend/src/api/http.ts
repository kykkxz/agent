import axios from "axios";

export const http = axios.create({
  baseURL: "/api/v1",
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      if (!location.hash.includes("/login")) {
        location.hash = "#/login";
      }
    }
    return Promise.reject(error);
  },
);