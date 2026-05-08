import { useContext } from "react";
import { AuthContext } from "./CognitoProvider";

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within CognitoProvider");
  }
  return ctx;
}
