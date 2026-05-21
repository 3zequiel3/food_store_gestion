import { BrowserRouter } from "react-router-dom";
import AppRoute from "./router/AppRoute";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { useInactivityTimer } from "./features/cocina/hooks/useInactivityTimer";

const App = () => {
  // D7 — Auto-logout por inactividad, excluyendo /cocina.
  useInactivityTimer();

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppRoute/>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

export default App;