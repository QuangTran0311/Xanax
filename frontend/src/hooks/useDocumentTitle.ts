import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { useLanguage } from "../store/language";
import { hubText, type HubMessageKey } from "../pages/hub/i18n";
import { hubNavigation } from "../pages/hub/navigation";

function hubRouteLabel(pathname: string): HubMessageKey | undefined {
  const [, root, routeTab] = pathname.split("/");
  if (root !== "hub") return undefined;
  const tab = routeTab || "home";
  return hubNavigation.find((item) => item.tab === tab)?.label;
}

export function useDocumentTitle(): void {
  const { pathname } = useLocation();
  const { language } = useLanguage();

  useEffect(() => {
    if (pathname === "/login") {
      document.title = "Xanax — Đăng nhập";
      return;
    }

    const label = hubRouteLabel(pathname)
      ?? (pathname === "/workspace" ? "nav.train" : undefined)
      ?? (pathname === "/taskrunner" || pathname.startsWith("/taskrunner/")
        ? "nav.automation"
        : undefined);
    document.title = label ? `${hubText(language, label)} · Xanax` : "Xanax";
  }, [language, pathname]);
}
