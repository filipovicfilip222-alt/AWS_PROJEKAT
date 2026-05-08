import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { BookOpen, GraduationCap, LogOut, Menu, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/useAuth";
import { cn } from "@/utils/cn";

interface NavItem {
  to: string;
  label: string;
  featured?: boolean;
}

const studentNav: NavItem[] = [
  { to: "/student", label: "Početna" },
  { to: "/student/termini", label: "Termini" },
  { to: "/student/pitaj", label: "Pitaj pre zakazivanja", featured: true },
  { to: "/student/rezervacije", label: "Moje rezervacije" },
];

const profesorNav: NavItem[] = [
  { to: "/profesor", label: "Početna" },
  { to: "/profesor/termini", label: "Moji termini" },
  { to: "/profesor/rezimei", label: "Rezimei" },
  { to: "/profesor/termini/novi", label: "Kreiraj termin" },
];

export function Layout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isProfesor = user?.rola === "profesor";
  const nav = isProfesor ? profesorNav : studentNav;

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const initials =
    `${user?.ime?.[0] ?? ""}${user?.prezime?.[0] ?? ""}`.toUpperCase() || "?";

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-foreground text-background shadow-sm">
              {isProfesor ? (
                <BookOpen className="h-4 w-4" />
              ) : (
                <GraduationCap className="h-4 w-4" />
              )}
            </span>
            <span className="text-base tracking-tight">PredZnanje</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1 ml-2">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  cn(
                    "inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    item.featured
                      ? isActive
                        ? "bg-accent text-accent-foreground shadow-sm"
                        : "text-accent hover:bg-accent-muted"
                      : isActive
                        ? "bg-foreground text-background shadow-sm"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                {item.featured ? (
                  <span className="font-display-italic-clean text-[0.95rem]">
                    &ldquo;PitajPreZakazivanja&rdquo;
                  </span>
                ) : (
                  item.label
                )}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2.5 rounded-full border border-border bg-card px-2 py-1 pr-3 shadow-sm">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-accent text-accent-foreground text-xs font-semibold">
                {initials}
              </span>
              <div className="flex flex-col leading-tight">
                <span className="text-xs font-medium">
                  {user?.ime} {user?.prezime}
                </span>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {isProfesor ? "Profesor" : "Student"}
                </span>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="hidden sm:inline-flex"
              onClick={async () => {
                await signOut();
                navigate("/login");
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden lg:inline">Izloguj se</span>
            </Button>
            <button
              type="button"
              className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-md border border-border bg-card text-foreground"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Meni"
            >
              {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Mobile drawer */}
        {mobileOpen && (
          <div className="md:hidden border-t border-border/70 bg-background">
            <div className="container py-3 flex flex-col gap-1">
              <div className="flex items-center gap-2 px-1 pb-3 mb-2 border-b border-border/60">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-accent text-accent-foreground text-xs font-semibold">
                  {initials}
                </span>
                <div className="flex flex-col leading-tight">
                  <span className="text-sm font-medium">
                    {user?.ime} {user?.prezime}
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    {isProfesor ? "Profesor" : "Student"}
                  </span>
                </div>
              </div>
              {nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  className={({ isActive }) =>
                    cn(
                      "inline-flex items-center rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                      item.featured
                        ? isActive
                          ? "bg-accent text-accent-foreground"
                          : "text-accent hover:bg-accent-muted"
                        : isActive
                          ? "bg-foreground text-background"
                          : "text-foreground hover:bg-muted",
                    )
                  }
                >
                  {item.featured ? (
                    <span className="font-display-italic-clean text-base">
                      &ldquo;PitajPreZakazivanja&rdquo;
                    </span>
                  ) : (
                    item.label
                  )}
                </NavLink>
              ))}
              <button
                type="button"
                onClick={async () => {
                  await signOut();
                  navigate("/login");
                }}
                className="mt-2 inline-flex items-center gap-2 rounded-md px-3 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/10"
              >
                <LogOut className="h-4 w-4" />
                Izloguj se
              </button>
            </div>
          </div>
        )}
      </header>
      <main className="container flex-1 py-6 sm:py-8">
        <Outlet />
      </main>
      <footer className="border-t border-border/70 py-4 text-center text-xs text-muted-foreground">
        PredZnanje — V4
      </footer>
    </div>
  );
}
