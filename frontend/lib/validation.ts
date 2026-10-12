export const LIMITS = { jdMin: 300, jdMax: 20000, maxBytes: 5 * 1024 * 1024 };
const OK_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];

export function validateInputs({ jd, file }: { jd: string; file: File | null }): { jd?: string; file?: string } {
  const errors: { jd?: string; file?: string } = {};
  const n = jd.trim().length;
  if (n < LIMITS.jdMin) errors.jd = `Paste the full job description — at least 300 characters (now ${n}).`;
  else if (n > LIMITS.jdMax) errors.jd = "That's over 20,000 characters. Paste just the role details.";
  if (!file) errors.file = "Upload your resume as a PDF or DOCX.";
  else if (!OK_TYPES.includes(file.type) && !/\.(pdf|docx)$/i.test(file.name)) errors.file = "Upload a PDF or DOCX file.";
  else if (file.size > LIMITS.maxBytes) errors.file = "This file is larger than 5 MB.";
  return errors;
}

export function formatBytes(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
