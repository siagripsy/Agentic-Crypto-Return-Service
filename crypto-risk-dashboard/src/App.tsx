import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import ForecastPage from "./pages/ForecastPage";
import CryptoServicePage from "./pages/CryptoServicePage";
import LoginPage from "./pages/LoginPage";
import PortfolioPage from "./pages/PortfolioPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/crypto-service" replace />} />
          <Route path="crypto-service" element={<CryptoServicePage />} />
          <Route path="forecast" element={<ForecastPage />} />
          <Route path="portfolio" element={<PortfolioPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
