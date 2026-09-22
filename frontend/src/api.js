const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

// Turns any failed call into an Error whose .message says exactly what went
// wrong — the registration forms show it word for word in their error popup.
//   .status   HTTP status (0 when the request never reached a server)
//   .details  the JSON body when there was one ({ message, errors })
//   .network  true when the browser could not connect at all
function describeFailure(res, data, text) {
  if (data && data.message) return data.message;
  const snippet = (text || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 160);
  const by = {
    413: "The files you attached are too large for the server (HTTP 413). Please use smaller images — under 8 MB each.",
    404: `The API address is wrong or the endpoint is missing (HTTP 404 at ${res.url}).`,
    429: "Too many attempts from this connection. Please wait a few minutes and try again (HTTP 429).",
    500: "The server hit an error while saving (HTTP 500).",
    502: "The server is not reachable right now (HTTP 502 Bad Gateway) — the backend may be restarting. Please try again in a minute.",
    503: "The server is temporarily unavailable (HTTP 503). Please try again in a minute.",
    504: "The server took too long to answer (HTTP 504). Please try again.",
  };
  const base = by[res.status] || `The server refused the request (HTTP ${res.status} ${res.statusText || ""}).`.replace(/\s+\)/, ")");
  return snippet && !by[res.status] ? `${base} ${snippet}` : base;
}

async function send(path, init) {
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
  } catch (e) {
    const error = new Error(
      `Could not reach the server at ${BASE_URL} — check your internet connection, or the backend is down / blocked by the browser (${e && e.message ? e.message : "network error"}).`
    );
    error.status = 0;
    error.network = true;
    error.details = null;
    throw error;
  }

  let data = null;
  let text = "";
  try {
    text = await res.text();
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    // non-JSON response (an HTML error page from a proxy, an empty body)
  }

  if (!res.ok) {
    const error = new Error(describeFailure(res, data, text));
    error.status = res.status;
    error.details = data;
    throw error;
  }

  return data;
}

async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return send(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
}

