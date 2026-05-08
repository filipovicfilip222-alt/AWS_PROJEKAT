import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GraduationCap, Sparkles, ShieldCheck, Calendar } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/useAuth";

const FEATURES = [
  {
    icon: Calendar,
    title: "Termini i slotovi",
    desc: "Pregled konsultacija po predmetu, atomska rezervacija slotova.",
  },
  {
    icon: Sparkles,
    title: "AI Tutor",
    desc: "Postavi pitanje pre dolaska — AI traži kroz odobrenu Q&A bazu.",
  },
  {
    icon: ShieldCheck,
    title: "Sigurno i privatno",
    desc: "Cognito autentikacija, JWT na API gateway-u.",
  },
];

export default function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      await signIn(email, password);
      navigate("/");
    } catch (e: unknown) {
      setErr((e as Error).message ?? "Neuspešna prijava");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left: branding */}
      <div className="relative hidden lg:flex flex-col justify-between p-10 bg-foreground text-background overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-[0.06]" />
        <div className="absolute -top-32 -left-20 h-96 w-96 rounded-full bg-accent/30 blur-3xl" />
        <div className="absolute -bottom-32 -right-20 h-96 w-96 rounded-full bg-primary/30 blur-3xl" />

        <div className="relative flex items-center gap-2 font-semibold">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-background text-foreground">
            <GraduationCap className="h-4 w-4" />
          </span>
          PredZnanje
        </div>

        <div className="relative space-y-6 max-w-md">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-background/10 border border-background/15 px-3 py-1 text-xs font-medium">
            <Sparkles className="h-3 w-3" />
            AI-powered student → profesor
          </div>
          <h2 className="font-display text-4xl leading-tight text-balance">
            Zakaži konsultacije i dobij brz odgovor pre dolaska.
          </h2>
          <p className="text-background/70 text-base leading-relaxed">
            Sistem sa AI tutorom koji ti pomaže pre i posle konsultacija. Profesor
            objavljuje termine, ti rezervišeš slot, a AI je tu kad treba dodatno
            pojašnjenje.
          </p>
          <div className="grid gap-3 pt-2">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="flex items-start gap-3 rounded-lg bg-background/5 border border-background/10 p-3"
              >
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-background/10">
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <div className="text-sm font-semibold">{title}</div>
                  <div className="text-xs text-background/60 leading-relaxed">
                    {desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-xs text-background/50">
          AWS · CDK · Bedrock Claude Haiku · DynamoDB
        </div>
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center px-6 py-12 lg:px-12">
        <div className="w-full max-w-sm space-y-8">
          <div className="lg:hidden flex items-center gap-2 font-semibold">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-foreground text-background">
              <GraduationCap className="h-4 w-4" />
            </span>
            PredZnanje
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight">Dobrodošao nazad</h1>
            <p className="text-sm text-muted-foreground">
              Uloguj se sa email-om koji si registrovao na fakultetu.
            </p>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="ime.prezime@fakultet.rs"
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
                autoComplete="current-password"
                placeholder="••••••••"
              />
            </div>
            {err && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {err}
              </div>
            )}
            <Button type="submit" className="w-full" size="lg" disabled={loading}>
              {loading ? "Prijava..." : "Prijavi se"}
            </Button>
          </form>

          <div className="text-center text-sm text-muted-foreground">
            Nemaš nalog?{" "}
            <Link to="/register" className="text-foreground font-medium hover:underline">
              Registruj se
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
