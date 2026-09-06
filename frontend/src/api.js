const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    // non-JSON response (e.g. CSV download handled separately)
  }

  if (!res.ok) {
    const message = (data && data.message) || `Request failed with status ${res.status}`;
    const error = new Error(message);
    error.details = data;
    throw error;
  }

  return data;
}

// Like request(), but sends a FormData body (multipart/form-data) instead of
// JSON — used for the exhibitor registration form, which may include a logo
// file. Never set Content-Type manually here: the browser needs to add its
// own multipart boundary.
async function requestForm(path, { method = "POST", formData, token } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { method, headers, body: formData });

  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    // non-JSON response
  }

  if (!res.ok) {
    const message = (data && data.message) || `Request failed with status ${res.status}`;
    const error = new Error(message);
    error.details = data;
    throw error;
  }

  return data;
}

function toFormData(payload) {
  const fd = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (key === "logo" && value instanceof File) {
      fd.append("logo", value);
    } else if (key === "productImages" && Array.isArray(value)) {
      value.forEach((file) => {
        if (file instanceof File) fd.append("productImages", file);
      });
    } else if (typeof value !== "object") {
      fd.append(key, value);
    }
  });
  return fd;
}

export const api = {
  getConfig: () => request("/public/config"),
  getStalls: (packageCode) => request(`/public/stalls${packageCode ? `?packageCode=${encodeURIComponent(packageCode)}` : ""}`),
  getStallMap: () => request("/public/stall-map"),
  registerExhibitor: (payload) => requestForm("/exhibitors/register", { formData: toFormData(payload) }),
  registerVisitor: (payload) => request("/visitors/register", { method: "POST", body: payload }),
  adminLogin: (payload) => request("/admin/login", { method: "POST", body: payload }),
  adminStats: (token) => request("/admin/stats", { token }),
  adminExhibitors: (token, params = "") => request(`/admin/exhibitors${params}`, { token }),
  adminVisitors: (token, params = "") => request(`/admin/visitors${params}`, { token }),
  adminCheckIn: (token, registrationCode) =>
    request("/admin/check-in", { method: "POST", body: { registrationCode }, token }),
  adminEntranceQR: (token) => request("/admin/visitors/entrance-qr", { token }),
  adminApproveExhibitor: (token, id) => request(`/admin/exhibitors/${id}/approve`, { method: "POST", token }),
  adminRejectExhibitor: (token, id) => request(`/admin/exhibitors/${id}/reject`, { method: "POST", token }),
  adminEditExhibitor: (token, id, payload) => request(`/admin/exhibitors/${id}`, { method: "PATCH", body: payload, token }),
  adminInvoiceUrl: (id) => `${BASE_URL}/admin/exhibitors/${id}/invoice`,
  exportUrl: (kind) => `${BASE_URL}/admin/${kind}/export`,
  adminListAdmins: (token) => request("/admin/admins", { token }),
  adminCreateAdmin: (token, payload) => request("/admin/admins", { method: "POST", body: payload, token }),
  adminDeleteAdmin: (token, id) => request(`/admin/admins/${id}`, { method: "DELETE", token }),
  adminListStalls: (token) => request("/admin/stalls", { token }),
  adminCreateStalls: (token, stalls) => request("/admin/stalls", { method: "POST", body: { stalls }, token }),
  adminUpdateStall: (token, id, payload) => request(`/admin/stalls/${id}`, { method: "PATCH", body: payload, token }),
  adminDeleteStall: (token, id) => request(`/admin/stalls/${id}`, { method: "DELETE", token }),
  adminUploadStallMap: (token, file) => {
    const fd = new FormData();
    fd.append("map", file);
    return requestForm("/admin/stalls/upload-map", { formData: fd, token });
  },
};

export { BASE_URL };
