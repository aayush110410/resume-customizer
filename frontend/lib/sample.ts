// Fictional demo content (labelled as a sample in the UI). Pairs with public/samples/sample-resume.pdf.
export const SAMPLE_JD = `Backend Engineer (SDE-2) — Payments Platform
Location: Bengaluru, India (hybrid)

About us
We are a fast-growing fintech product company processing millions of UPI and card payments every day.

What you'll do
- Design, build and own Python and Java microservices for payment orchestration and reconciliation.
- Design clean REST APIs used by internal teams and merchants.
- Improve latency, reliability and observability of high-throughput services.
- Run services on Kubernetes on AWS; own CI/CD pipelines.
- Mentor junior engineers and review code.

Requirements
- 3+ years of backend development experience.
- Strong in Java (Spring Boot) or Python (Django/FastAPI).
- Solid SQL and data modelling (PostgreSQL or MySQL).
- Experience with Docker and Kubernetes.
- Experience with messaging systems such as Kafka.

Good to have
- Payments or banking domain experience.
- AWS certification.
- Experience with Redis and observability tools (Prometheus, Grafana).`;

export async function loadSampleResume(): Promise<File> {
  const res = await fetch("/samples/sample-resume.pdf");
  return new File([await res.blob()], "sample-resume-arjun-mehta.pdf", { type: "application/pdf" });
}
