"""S3 helper za pre-signed URL-ove i čitanje materijala."""
from __future__ import annotations

import os
from typing import Literal

import boto3
from botocore.config import Config

MATERIALS_BUCKET = os.environ.get("MATERIALS_BUCKET", "")
PRESIGN_TTL_SECONDS = int(os.environ.get("PRESIGN_TTL_SECONDS", "300"))  # 5 min
# AWS_REGION je uvek postavljen u Lambda runtime-u; fallback na eu-central-1 za lokalni dev.
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "eu-central-1"

# NAPOMENA: forsiramo regional endpoint i virtual-host addressing. Bez ovoga
# boto3 generate_presigned_post zna da padne na legacy global host
# (`bucket.s3.amazonaws.com` umesto `bucket.s3.<region>.amazonaws.com`),
# pa S3 u eu-central-1 vrati 500 bez CORS header-a → browser javi
# "CORS Missing Allow Origin" iako bucket CORS jeste ispravno postavljen.
_s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com",
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
    ),
)

ContentType = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image": "image/png",  # default, overridden by client
}


def material_key(termin_id: str, material_id: str, file_name: str) -> str:
    return f"materials/{termin_id}/{material_id}/{file_name}"


def presign_put(key: str, *, content_type: str, max_size_bytes: int) -> dict:
    """Vraća pre-signed POST sa policy-jem koji limitira veličinu."""
    return _s3.generate_presigned_post(
        Bucket=MATERIALS_BUCKET,
        Key=key,
        Conditions=[
            ["content-length-range", 1, max_size_bytes],
            {"Content-Type": content_type},
        ],
        Fields={"Content-Type": content_type},
        ExpiresIn=PRESIGN_TTL_SECONDS,
    )


def get_object_bytes(bucket: str, key: str) -> bytes:
    res = _s3.get_object(Bucket=bucket, Key=key)
    return res["Body"].read()


def get_object_text(bucket: str, key: str, *, max_chars: int | None = None) -> str | None:
    """V3: učitaj UTF-8 text iz S3; vrati None ako ne postoji.

    Koristi se za `extracted.txt` materijala (RAG kontekst za AI tutora).
    Ostale greške se propagiraju kao boto3 exceptions.
    """
    try:
        res = _s3.get_object(Bucket=bucket, Key=key)
    except _s3.exceptions.NoSuchKey:
        return None
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "NotFound"):
            return None
        raise
    body = res["Body"].read().decode("utf-8", errors="replace")
    if max_chars is not None and len(body) > max_chars:
        return body[:max_chars]
    return body


def put_object_text(bucket: str, key: str, text: str, *, content_type: str = "text/plain; charset=utf-8") -> None:
    """V3: snimi UTF-8 text u S3 (npr. `extracted.txt`)."""
    _s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=text.encode("utf-8"),
        ContentType=content_type,
    )


def delete_object(bucket: str, key: str) -> None:
    _s3.delete_object(Bucket=bucket, Key=key)


def detect_file_type(key: str) -> Literal["pdf", "pptx", "image"]:
    lower = key.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".pptx"):
        return "pptx"
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return "image"
    raise ValueError(f"Unsupported file type for key: {key}")