// Like request(), but sends a FormData body (multipart/form-data) instead of
// JSON — used for the exhibitor registration form, which may include a logo
// file. Never set Content-Type manually here: the browser needs to add its
// own multipart boundary.
async function requestForm(path, { method = "POST", formData, token } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  return send(path, { method, headers, body: formData });
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

// Uploaded files (venue map, logos, product images) come from the API as
// "/uploads/…" paths. They are served by the backend under the API base too
// (…/api/uploads/…), which is the only path some hosts (Emergent) forward to
// the backend — so every file link is built through BASE_URL.
export function fileUrl(path) {
  if (!path) return "";
  if (/^(https?:)?\/\//i.test(path) || path.startsWith("data:") || path.startsWith("blob:")) return path;
  return `${BASE_URL.replace(/\/$/, "")}${path.startsWith("/") ? "" : "/"}${path}`;
}

export const api = {
  baseUrl: BASE_URL,
  fileUrl,
  getConfig: () => request("/public/config"),
  getStalls: (packageCode) => request(`/public/stalls${packageCode ? `?packageCode=${encodeURIComponent(packageCode)}` : ""}`),
  getStallMap: () => request("/public/stall-map"),
  getStallDirectory: () => request("/public/stall-directory"),
  getExhibitorLogos: () => request("/public/exhibitor-logos"),
  registerExhibitor: (payload) => requestForm("/exhibitors/register", { formData: toFormData(payload) }),
  holdStall: (stallNumber, previousToken) =>
    request(`/public/stalls/${encodeURIComponent(stallNumber)}/hold`, { method: "POST", body: { previousToken: previousToken || null } }),
  releaseStallHold: (holdToken) => request("/public/stalls/release-hold", { method: "POST", body: { holdToken } }),
  registerVisitor: (payload) => request("/visitors/register", { method: "POST", body: payload }),
  submitEnquiry: (payload) => request("/enquiries", { method: "POST", body: payload }),
  adminLogin: (payload) => request("/admin/login", { method: "POST", body: payload }),
  adminStats: (token) => request("/admin/stats", { token }),
  adminExhibitors: (token, params = "") => request(`/admin/exhibitors${params}`, { token }),
  adminVisitors: (token, params = "") => request(`/admin/visitors${params}`, { token }),
  adminCheckIn: (token, registrationCode) =>
    request("/admin/check-in", { method: "POST", body: { registrationCode }, token }),
  adminEntranceQR: (token) => request("/admin/visitors/entrance-qr", { token }),
  adminApproveExhibitor: (token, id, paymentStatus) => request(`/admin/exhibitors/${id}/approve`, { method: "POST", body: { paymentStatus }, token }),
  adminSetPayment: (token, id, paymentStatus) => request(`/admin/exhibitors/${id}/payment`, { method: "PATCH", body: { paymentStatus }, token }),
  adminChangePassword: (token, payload) => request("/admin/me/password", { method: "POST", body: payload, token }),
  adminResetAdminPassword: (token, id, payload) => request(`/admin/admins/${id}/password`, { method: "POST", body: payload, token }),
  adminRejectExhibitor: (token, id) => request(`/admin/exhibitors/${id}/reject`, { method: "POST", token }),
  adminReopenExhibitor: (token, id) => request(`/admin/exhibitors/${id}/reopen`, { method: "POST", token }),
  adminSendPaymentReminder: (token, id) => request(`/admin/exhibitors/${id}/payment-reminder`, { method: "POST", token }),
  adminGetExhibitor: (token, id) => request(`/admin/exhibitors/${id}`, { token }),
  adminGetVisitor: (token, id) => request(`/admin/visitors/${id}`, { token }),
  adminGetEnquiry: (token, id) => request(`/admin/enquiries/${id}`, { token }),
  adminEditExhibitor: (token, id, payload) => request(`/admin/exhibitors/${id}`, { method: "PATCH", body: payload, token }),
  adminBookStall: (token, payload) => requestForm("/admin/exhibitors/book", { formData: toFormData(payload), token }),
  adminDeleteExhibitor: (token, id) => request(`/admin/exhibitors/${id}`, { method: "DELETE", token }),
  adminEditVisitor: (token, id, payload) => request(`/admin/visitors/${id}`, { method: "PATCH", body: payload, token }),
  adminDeleteVisitor: (token, id) => request(`/admin/visitors/${id}`, { method: "DELETE", token }),
  adminInvoiceUrl: (id) => `${BASE_URL}/admin/exhibitors/${id}/invoice`,
  exportUrl: (kind) => `${BASE_URL}/admin/${kind}/export`,
  adminListAdmins: (token) => request("/admin/admins", { token }),
  adminCreateAdmin: (token, payload) => request("/admin/admins", { method: "POST", body: payload, token }),
  adminDeleteAdmin: (token, id) => request(`/admin/admins/${id}`, { method: "DELETE", token }),
  adminEnquiries: (token, params = "") => request(`/admin/enquiries${params}`, { token }),
  // `payload` may carry { status } and/or edited fields { name, email, mobile, details }
  adminUpdateEnquiry: (token, id, payload) =>
    request(`/admin/enquiries/${id}`, { method: "PATCH", body: payload, token }),
  adminDeleteEnquiry: (token, id) => request(`/admin/enquiries/${id}`, { method: "DELETE", token }),
  adminListStalls: (token) => request("/admin/stalls", { token }),
  adminCreateStalls: (token, stalls) => request("/admin/stalls", { method: "POST", body: { stalls }, token }),
  adminUpdateStall: (token, id, payload) => request(`/admin/stalls/${id}`, { method: "PATCH", body: payload, token }),
  adminDeleteStall: (token, id) => request(`/admin/stalls/${id}`, { method: "DELETE", token }),
  // `file` may be an image or a PDF (first page is rendered server-side);
  // `series` is an optional [{ prefix, packageCode, separator }] mapping.
  adminUploadStallMap: (token, file, series) => {
    const fd = new FormData();
    fd.append("map", file);
    if (series) fd.append("series", JSON.stringify(series));
    return requestForm("/admin/stalls/upload-map", { formData: fd, token });
  },
  adminSaveMapSeries: (token, series) => request("/admin/stalls/map-series", { method: "PUT", body: { series }, token }),
  adminDetectLayout: (token) => request("/admin/stalls/detect-layout", { method: "POST", token }),
  adminDetectionStatus: (token) => request("/admin/stalls/detection", { token }),
  adminApplyBundledLayout: (token, keepOld = false) =>
    request("/admin/stalls/apply-bundled-layout", { method: "POST", body: { keepOld }, token }),
  // stalls: [{ stallNumber, packageCode, mapX, mapY }] — creates/updates them with positions
  adminApplyLayout: (token, series, stalls) =>
    request("/admin/stalls/apply-layout", { method: "POST", body: { series, stalls }, token }),
  adminGenerateStallsFromSeries: (token, counts = {}) =>
    request("/admin/stalls/generate-from-series", { method: "POST", body: { counts }, token }),
  adminWaGetConfig: (token) => request("/admin/whatsapp/config", { token }),
  adminWaSaveConfig: (token, payload) => request("/admin/whatsapp/config", { method: "PUT", body: payload, token }),
  adminWaTemplates: (token) => request("/admin/whatsapp/templates", { token }),
  adminWaSaveTemplate: (token, key, payload) => request(`/admin/whatsapp/templates/${key}`, { method: "PUT", body: payload, token }),
  adminWaLogs: (token, params = "") => request(`/admin/whatsapp/logs${params}`, { token }),
  adminWaTest: (token, payload) => request("/admin/whatsapp/test", { method: "POST", body: payload, token }),
  adminWaBroadcast: (token, payload) => request("/admin/whatsapp/broadcast", { method: "POST", body: payload, token }),
};

export { BASE_URL };
