# frontend/CLAUDE.md

> Lokalna pravila za React frontend.
> Root pravila: `/CLAUDE.md`. Ova pravila imaju prioritet u frontend kontekstu.

---

## 1. Stack

- React 18 + Vite + TypeScript (strict)
- Routing: `react-router-dom` v6
- Data fetching: `@tanstack/react-query` v5
- Auth: `aws-amplify` v6 (Cognito)
- UI: Tailwind CSS + Radix UI primitives + custom komponente
- State (klijent-side): React state + Context (Zustand opciono ako treba globalno)
- HTTP: Axios sa interceptor-om (Cognito JWT)

---

## 2. Folder struktura

```
frontend/src/
├── api/                   # API client funkcije (jedan fajl po domain-u)
│   ├── client.ts          # Axios instance + JWT interceptor
│   ├── feedback.ts        # V2
│   ├── materials.ts
│   ├── questions.ts
│   ├── rezime.ts          # V2
│   ├── search.ts
│   ├── slots.ts
│   └── termini.ts
├── auth/
│   ├── CognitoProvider.tsx
│   ├── ProtectedRoute.tsx
│   └── useAuth.ts
├── components/
│   ├── common/            # Button, Input, Modal, Spinner...
│   ├── feedback/          # V2: FeedbackButtons, QuestionDetailModal
│   ├── question/
│   ├── rezime/            # V2: RezimeInsights
│   ├── slot/              # V2: SlotCard sa "Pridruži se"
│   ├── termin/
│   └── upload/
├── pages/
│   ├── Login.tsx
│   ├── Register.tsx
│   ├── student/
│   │   ├── Dashboard.tsx
│   │   ├── BrowseTermini.tsx
│   │   ├── PitajPreZakazivanja.tsx  # uses QuestionDetailModal
│   │   └── MojeRezervacije.tsx
│   └── profesor/
│       ├── Dashboard.tsx
│       ├── KreirajTermin.tsx
│       ├── UrediTermin.tsx
│       ├── ApprovePitanja.tsx
│       ├── MojiTermini.tsx
│       └── RezimeKonsultacija.tsx   # V2
├── hooks/                 # custom hookovi (useFeedback, useTermini...)
├── store/                 # globalni state (ako treba)
├── styles/                # Tailwind config + globalne stilove
├── types/                 # TypeScript types/interfaces
├── utils/                 # helpers (formatDate, parseError...)
├── App.tsx
└── main.tsx
```

---

## 3. API client pattern

### 3.1 Jedan fajl po domain-u

```typescript
// api/feedback.ts
import { client } from "./client";

export interface FeedbackResponse {
  vote: "yes" | "no" | null;
  updatedAt?: string;
}

export async function submitFeedback(
  questionId: string,
  vote: "yes" | "no"
): Promise<{ vote: "yes" | "no" }> {
  const { data } = await client.post(
    `/questions/${questionId}/feedback`,
    { vote }
  );
  return data;
}

export async function getMyFeedback(
  questionId: string
): Promise<FeedbackResponse> {
  const { data } = await client.get(`/questions/${questionId}/feedback/me`);
  return data;
}
```

### 3.2 React Query integracija

```typescript
// hooks/useFeedback.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { submitFeedback, getMyFeedback } from "@/api/feedback";

export function useMyFeedback(questionId: string) {
  return useQuery({
    queryKey: ["feedback", questionId, "me"],
    queryFn: () => getMyFeedback(questionId),
    staleTime: 60_000
  });
}

export function useSubmitFeedback(questionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vote: "yes" | "no") => submitFeedback(questionId, vote),
    onMutate: async (vote) => {
      // Optimistic update
      await qc.cancelQueries({ queryKey: ["feedback", questionId, "me"] });
      const prev = qc.getQueryData(["feedback", questionId, "me"]);
      qc.setQueryData(["feedback", questionId, "me"], { vote });
      return { prev };
    },
    onError: (_err, _vote, ctx) => {
      // Rollback
      qc.setQueryData(["feedback", questionId, "me"], ctx?.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["feedback", questionId, "me"] });
    }
  });
}
```

