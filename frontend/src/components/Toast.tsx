import { useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { STORAGE_KEYS } from "../store/keys";
import { Icon } from "./Icon";

export type ToastKind = "success" | "error" | "info";

interface ToastItem {
  id: number;
  kind: ToastKind;
  leaving: boolean;
  message: ReactNode;
}

interface ToastSnapshot {
  animations: boolean;
  items: ToastItem[];
}

interface ToastProps {
  "data-testid"?: string;
}

const TOAST_LIFETIME_MS = 2400;
const EXIT_DURATION_MS = 180;
const MAX_VISIBLE_TOASTS = 4;

const listeners = new Set<() => void>();
const lifetimeTimers = new Map<number, ReturnType<typeof setTimeout>>();
const exitTimers = new Map<number, ReturnType<typeof setTimeout>>();
let nextId = 0;

function storedAnimations(): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.localStorage.getItem(STORAGE_KEYS.animations) !== "0";
  } catch {
    return true;
  }
}

let snapshot: ToastSnapshot = { animations: storedAnimations(), items: [] };

function emit(next: ToastSnapshot): void {
  snapshot = next;
  listeners.forEach((listener) => listener());
}

function clearTimers(id: number): void {
  const lifetimeTimer = lifetimeTimers.get(id);
  if (lifetimeTimer !== undefined) clearTimeout(lifetimeTimer);
  lifetimeTimers.delete(id);

  const exitTimer = exitTimers.get(id);
  if (exitTimer !== undefined) clearTimeout(exitTimer);
  exitTimers.delete(id);
}

function removeToast(id: number): void {
  clearTimers(id);
  const items = snapshot.items.filter((item) => item.id !== id);
  if (items.length !== snapshot.items.length) emit({ ...snapshot, items });
}

function beginExit(id: number): void {
  lifetimeTimers.delete(id);
  const item = snapshot.items.find((candidate) => candidate.id === id);
  if (!item || item.leaving) return;

  if (!snapshot.animations) {
    removeToast(id);
    return;
  }

  emit({
    ...snapshot,
    items: snapshot.items.map((candidate) => candidate.id === id
      ? { ...candidate, leaving: true }
      : candidate),
  });
  exitTimers.set(id, setTimeout(() => removeToast(id), EXIT_DURATION_MS));
}

/** Đẩy thông báo vào hàng đợi chung; mọi trang dùng cùng thời gian sống và giới hạn. */
export function enqueueToast(message: ReactNode, kind: ToastKind = "info"): void {
  if (message === null || message === undefined || message === "") return;

  const item: ToastItem = { id: ++nextId, kind, leaving: false, message };
  const combined = [...snapshot.items, item];
  const items = combined.slice(-MAX_VISIBLE_TOASTS);

  // Khi quá giới hạn, bỏ ngay thông báo cũ nhất và huỷ cả hai timer của nó.
  combined.slice(0, Math.max(0, combined.length - MAX_VISIBLE_TOASTS))
    .forEach((dropped) => clearTimers(dropped.id));
  emit({ ...snapshot, items });
  lifetimeTimers.set(item.id, setTimeout(() => beginExit(item.id), TOAST_LIFETIME_MS));
}

/** Đồng bộ tuỳ chọn hiệu ứng của Hub với viewport được portal ra ngoài Hub. */
export function setToastAnimations(animations: boolean): void {
  if (snapshot.animations === animations) return;
  emit({ ...snapshot, animations });
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): ToastSnapshot {
  return snapshot;
}

/** Viewport duy nhất của hàng đợi toast, được gắn ở tầng App. */
export function Toast({ "data-testid": testId }: ToastProps = {}) {
  const current = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  if (!current.items.length || typeof document === "undefined") return null;

  return createPortal(
    <div className="toast-stack">
      {current.items.map((item) => {
        const iconName = item.kind === "success"
          ? "check"
          : item.kind === "error"
            ? "warning"
            : "info";
        return (
          <div
            key={item.id}
            className={`toast-notification toast-notification--${item.kind}${item.leaving ? " toast-notification--leaving" : ""}${current.animations ? "" : " toast-notification--no-animation"}`}
            role="status"
            data-testid={testId}
          >
            <Icon name={iconName} />
            <span>{item.message}</span>
          </div>
        );
      })}
    </div>,
    document.body,
  );
}
