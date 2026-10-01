import apiClient from "./client";

export async function login(credentials) {
  const { data } = await apiClient.post("/auth/login/", credentials);
  return data;
}

export async function authenticateWithGoogle(credential) {
  const { data } = await apiClient.post("/auth/google/", {
    credential,
  });
  return data;
}

export async function logout(refresh) {
  await apiClient.post("/auth/logout/", {
    refresh,
  });
}

export async function getProfile() {
  const { data } = await apiClient.get("/account/profile/");
  return data;
}

export async function updateProfile(payload) {
  const { data } = await apiClient.patch(
    "/account/profile/",
    payload,
  );
  return data;
}

export async function changePassword(payload) {
  const { data } = await apiClient.post(
    "/auth/password/change/",
    payload,
  );
  return data;
}

export async function setGooglePassword(payload) {
  const { data } = await apiClient.post(
    "/auth/google/password/set/",
    payload,
  );
  return data;
}

export async function startRegistration(email) {
  const { data } = await apiClient.post("/auth/register/start/", {
    email,
  });
  return data;
}

export async function verifyRegistration(payload) {
  const { data } = await apiClient.post(
    "/auth/register/verify/",
    payload,
  );
  return data;
}

export async function completeRegistration(payload) {
  const { data } = await apiClient.post(
    "/auth/register/complete/",
    payload,
  );
  return data;
}

export async function requestPasswordReset(email) {
  const { data } = await apiClient.post("/auth/password/reset/", {
    email,
  });
  return data;
}

export async function confirmPasswordReset(payload) {
  const { data } = await apiClient.post(
    "/auth/password/reset/confirm/",
    payload,
  );
  return data;
}