---

## 4. Routing

### Konvencija routes

```typescript
// App.tsx
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  
  <Route element={<ProtectedRoute />}>
    <Route path="/" element={<RoleRedirect />} />
    
    {/* Student */}
    <Route path="/student" element={<StudentDashboard />} />
    <Route path="/student/termini" element={<BrowseTermini />} />
    <Route path="/student/pitaj" element={<PitajPreZakazivanja />} />
    <Route path="/student/rezervacije" element={<MojeRezervacije />} />
    
    {/* Profesor */}
    <Route path="/profesor" element={<ProfesorDashboard />} />
    <Route path="/profesor/termini" element={<MojiTermini />} />
    <Route path="/profesor/termini/novi" element={<KreirajTermin />} />
    <Route path="/profesor/termini/:id/uredi" element={<UrediTermin />} />
    <Route path="/profesor/termini/:id/pitanja" element={<ApprovePitanja />} />
    <Route path="/profesor/termini/:id/rezime" element={<RezimeKonsultacija />} />
    
    {/* Shared */}
    <Route path="/termini/:id" element={<TerminDetail />} />
  </Route>
</Routes>
```

### `<ProtectedRoute />`

Proverava da li je user logovan. Ako nije → redirect na `/login`.
Role-specific gating se radi **na nivou stranice** (ako user nije profesor a otvori `/profesor/...`, redirect na svoj dashboard).

---

## 5. Komponentna struktura

### 5.1 Single responsibility

Komponenta radi **jednu stvar**. Ako šta god radi >150 linija ili ima >5 props, razmisli o split-u.

### 5.2 Props interface

Svaka komponenta sa props ima eksplicitan TypeScript interface:

```typescript
interface QuestionDetailModalProps {
  questionId: string;
  isOpen: boolean;
  onClose: () => void;
  onScheduleClick?: (terminId: string) => void;
}

export function QuestionDetailModal({ ... }: QuestionDetailModalProps) {
  ...
}
```

### 5.3 Folder convention za komponente

Komponenta sa subfajlovima:
```
components/feedback/
├── QuestionDetailModal.tsx
├── FeedbackButtons.tsx
└── index.ts                # re-export public komponente
```

### 5.4 Komponente NE rade direktan API poziv

Komponenta poziva **hook** koji wrap-uje React Query. Komponenta ne zna za axios.

❌ Loše:
```typescript
useEffect(() => {
  axios.get("/api/feedback").then(...)
}, [])
```

✅ Dobro:
```typescript
const { data, isLoading } = useMyFeedback(questionId);
```

---

## 6. UX patterns

### 6.1 Loading states

Svaki query ima 3 stanja: loading, error, success.

```typescript
const { data, isLoading, error } = useTermin(terminId);

if (isLoading) return <Spinner />;
if (error) return <ErrorMessage error={error} />;
if (!data) return <EmptyState />;

return <TerminCard termin={data} />;
```

### 6.2 Error handling

User-facing errori **na srpskom**:

```typescript
function parseError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.error || "Došlo je do greške. Pokušajte ponovo.";
  }
  return "Neočekivana greška.";
}
```

### 6.3 Toast notifikacije

Za ne-blokirajuće poruke (success snimanja, kopirano u clipboard):
```typescript
toast.success("Feedback sačuvan");
toast.error("Slot je već popunjen");
```

### 6.4 Optimistic updates

Za feedback dugmad — koristi React Query optimistic mutations (vidi gore primer). Fast UX.

### 6.5 Polling za async operacije

AI processing i rezime generation traju nekoliko sekundi. Poll-uj svakih **3-5s** preko `refetchInterval`:

```typescript
const { data } = useTermin(terminId, {
  refetchInterval: (query) => {
    return query.state.data?.status === "ai_processing" ? 3000 : false;
  }
});
```

