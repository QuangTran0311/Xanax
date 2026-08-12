import { Icon } from "../../components/Icon";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;

export function Dialog({ title, children, onClose, wide = false }: { title: string; children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  return <div className={c("modalBackdrop")} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className={`${c("dialog")} ${wide ? c("dialogWide") : ""}`} role="dialog" aria-modal="true" aria-label={title}>
      <header><h2>{title}</h2><button type="button" onClick={onClose}><Icon name="close" /></button></header>
      <div className={c("dialogBody")}>{children}</div>
    </section>
  </div>;
}
