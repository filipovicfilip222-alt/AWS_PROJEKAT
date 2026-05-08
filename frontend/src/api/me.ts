import { apiClient } from "./client";

export interface MeProfile {
  sub: string;
  email: string;
  ime: string;
  prezime: string;
  rola: "student" | "profesor";
  predmeti?: string[];
  createdAt?: string;
}

export async function getMe() {
  const { data } = await apiClient.get<MeProfile>("/me");
  return data;
}
