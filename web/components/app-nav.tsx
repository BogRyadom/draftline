"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/app/dashboard", label: "Dashboard" },
  { href: "/app", label: "Inbox" },
  { href: "/app/knowledge", label: "Knowledge" },
  { href: "/app/audit", label: "Audit" },
  { href: "/app/settings", label: "Settings" },
];

export function AppNav() {
  const pathname = usePathname();
  return (
    <nav className="flex items-center gap-1 whitespace-nowrap">
      {links.map((link) => {
        const active =
          link.href === "/app"
            ? pathname === "/app"
            : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              active
                ? "bg-surface-2 text-ink"
                : "text-ink-soft hover:text-ink"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
