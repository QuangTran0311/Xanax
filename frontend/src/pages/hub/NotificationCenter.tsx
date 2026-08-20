import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useLanguage } from "../../store/language";
import { useHub } from "./HubContext";
import { notificationBody, notificationKindLabel } from "./notifications";
import type { NotificationRecord } from "./types";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;

function formatNotificationTime(value: string, locale: string): string {
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value.replace(" ", "T")}Z`);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString(locale, { dateStyle: "short", timeStyle: "short" });
}

function suggestionsOf(notification: NotificationRecord): Array<Record<string, unknown>> {
  return Array.isArray(notification.payload.suggestions)
    ? notification.payload.suggestions.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}

export function NotificationCenter() {
  const { language } = useLanguage();
  const vi = language === "vi";
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const {
    notifications, unreadNotificationCount, selectedNotification,
    openNotification, closeNotification, markNotificationRead,
    markAllNotificationsRead, resolveNotification,
    setCurrentProjectId, setCurrentProjectSubtab,
  } = useHub();

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);

  useEffect(() => {
    if (!selectedNotification) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeNotification();
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [closeNotification, selectedNotification]);

  const selectNotification = (notification: NotificationRecord) => {
    openNotification(notification);
    setOpen(false);
  };

  const action = () => {
    if (!selectedNotification?.link.startsWith("/hub")) return;
    if (selectedNotification.source_type === "work_item") {
      const projectId = Number(selectedNotification.payload.project_id || 0);
      if (projectId) setCurrentProjectId(projectId);
      setCurrentProjectSubtab("work");
    }
    navigate(selectedNotification.link);
    closeNotification();
  };

  const suggestions = selectedNotification ? suggestionsOf(selectedNotification) : [];

  return (
    <>
      <div className={c("notificationMenu")} ref={rootRef}>
        <Tooltip label={vi ? "Trung tâm thông báo" : "Notification center"}>
          <button
            className={c("topbarIconButton")}
            type="button"
            aria-label={vi ? "Mở trung tâm thông báo" : "Open notification center"}
            aria-haspopup="menu"
            aria-expanded={open}
            onClick={() => setOpen((current) => !current)}
          >
            <Icon name="bell" />
            {unreadNotificationCount > 0 && (
              <span className={c("notificationBadge")}>
                {unreadNotificationCount > 99 ? "99+" : unreadNotificationCount}
              </span>
            )}
          </button>
        </Tooltip>
        {open && (
          <div className={c("notificationDropdown")} role="menu">
            <header>
              <div>
                <strong>{vi ? "Thông báo" : "Notifications"}</strong>
                <small>{vi ? `${unreadNotificationCount} chưa đọc` : `${unreadNotificationCount} unread`}</small>
              </div>
              {unreadNotificationCount > 0 && (
                <button type="button" onClick={() => void markAllNotificationsRead()}>
                  {vi ? "Đọc tất cả" : "Mark all read"}
                </button>
              )}
            </header>
            <div className={c("notificationList")}>
              {notifications.length ? notifications.map((notification) => (
                <button
                  key={notification.id}
                  type="button"
                  role="menuitem"
                  className={`${c("notificationRow")} ${notification.status === "unread" ? c("notificationUnread") : ""}`}
                  onClick={() => selectNotification(notification)}
                >
                  <span className={`${c("notificationDot")} ${c(`notification${notification.severity}`)}`} />
                  <span>
                    <strong>{notification.title}</strong>
                    <small>{notificationKindLabel(notification, language)}</small>
                    <time>{formatNotificationTime(notification.created_at, vi ? "vi-VN" : "en-US")}</time>
                  </span>
                </button>
              )) : (
                <p className={c("notificationEmpty")}>
                  {vi ? "Chưa có thông báo." : "No notifications yet."}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {selectedNotification && (
        <div className={c("modalBackdrop")} role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeNotification();
        }}>
          <article className={`${c("modalCard")} ${c("notificationDetail")}`} role="dialog" aria-modal="true" aria-labelledby="notification-detail-title">
            <header>
              <span className={`${c("notificationDetailIcon")} ${c(`notification${selectedNotification.severity}`)}`}>
                <Icon name={selectedNotification.severity === "error" ? "warning" : "bell"} />
              </span>
              <div>
                <small>{notificationKindLabel(selectedNotification, language)}</small>
                <h2 id="notification-detail-title">{selectedNotification.title}</h2>
              </div>
              <button type="button" className={c("notificationClose")} onClick={closeNotification} aria-label={vi ? "Đóng" : "Close"}>
                <Icon name="close" />
              </button>
            </header>
            <p className={c("notificationBody")}>{notificationBody(selectedNotification, language)}</p>
            {suggestions.length > 0 && (
              <section className={c("notificationSuggestions")}>
                <h3>{vi ? "Gợi ý nhân viên" : "Suggested employees"}</h3>
                {suggestions.map((suggestion, index) => (
                  <article key={String(suggestion.agent_id ?? index)}>
                    <div>
                      <strong>{String(suggestion.agent_name || (vi ? "Nhân viên AI" : "AI employee"))}</strong>
                      <small>{String(suggestion.agent_role || suggestion.reason || "")}</small>
                    </div>
                    <span>{Number(suggestion.score || 0).toLocaleString(vi ? "vi-VN" : "en-US", { maximumFractionDigits: 1 })}%</span>
                  </article>
                ))}
              </section>
            )}
            <footer className={c("modalActions")}>
              {selectedNotification.status === "unread" && (
                <button className={c("buttonGhost")} type="button" onClick={() => void markNotificationRead(selectedNotification.id)}>
                  <Icon name="check" />{vi ? "Đánh dấu đã đọc" : "Mark as read"}
                </button>
              )}
              {selectedNotification.status !== "resolved" && (
                <button className={c("buttonGhost")} type="button" onClick={() => void resolveNotification(selectedNotification.id)}>
                  {vi ? "Đã xử lý" : "Resolve"}
                </button>
              )}
              {selectedNotification.link.startsWith("/hub") && (
                <button className={c("primaryButton")} type="button" onClick={action}>
                  {vi ? "Mở nguồn" : "Open source"}<Icon name="arrowRight" />
                </button>
              )}
            </footer>
          </article>
        </div>
      )}
    </>
  );
}
