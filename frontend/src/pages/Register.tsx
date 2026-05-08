import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, GraduationCap, Mail, ShieldCheck, UserRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/useAuth";
import { cn } from "@/utils/cn";

const PASSWORD_RULES = [
  { test: (p: string) => p.length >= 8, label: "Min 8 karaktera" },
  { test: (p: string) => /[A-Z]/.test(p), label: "Bar 1 veliko slovo" },
  { test: (p: string) => /[0-9]/.test(p), label: "Bar 1 broj" },
];

export default function Register() {
  const { signUp, confirm, signIn, resend } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<"form" | "confirm">("form");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [ime, setIme] = useState("");
  const [prezime, setPrezime] = useState("");
  const [rola, setRola] = useState<"student" | "profesor">("student");
  const [code, setCode] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const { confirmRequired } = await signUp({ email, password, ime, prezime, rola });
      if (confirmRequired) {
        setStep("confirm");
      } else {
        await signIn(email, password);
        navigate("/");
      }
    } catch (e: unknown) {
      setErr((e as Error).message ?? "Greška pri registraciji");
    } finally {
      setLoading(false);
    }
  };

  const onConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      await confirm(email, code);
      await signIn(email, password);
      navigate("/");
    } catch (e: unknown) {
      setErr((e as Error).message ?? "Pogrešan kod");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-background">
      <div className="w-full max-w-md space-y-8">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-foreground text-background">
            <GraduationCap className="h-4 w-4" />
          </span>
          PredZnanje
        </Link>

        <div className="rounded-2xl border border-border bg-card shadow-card p-6 sm:p-8 space-y-6">
          <div className="space-y-1.5">
            <h1 className="text-2xl font-semibold tracking-tight">
              {step === "form" ? "Napravi nalog" : "Potvrdi email"}
            </h1>
            <p className="text-sm text-muted-foreground">
              {step === "form"
                ? "Popuni osnovne podatke i izaberi ulogu."
                : `Unesi 6-cifreni kod koji smo poslali na ${email}.`}
            </p>
          </div>

          {step === "form" ? (
            <form onSubmit={onSignUp} className="space-y-5">
              {/* Section 1: Profile */}
              <FormSection
                icon={<UserRound className="h-3.5 w-3.5" />}
                title="Profil"
              >
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="ime">Ime</Label>
                    <Input
                      id="ime"
                      value={ime}
                      onChange={(e) => setIme(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="prezime">Prezime</Label>
                    <Input
                      id="prezime"
                      value={prezime}
                      onChange={(e) => setPrezime(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Uloga</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {(["student", "profesor"] as const).map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setRola(r)}
                        className={cn(
                          "flex flex-col items-start gap-0.5 rounded-md border px-3 py-2.5 text-left transition-all",
                          rola === r
                            ? "border-foreground bg-foreground text-background shadow-sm"
                            : "border-border bg-card hover:border-foreground/40",
                        )}
                      >
                        <span className="text-sm font-medium">
                          {r === "student" ? "Student" : "Profesor"}
                        </span>
                        <span
                          className={cn(
                            "text-[11px]",
                            rola === r
                              ? "text-background/70"
                              : "text-muted-foreground",
                          )}
                        >
                          {r === "student"
                            ? "Rezervi\u0161e slotove"
                            : "Objavljuje termine"}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </FormSection>

              {/* Section 2: Account */}
              <FormSection
                icon={<Mail className="h-3.5 w-3.5" />}
                title="Pristup"
              >
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password">Lozinka</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                  <ul className="flex flex-wrap gap-2 pt-1">
                    {PASSWORD_RULES.map((rule) => {
                      const ok = rule.test(password);
                      return (
                        <li
                          key={rule.label}
                          className={cn(
                            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]",
                            ok
                              ? "border-success/30 bg-success/10 text-success"
                              : "border-border bg-card text-muted-foreground",
                          )}
                        >
                          {ok && <Check className="h-3 w-3" />}
                          {rule.label}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              </FormSection>

              {err && (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {err}
                </div>
              )}
              <Button type="submit" className="w-full" size="lg" disabled={loading}>
                {loading ? "Registracija..." : "Registruj se"}
              </Button>
            </form>
          ) : (
            <form onSubmit={onConfirm} className="space-y-4">
              <div className="rounded-md border border-info/30 bg-info/10 px-3 py-2 text-sm text-info flex items-start gap-2">
                <ShieldCheck className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  Ako ne vidiš email, proveri spam i sačekaj minut. Možeš zatražiti
                  novi kod ispod.
                </span>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="code">Kod za potvrdu</Label>
                <Input
                  id="code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                  inputMode="numeric"
                  className="text-center text-lg tracking-[0.4em] font-mono"
                  placeholder="------"
                  maxLength={10}
                />
              </div>
              {err && (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {err}
                </div>
              )}
              <Button type="submit" className="w-full" size="lg" disabled={loading}>
                {loading ? "Potvrda..." : "Potvrdi i prijavi se"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="w-full"
                onClick={() => resend(email).catch(() => null)}
              >
                Pošalji kod ponovo
              </Button>
            </form>
          )}
        </div>

        <div className="text-center text-sm text-muted-foreground">
          Već imaš nalog?{" "}
          <Link to="/login" className="text-foreground font-medium hover:underline">
            Prijavi se
          </Link>
        </div>
      </div>
    </div>
  );
}

function FormSection({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-muted">
          {icon}
        </span>
        {title}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}
