import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { hubText } from "./i18n";
import { useHub } from "./HubContext";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;

export function HubOverlays() {
  const { language } = useLanguage();
  const tooltip = useTooltipText();
  const { confirmState, answerConfirm } = useHub();
  return <>
    {confirmState ? <div className={c("modalBackdrop")} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) answerConfirm(false); }}>
      <div className={c("modalCard")} role="dialog" aria-modal="true" aria-label={hubText(language, "common.confirm")}>
        <Icon name="warning" size={28} />
        <p>{confirmState.message}</p>
        <div className={c("modalActions")}>
          <Tooltip label={tooltip("tooltip.common.confirm_cancel")}><button className={c("buttonGhost")} onClick={() => answerConfirm(false)}>{hubText(language, "common.cancel")}</button></Tooltip>
          <Tooltip label={tooltip("tooltip.common.confirm_accept")}><button data-testid="confirm-yes" className={c("buttonDanger")} onClick={() => answerConfirm(true)}>{hubText(language, "common.confirm")}</button></Tooltip>
        </div>
      </div>
    </div> : null}
  </>;
}
