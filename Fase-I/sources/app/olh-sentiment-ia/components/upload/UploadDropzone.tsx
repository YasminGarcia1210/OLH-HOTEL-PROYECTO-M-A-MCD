"use client";

import { useCallback, useRef, useState } from "react";

import type { ArchivoUploadData } from "@/lib/upload-api";
import { uploadArchivo } from "@/lib/upload-api";

const MAX_BYTES = 50 * 1024 * 1024;
const ACCEPT =
  ".csv,.json,.txt,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

type UploadPhase = "idle" | "uploading" | "success" | "error";

type UploadDropzoneProps = {
  title: string;
  formatsLine: string;
  browseButtonLabel: string;
  onUploadSuccess?: (data: ArchivoUploadData) => void;
};

function truncateHash(hash: string, head = 8, tail = 6): string {
  if (hash.length <= head + tail + 1) return hash;
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`;
}

export function UploadDropzone({
  title,
  formatsLine,
  browseButtonLabel,
  onUploadSuccess,
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [successData, setSuccessData] = useState<ArchivoUploadData | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resetInput = () => {
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      const file = files[0];
      if (file.size > MAX_BYTES) {
        setPhase("error");
        setErrorMessage(
          "El archivo supera el tamaño máximo permitido (50 MB).",
        );
        setSuccessData(null);
        resetInput();
        return;
      }

      setPhase("uploading");
      setErrorMessage(null);
      setSuccessData(null);

      const result = await uploadArchivo(file);

      if (result.ok && result.data) {
        setPhase("success");
        setSuccessData(result.data);
        onUploadSuccess?.(result.data);
      } else {
        setPhase("error");
        setSuccessData(null);
        const code = result.error?.codigo ?? "";
        const msg = result.error?.mensaje ?? "No se pudo completar la subida.";
        if (code === "ARCHIVO_YA_SUBIDO") {
          setErrorMessage(msg);
        } else if (
          code === "ARCHIVO_DEMASIADO_GRANDE" ||
          msg.toLowerCase().includes("tamaño")
        ) {
          setErrorMessage(
            result.error?.mensaje ??
              "El archivo supera el tamaño máximo permitido.",
          );
        } else {
          setErrorMessage(msg);
        }
      }
      resetInput();
    },
    [onUploadSuccess],
  );

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    void handleFiles(e.dataTransfer.files);
  };

  const busy = phase === "uploading";

  return (
    <div className="group relative cursor-pointer">
      <input
        ref={inputRef}
        type="file"
        className="sr-only"
        accept={ACCEPT}
        disabled={busy}
        aria-label={browseButtonLabel}
        onChange={(e) => void handleFiles(e.target.files)}
      />
      <div
        className="absolute -inset-1 rounded-xl bg-gradient-to-r from-primary/20 to-tertiary/20 opacity-25 blur transition duration-1000 group-hover:opacity-50"
        aria-hidden
      />
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !busy && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (busy) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={busy ? -1 : 0}
        className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed bg-surface-container-low p-16 text-center transition-all duration-300 ease-in-out group-hover:border-primary/50 group-hover:bg-surface-container ${
          isDragging
            ? "border-primary bg-surface-container shadow-[0_0_24px_rgba(212,168,71,0.15)]"
            : "border-outline-variant/30"
        } ${busy ? "pointer-events-none opacity-70" : ""}`}
      >
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-surface-container-highest transition-transform group-hover:scale-110">
          <span className="material-symbols-outlined text-3xl text-primary">
            cloud_upload
          </span>
        </div>
        <h3 className="mb-2 text-xl font-semibold">{title}</h3>
        <p className="mb-8 font-label text-xs uppercase tracking-widest text-on-surface/40">
          {formatsLine}
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={(e) => {
            e.stopPropagation();
            inputRef.current?.click();
          }}
          className="rounded-md border border-outline-variant/50 bg-surface-container-highest px-8 py-3 font-label text-[0.6875rem] uppercase tracking-widest transition-all duration-300 ease-in-out hover:bg-primary hover:text-on-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          {browseButtonLabel}
        </button>

        {phase === "uploading" && (
          <p className="mt-6 font-label text-sm text-primary" role="status">
            Subiendo…
          </p>
        )}
        {phase === "success" && successData && (
          <div
            className="mt-6 max-w-md space-y-1 text-left text-sm text-tertiary"
            role="status"
          >
            <p className="font-medium text-on-surface">
              Archivo subido correctamente
            </p>
            <p className="break-all text-on-surface/70">
              <span className="text-on-surface/50">Blob: </span>
              {successData.blob_path}
            </p>
            <p className="font-mono text-xs text-on-surface/60">
              SHA-256: {truncateHash(successData.hash)}
            </p>
          </div>
        )}
        {phase === "error" && errorMessage && (
          <p
            className="mt-6 max-w-md text-center text-sm text-error"
            role="alert"
          >
            {errorMessage}
          </p>
        )}
      </div>
    </div>
  );
}
