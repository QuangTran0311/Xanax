import { AppRoutes } from "./routes";
import { LanguageProvider } from "./store/language";
import { ThemeProvider } from "./store/theme";

export function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppRoutes />
      </LanguageProvider>
    </ThemeProvider>
  );
}
