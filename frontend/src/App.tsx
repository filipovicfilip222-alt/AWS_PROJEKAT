import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { Layout } from "@/components/common/Layout";
import { useAuth } from "@/auth/useAuth";

import Login from "@/pages/Login";
import Register from "@/pages/Register";
import StudentDashboard from "@/pages/student/Dashboard";
import BrowseTermini from "@/pages/student/BrowseTermini";
import PitajPreZakazivanja from "@/pages/student/PitajPreZakazivanja";
import MojeRezervacije from "@/pages/student/MojeRezervacije";
import TerminDetails from "@/pages/TerminDetails";
import ProfesorDashboard from "@/pages/profesor/Dashboard";
import KreirajTermin from "@/pages/profesor/KreirajTermin";
import UrediTermin from "@/pages/profesor/UrediTermin";
import ApprovePitanja from "@/pages/profesor/ApprovePitanja";
import MojiTermini from "@/pages/profesor/MojiTermini";
import Rezime from "@/pages/profesor/Rezime";
import Rezimei from "@/pages/profesor/Rezimei";

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.rola === "profesor" ? "/profesor" : "/student"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomeRedirect />} />

        <Route path="/student" element={<StudentDashboard />} />
        <Route path="/student/termini" element={<BrowseTermini />} />
        <Route path="/student/pitaj" element={<PitajPreZakazivanja />} />
        <Route path="/student/rezervacije" element={<MojeRezervacije />} />

        <Route path="/profesor" element={<ProfesorDashboard />} />
        <Route path="/profesor/termini" element={<MojiTermini />} />
        <Route path="/profesor/rezimei" element={<Rezimei />} />
        <Route path="/profesor/termini/novi" element={<KreirajTermin />} />
        <Route path="/profesor/termini/:id/uredi" element={<UrediTermin />} />
        <Route path="/profesor/termini/:id/pitanja" element={<ApprovePitanja />} />
        <Route path="/profesor/termini/:id/rezime" element={<Rezime />} />

        <Route path="/termini/:id" element={<TerminDetails />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
