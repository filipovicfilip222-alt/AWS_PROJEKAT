import { apiClient } from "./client";
import type { Material } from "./types";

interface UploadUrlResponse {
  materialId: string;
  url: string;
  fields: Record<string, string>;
  key: string;
  bucket: string;
  maxSizeBytes: number;
}

export async function getUploadUrl(
  terminId: string,
  payload: { fileName: string; fileType: "pdf" | "pptx" | "image"; sizeBytes: number },
) {
  const { data } = await apiClient.post<UploadUrlResponse>(
    `/termini/${terminId}/materials/upload-url`,
    payload,
  );
  return data;
}

export async function listMaterials(terminId: string) {
  const { data } = await apiClient.get<{ items: Material[]; count: number }>(
    `/termini/${terminId}/materials`,
  );
  return data;
}

export async function deleteMaterial(terminId: string, materialId: string) {
  const { data } = await apiClient.delete(`/termini/${terminId}/materials/${materialId}`);
  return data;
}

export async function uploadFileToS3(
  url: string,
  fields: Record<string, string>,
  file: File,
  onProgress?: (pct: number) => void,
) {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  fd.append("file", file);

  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable && onProgress) {
        onProgress(Math.round((ev.loaded / ev.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`S3 upload failed with status ${xhr.status}: ${xhr.responseText}`));
    };
    xhr.onerror = () => reject(new Error("Mrežna greška pri upload-u"));
    xhr.send(fd);
  });
}
