import { Icon } from "../../components/Icon";
import { useLanguage } from "../../store/language";
import { hubText } from "./i18n";
import { useHub } from "./HubContext";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;

export function HubOverlays() {
  const { language } = useLanguage();
  const { confirmState, answerConfirm, toastState } = useHub();
  return <>
    {confirmState ? <div className={c("modalBackdrop")} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) answerConfirm(false); }}>
      <div className={c("modalCard")} role="dialog" aria-modal="true" aria-label={hubText(language, "common.confirm")}>
        <Icon name="warning" size={28} />
        <p>{confirmState.message}</p>
        <div className={c("modalActions")}>
          <button className={c("buttonGhost")} onClick={() => answerConfirm(false)}>{hubText(language, "common.cancel")}</button>
          <button data-testid="confirm-yes" className={c("buttonDanger")} onClick={() => answerConfirm(true)}>{hubText(language, "common.confirm")}</button>
        </div>
      </div>
    </div> : null}
    {toastState ? <div className={`${c("toast")} ${c(toastState.kind)}`} role="status">
      <Icon name={toastState.kind === "success" ? "check" : toastState.kind === "error" ? "warning" : "info"} size={18} />
      {toastState.message}
    </div> : null}
  </>;
}
