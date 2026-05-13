import { BrowserRouter } from "react-router-dom";
import AppRoute from "./router/AppRoute";
import { ErrorBoundary } from "./components/common/ErrorBoundary";

const App = () => {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppRoute/>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

export default App;