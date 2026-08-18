import { AppRoutes } from "./routes";
import { Toast } from "./components/Toast";
import { useDocumentTitle } from "./hooks/useDocumentTitle";
import { LanguageProvider } from "./store/language";
import { ThemeProvider } from "./store/theme";

function AppContent() {
  useDocumentTitle();
  return (
    <>
      <AppRoutes />
      <Toast />
    </>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppContent />
      </LanguageProvider>
    </ThemeProvider>
  );
}
