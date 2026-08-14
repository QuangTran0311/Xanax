import { AppRoutes } from "./routes";
import { Toast } from "./components/Toast";
import { LanguageProvider } from "./store/language";
import { ThemeProvider } from "./store/theme";

export function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppRoutes />
        <Toast />
      </LanguageProvider>
    </ThemeProvider>
  );
}