---

## 7. Styling

### 7.1 Tailwind first

Koristi Tailwind utility klase. **Ne** pisati zasebne CSS fajlove osim za:
- Globalna podešavanja (`styles/globals.css`)
- Custom Tailwind components (`@layer components`)

### 7.2 Color tokens

Definisani u `tailwind.config.js`:
- `primary` — glavna boja akcija
- `secondary` — sekundarne akcije
- `success`, `warning`, `danger` — status boje
- `neutral` — pozadine, borderi

❌ NIKAD `bg-[#1234ab]` (proizvoljna hex). Uvek token.

### 7.3 Responsive

Mobile first. Sve komponente moraju da rade na <500px viewport.

### 7.4 Dark mode

Trenutno **nije** podržan. Ne dodaji `dark:` klase u nove komponente bez razloga.

---

## 8. Forms

### Pattern: react-hook-form + Zod

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const schema = z.object({
  predmet: z.string().min(1, "Predmet je obavezan"),
  datum: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Format: YYYY-MM-DD"),
  vremeOd: z.string(),
  vremeDo: z.string(),
  maxStudenataPoSlotu: z.number().int().min(1).max(50).optional()
});

type FormData = z.infer<typeof schema>;

function KreirajTermin() {
  const form = useForm<FormData>({ resolver: zodResolver(schema) });
  // ...
}
```

---

## 9. Auth flow

```typescript
// auth/useAuth.ts
import { fetchAuthSession, signIn, signOut } from "aws-amplify/auth";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  // ...
  
  return {
    user,
    isAuthenticated: !!user,
    isStudent: user?.role === "student",
    isProfesor: user?.role === "profesor",
    signIn: async (email, password) => { ... },
    signOut: async () => { ... }
  };
}
```

JWT se čuva u Amplify storage, automatski refresh-uje. Axios interceptor čita iz Amplify pri svakom request-u:

```typescript
// api/client.ts
client.interceptors.request.use(async (config) => {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## 10. Internationalization

Trenutno **samo srpski** UI. Ne koristi `react-i18next` (overkill za V1).

**Konvencija:** UI string-ovi su direktno u JSX-u. Ako treba reused, lokalna `const`:

```typescript
const STRINGS = {
  feedbackPrompt: "Jasno?",
  yesButton: "Da",
  noButton: "Ne",
  scheduleConsultation: "Zakaži konsultacije"
} as const;
```

---

## 11. Frontend-specific don'ts

- ❌ `any` tip (koristi `unknown` ako ne znaš)
- ❌ Inline arrow funkcije u render-u kod liste sa hiljadama itema (perf)
- ❌ Direktan axios poziv u komponenti (uvek hook)
- ❌ `localStorage` za sensitive data (Cognito Amplify managea token storage sigurnije)
- ❌ Hardkodovan API URL (uvek iz `import.meta.env.VITE_API_URL`)
- ❌ User-facing tekst na engleskom (osim error fallback)
- ❌ `console.log` ostavljen u production kodu
- ❌ `useEffect` sa missing deps (eslint to hvata, popravi)
- ❌ Re-fetching na svaki render (koristi React Query staleTime)

---

## 12. Build & deploy

```bash
# Dev
cd frontend && npm run dev

# Build
npm run build  # output u frontend/dist

# Type check
npm run type-check

# Deploy preko CDK
cd ../infra && cdk deploy FrontendStack
```

### Environment variables

`.env.local`:
```
VITE_API_URL=https://abc123.execute-api.eu-central-1.amazonaws.com/v1
VITE_USER_POOL_ID=eu-central-1_XXXXX
VITE_USER_POOL_CLIENT_ID=YYYYY
VITE_REGION=eu-central-1
```

**Sve env var-ovi moraju da počinju sa `VITE_`** da bi bili dostupni u kodu.

---

**End of frontend/CLAUDE.md.**
