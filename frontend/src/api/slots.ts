import { apiClient } from "./client";
import type { Reservation } from "./types";

export async function rezervisiSlot(terminId: string, slotIndex: string) {
  const { data } = await apiClient.post(`/termini/${terminId}/slots/${slotIndex}/rezervisi`);
  return data;
}

export async function otkaziRezervaciju(terminId: string, slotIndex: string) {
  const { data } = await apiClient.delete(`/termini/${terminId}/slots/${slotIndex}/rezervacija`);
  return data;
}

export async function listMojeRezervacije() {
  const { data } = await apiClient.get<{ items: Reservation[]; count: number }>(
    "/me/rezervacije",
  );
  return data;
}
