import { NavLink, Route, Routes } from "react-router-dom";
import SafetyBanner from "./components/SafetyBanner";
import PatientsPage from "./pages/PatientsPage";
import PatientDetailPage from "./pages/PatientDetailPage";
import GuidelineSearchPage from "./pages/GuidelineSearchPage";
import ObservabilityPage from "./pages/ObservabilityPage";
import ReviewQueuePage from "./pages/ReviewQueuePage";
import ReviewDetailPage from "./pages/ReviewDetailPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>FolioPrior Auth</h1>
        <nav className="app-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Patients
          </NavLink>
          <NavLink to="/review" className={({ isActive }) => (isActive ? "active" : "")}>
            Review Queue
          </NavLink>
          <NavLink to="/guidelines" className={({ isActive }) => (isActive ? "active" : "")}>
            Policy Search
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
            History
          </NavLink>
          <NavLink to="/observability" className={({ isActive }) => (isActive ? "active" : "")}>
            Observability
          </NavLink>
        </nav>
      </header>

      <SafetyBanner />

      <main className="app-main">
        <Routes>
          <Route path="/" element={<PatientsPage />} />
          <Route path="/patients/:id" element={<PatientDetailPage />} />
          <Route path="/review" element={<ReviewQueuePage />} />
          <Route path="/review/:runId" element={<ReviewDetailPage />} />
          <Route path="/guidelines" element={<GuidelineSearchPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/observability" element={<ObservabilityPage />} />
        </Routes>
      </main>
    </div>
  );
}
