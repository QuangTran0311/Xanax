import type { ReactNode } from "react";

import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import styles from "./TaskrunnerPage.module.css";

const c = (name: string) => styles[name] ?? name;

export function Modal({ open, title, children, onClose, wide = false }: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const tt = useTooltipText();
  if (!open) return null;
  return <div className={c("modal-overlay")} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className={`${c("modal-box")} ${wide ? c("modal-wide") : ""}`} role="dialog" aria-modal="true" aria-label={title}>
      <div className={c("modal-heading")}><div className={c("modal-title")}>{title}</div><Tooltip label={tt("tooltip.common.close_dialog")}><button className={c("editor-icon-btn")} onClick={onClose} aria-label={tt("tooltip.common.close_dialog")}>×</button></Tooltip></div>
      {children}
    </div>
  </div>;
}
