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

const projectItems = [
  {
    label: "Galerie",
    suffix: "gallery",
    path: "M3 16.5l5-5 4 4 3-3 6 6M5 5h14v14H5z",
  },
  {
    label: "Workflows",
    suffix: "workflows",
    path: "M6 4v5m0 6v5m12-16v5m0 6v5M6 9h12v6H6z",
  },
];

const globalItems = [
  {
    label: "Connecteurs",
    href: "/connectors",
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
    <div className="min-h-dvh bg-[#282828] text-zinc-100 md:flex">
      <aside className="border-b border-white/10 bg-[#212121]/95 md:sticky md:top-0 md:h-dvh md:w-60 md:shrink-0 md:border-r md:border-b-0">
        <div className="flex h-full flex-col">
          <Link
            href="/projects"
            className="flex items-center gap-3 px-5 py-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-focus"
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-accent shadow-[0_0_24px_rgba(97,92,80,0.3)]">
              <svg
                aria-hidden="true"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 3v3m0-3h4m-4 3L4 11h16l-8-5zM5 11v9m14-9v9M3 20h18"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 20v-5a4 4 0 0 1 8 0v5M5 11c1.4 1.6 3.2 1.6 4.6 0 1.4 1.6 3.4 1.6 4.8 0 1.4 1.6 3.2 1.6 4.6 0M8 13h8"
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
            {projectItems.map((item) => {
              const href = projectId
                ? `/projects/${projectId}/${item.suffix}`
                : null;
              const active = href && pathname === href;
              if (!href) {
                return (
                  <span
                    key={item.label}
                    aria-disabled="true"
                    title="Ouvrez un projet pour acceder a cette section"
                    className="flex min-h-11 shrink-0 cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-600"
                  >
                    <NavIcon path={item.path} />
                    {item.label}
                  </span>
                );
              }
              return (
                <Link
                  key={item.label}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className="flex min-h-11 shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-400 transition-colors hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
                >
                  <NavIcon path={item.path} />
                  {item.label}
                </Link>
              );
            })}
            {globalItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                aria-current={pathname === item.href ? "page" : undefined}
                className="flex min-h-11 shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-400 transition-colors hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
              >
                <NavIcon path={item.path} />
                {item.label}
              </Link>
            ))}
          </nav>

          <p className="hidden px-5 py-5 text-xs leading-5 text-zinc-600 md:block">
            Les fichiers restent sur cette machine.
          </p>
        </div>
      </aside>

      <main className="relative min-w-0 flex-1 overflow-hidden">
        <div className="pointer-events-none absolute -top-32 right-0 h-96 w-96 rounded-full bg-accent/10 blur-[120px]" />
        <div className="relative w-full px-4 py-5 sm:px-6 md:px-8 md:py-5">
          {children}
        </div>
      </main>
    </div>
  );
}
