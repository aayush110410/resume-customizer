const MESSAGES: Record<string, string> = {
  INVALID_FILE_TYPE: "That file isn't a PDF or DOCX. Please upload your resume as a PDF or Word document.",
  FILE_TOO_LARGE: "That file is larger than 5 MB. Please upload a smaller PDF or DOCX.",
  TOO_MANY_PAGES: "Resumes longer than 5 pages aren't supported. Please trim it and try again.",
  ENCRYPTED_PDF: "This PDF is password-protected. Please export an unlocked copy.",
  SCANNED_PDF: "This PDF looks like a scanned image with no selectable text. Please upload a text-based PDF or DOCX.",
  EMPTY_FILE: "The uploaded file is empty.",
  CORRUPT_FILE: "We couldn't read this file. It may be damaged; try re-exporting it.",
  JD_TOO_SHORT: "The job description is too short. Paste the full posting (at least 300 characters).",
  JD_TOO_LONG: "The job description is too long (over 20,000 characters). Paste just the role details.",
  NOT_A_JD: "This doesn't look like a job description, so results may be unreliable.",
  RATE_LIMITED: "You've hit the hourly limit for this free demo. Please try again later.",
  LLM_UNAVAILABLE: "All AI providers are busy right now. Your inputs are kept, so try again in a moment.",
  LLM_BAD_OUTPUT: "The AI returned an unusable answer. Please try again.",
  INVALID_EXPORT: "There's nothing to export yet.",
  NETWORK: "Couldn't reach the analysis server. Check your connection and try again.",
  INTERNAL: "Something went wrong on our side. Please try again.",
};

export function messageFor(code: string): string {
  return MESSAGES[code] ?? MESSAGES.INTERNAL;
}
