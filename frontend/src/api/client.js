import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api/v1";

const ACCESS_TOKEN_KEY = "shopshere_access";
const REFRESH_TOKEN_KEY = "shopshere_refresh";
const SESSION_ENDED_EVENT =
  "shopshere:session-ended";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    Accept: "application/json",
  },
});

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    Accept: "application/json",
  },
});

let refreshRequest = null;

apiClient.interceptors.request.use((config) => {
  const accessToken =
    sessionStorage.getItem(ACCESS_TOKEN_KEY);

  if (accessToken) {
    config.headers.Authorization =
      `Bearer ${accessToken}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    const refreshToken =
      sessionStorage.getItem(REFRESH_TOKEN_KEY);

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      !refreshToken ||
      originalRequest.url?.includes(
        "/auth/token/refresh/",
      )
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      refreshRequest ??= refreshClient
        .post("/auth/token/refresh/", {
          refresh: refreshToken,
        })
        .then(({ data }) => {
          sessionStorage.setItem(
            ACCESS_TOKEN_KEY,
            data.access,
          );

          if (data.refresh) {
            sessionStorage.setItem(
              REFRESH_TOKEN_KEY,
              data.refresh,
            );
          }

          return data.access;
        })
        .finally(() => {
          refreshRequest = null;
        });

      const accessToken = await refreshRequest;

      originalRequest.headers.Authorization =
        `Bearer ${accessToken}`;

      return apiClient(originalRequest);
    } catch (refreshError) {
      sessionStorage.removeItem(
        ACCESS_TOKEN_KEY,
      );

      sessionStorage.removeItem(
        REFRESH_TOKEN_KEY,
      );

      window.dispatchEvent(
        new Event(SESSION_ENDED_EVENT),
      );

      return Promise.reject(refreshError);
    }
  },
);

export default apiClient;