import { BrowserRouter } from "react-router-dom";
import AppRoute from "./router/AppRoute";

const App = () => {
  return (
    <BrowserRouter>
      <AppRoute/>
    </BrowserRouter>
  );
};

export default App;