/** Ultimo segmento de una ruta (compat. separadores Windows/Unix). */
export function basename(path: string): string {
  const i = path.replace(/\\/g, "/").lastIndexOf("/");
  return i === -1 ? path : path.slice(i + 1);
}
