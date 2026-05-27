import { BrowserRouter } from "react-router-dom";
import AppRoute from "./router/AppRoute";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { useInactivityTimer } from "./features/cocina/hooks/useInactivityTimer";


function InactivityTimer({children}: {children: React.ReactNode}) {
  useInactivityTimer();
  return <>{children}</>;
}

const App = () => {
  // D7 — Auto-logout por inactividad, excluyendo /cocina.

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <InactivityTimer>
          <AppRoute/>
        </InactivityTimer>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

export default App;