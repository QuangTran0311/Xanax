import { useNavigate } from "react-router-dom";

import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { sessionApi } from "../../store/session";
import { useTheme } from "../../store/theme";
import { useHub } from "./HubContext";
import { hubText } from "./i18n";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;

export function SettingsPage() {
  const navigate = useNavigate(); const { theme, setTheme } = useTheme(); const { language, setLanguage } = useLanguage();
  const tooltip = useTooltipText();
  const { username, sidebarCompact, setSidebarCompact, animations, setAnimations } = useHub();
  return <div className={c("page")}>
    <header className={c("pageHeader")}><div><h1>{hubText(language, "settings.title")}</h1><p>{hubText(language, "settings.subtitle")}</p></div></header>
    <section className={c("settingsGrid")}>
      <article className={c("settingsCard")}><h2><Icon name="sun" />{hubText(language, "settings.appearance")}</h2><div className={c("choiceGrid")}><Tooltip label={tooltip("tooltip.settings.theme_light")}><button data-testid="theme-light" className={theme === "light" ? c("choiceSelected") : c("choice")} onClick={() => setTheme("light")}><span className={c("themePreviewLight")} /><Icon name="sun" />{hubText(language, "settings.light")}</button></Tooltip><Tooltip label={tooltip("tooltip.settings.theme_dark")}><button data-testid="theme-dark" className={theme === "dark" ? c("choiceSelected") : c("choice")} onClick={() => setTheme("dark")}><span className={c("themePreviewDark")} /><Icon name="moon" />{hubText(language, "settings.dark")}</button></Tooltip></div></article>
      <article className={c("settingsCard")}><h2><Icon name="globe" />{hubText(language, "settings.language")}</h2><div className={c("segmented")}><Tooltip label={tooltip("tooltip.settings.language_vi")}><button data-testid="language-vi" className={language === "vi" ? c("selected") : ""} onClick={() => setLanguage("vi")}>Tiếng Việt</button></Tooltip><Tooltip label={tooltip("tooltip.settings.language_en")}><button data-testid="language-en" className={language === "en" ? c("selected") : ""} onClick={() => setLanguage("en")}>English</button></Tooltip></div></article>
      <article className={c("settingsCard")}><h2><Icon name="sliders" />{hubText(language, "settings.interface")}</h2><Toggle label={hubText(language, "settings.compact")} checked={sidebarCompact} onChange={setSidebarCompact} /><Toggle label={hubText(language, "settings.animations")} checked={animations} onChange={setAnimations} /></article>
      <article className={c("settingsCard")}><h2><Icon name="lock" />{hubText(language, "settings.session")}</h2><p>{language === "vi" ? `Đăng nhập: ${username}` : `Signed in: ${username}`}</p><Tooltip label={tooltip("tooltip.common.logout")}><button className={c("buttonDanger")} onClick={() => void sessionApi.logout().finally(() => navigate("/login", { replace: true }))}>{hubText(language, "common.logout")}</button></Tooltip></article>
      <article className={`${c("settingsCard")} ${c("settingsWide")}`}><h2><Icon name="info" />{hubText(language, "settings.about")}</h2><p>{hubText(language, "settings.about_text")}</p><small>Xanax Hub · React migration GĐ4</small></article>
    </section>
  </div>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) { return <label className={c("toggleRow")}><span>{label}</span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><i /></label>; }
