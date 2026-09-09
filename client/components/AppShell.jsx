"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";

function NavIcon({ path }) {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.7"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

const futureItems = [
  {
    label: "Galerie",
    path: "M3 16.5l5-5 4 4 3-3 6 6M5 5h14v14H5z",
  },
  {
    label: "Workflows",
    path: "M6 4v5m0 6v5m12-16v5m0 6v5M6 9h12v6H6z",
  },
  {
    label: "Connecteurs",
    path: "M8 12h8m-6-4v8m4-8v8M5 5h14v14H5z",
  },
];

export default function AppShell({ children }) {
  const params = useParams();
  const pathname = usePathname();
  const projectId = params?.projectId;
  const projectHref = projectId ? `/projects/${projectId}` : "/projects";
  const projectIsActive = pathname === "/projects" || Boolean(projectId);

  return (
    <div className="min-h-dvh bg-[#050505] text-zinc-100 md:flex">
      <aside className="border-b border-white/10 bg-zinc-950/95 md:sticky md:top-0 md:h-dvh md:w-60 md:shrink-0 md:border-r md:border-b-0">
        <div className="flex h-full flex-col">
          <Link
            href="/projects"
            className="flex items-center gap-3 px-5 py-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-focus"
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-accent shadow-[0_0_24px_rgba(97,92,80,0.3)]">
              <svg
                aria-hidden="true"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M7 4h10l3 5-8 11L4 9l3-5zm-3 5h16M9 4l3 16 3-16"
                />
              </svg>
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-wide text-white">
                Portrait Studio
              </span>
              <span className="block text-xs text-zinc-500">Production locale</span>
            </span>
          </Link>

          <nav
            aria-label="Navigation principale"
            className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:overflow-visible md:py-4"
          >
            <Link
              href={projectHref}
              aria-current={projectIsActive ? "page" : undefined}
              className="flex min-h-11 shrink-0 items-center gap-3 rounded-xl bg-accent/10 px-3 py-2.5 text-sm font-medium text-accent-soft ring-1 ring-inset ring-accent/20 transition-colors hover:bg-accent/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
            >
              <NavIcon path="M4 7.5L12 3l8 4.5V20H4V7.5zm5 12v-6h6v6" />
              Projet
            </Link>
            {futureItems.map((item) => (
              <span
                key={item.label}
                aria-disabled="true"
                title="Disponible dans un prochain lot"
                className="flex min-h-11 shrink-0 cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-600"
              >
                <NavIcon path={item.path} />
                {item.label}
              </span>
            ))}
          </nav>

          <p className="hidden px-5 py-5 text-xs leading-5 text-zinc-600 md:block">
            Les fichiers restent sur cette machine.
          </p>
        </div>
      </aside>

      <main className="relative min-w-0 flex-1 overflow-hidden">
        <div className="pointer-events-none absolute -top-32 right-0 h-96 w-96 rounded-full bg-accent/10 blur-[120px]" />
        <div className="relative mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 md:px-10 md:py-12">
          {children}
        </div>
      </main>
    </div>
  );
}
