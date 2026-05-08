import { apiClient } from "./client";
import type { Material, ProfMojiTermin, Slot, Termin } from "./types";

export async function listTermini(params?: { predmet?: string; datum?: string; status?: string }) {
  const { data } = await apiClient.get<{ items: Termin[]; count: number }>("/termini", { params });
  return data;
}

export async function getTermin(id: string) {
  const { data } = await apiClient.get<{
    termin: Termin;
    slots: Slot[];
    materials: Material[];
  }>(`/termini/${id}`);
  return data;
}

export async function createTermin(payload: {
  predmet: string;
  datum: string;
  vremeOd: string;
  vremeDo: string;
  trajanjeSlot?: number;
  maxStudenataPoSlotu?: number | null;
}) {
  const { data } = await apiClient.post<{
    terminId: string;
    status: string;
    brojSlotova: number;
    slots: Slot[];
  }>("/termini", payload);
  return data;
}

export async function updateTermin(
  id: string,
  payload: Partial<
    Pick<
      Termin,
      | "predmet"
      | "datum"
      | "vremeOd"
      | "vremeDo"
      | "description"
      | "maxStudenataPoSlotu"
    >
  >,
) {
  const { data } = await apiClient.patch(`/termini/${id}`, payload);
  return data;
}

export async function deleteTermin(id: string) {
  const { data } = await apiClient.delete(`/termini/${id}`);
  return data;
}

export async function objaviTermin(id: string) {
  const { data } = await apiClient.post(`/termini/${id}/objavi`);
  return data;
}

export async function listMojiTermini() {
  const { data } = await apiClient.get<{ items: ProfMojiTermin[]; count: number }>(
    "/me/termini",
  );
  return data;
}
