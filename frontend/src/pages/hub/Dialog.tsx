import { useEffect } from "react";

import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;

export function Dialog({ title, children, onClose, wide = false }: { title: string; children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  const tooltip = useTooltipText();
  // Đóng hộp thoại bằng ESC để thống nhất thao tác trên toàn bộ giao diện.
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return <div className={c("modalBackdrop")} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className={`${c("dialog")} ${wide ? c("dialogWide") : ""}`} role="dialog" aria-modal="true" aria-label={title}>
      <header><h2>{title}</h2><Tooltip label={tooltip("tooltip.common.close_dialog")}><button type="button" aria-label={tooltip("tooltip.common.close_dialog")} onClick={onClose}><Icon name="close" /></button></Tooltip></header>
      <div className={c("dialogBody")}>{children}</div>
    </section>
  </div>;
}
