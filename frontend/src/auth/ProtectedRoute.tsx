import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "./useAuth";

export function ProtectedRoute({
  children,
  requireRole,
}: {
  children: ReactNode;
  requireRole?: "student" | "profesor";
}) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner label="Učitavanje..." />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (requireRole && user.rola !== requireRole) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
