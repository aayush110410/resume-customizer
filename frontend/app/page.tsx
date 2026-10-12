export default function Home() {
  return (
    <main className="mx-auto grid w-full max-w-7xl flex-1 gap-6 px-4 py-6 lg:grid-cols-[420px_1fr]">
      <section aria-label="Inputs" className="rounded-lg border p-4">
        <h1 className="text-xl font-semibold">Resume Customizer</h1>
      </section>
      <section aria-label="Results" className="rounded-lg border p-4" />
    </main>
  );
}
