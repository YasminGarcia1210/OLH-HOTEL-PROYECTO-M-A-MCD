"use client";

import { useCallback, useState } from "react";

import { ArchivosEntradaPanels } from "@/components/upload/ArchivosEntradaPanels";
import { UploadDropzone } from "@/components/upload/UploadDropzone";
import { uploadDropzoneCopy, uploadHero } from "@/lib/upload-mock";

export function UploadPageContent() {
  const [entradaKey, setEntradaKey] = useState(0);

  const onUploadSuccess = useCallback(() => {
    setEntradaKey((k) => k + 1);
  }, []);

  return (
    <>
      <div className="mx-auto max-w-6xl space-y-12 p-8 lg:p-12">
        <section>
          <h1 className="font-headline mb-2 text-4xl font-bold text-on-background">
            {uploadHero.title}
          </h1>
          <p className="max-w-2xl text-lg text-on-surface/60">
            {uploadHero.subtitle}
          </p>
        </section>

        <UploadDropzone
          title={uploadDropzoneCopy.title}
          formatsLine={uploadDropzoneCopy.formatsLine}
          browseButtonLabel={uploadDropzoneCopy.browseButton}
          onUploadSuccess={onUploadSuccess}
        />

        <section className="space-y-6">
          <h2 className="font-headline text-2xl text-on-background">
            Subidas recientes
          </h2>
          <ArchivosEntradaPanels key={entradaKey} />
        </section>
      </div>
    </>
  );
}
