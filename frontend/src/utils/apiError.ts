interface ApiErrorShape {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
  message?: string;
}

function formatDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map(item => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter(Boolean);
    return messages.length ? messages.join("; ") : null;
  }
  return null;
}

export function formatApiError(err: unknown, fallback: string): string {
  if (!err || typeof err !== "object") return fallback;
  const shaped = err as ApiErrorShape;
  return formatDetail(shaped.response?.data?.detail) || shaped.message || fallback;
}
