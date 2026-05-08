# Implementation plan — Frontend redesign (V4)

> **Verzija:** 2.0 (modifikovana — integrisan AI Tutor UX deep-dive)
> **Datum:** Maj 2026
> **Scope:** Finalni frontend redesign nakon stabilnog V3 backend-a
> **Optimizovano za:** Cursor agent direktnu implementaciju

Ovaj dokument zamenjuje V4 v1.0. Sve postojeće sekcije (design system, beige tema, redesign svih stranica) zadržane su; sekcija **7.5 (PitajPreZakazivanja + AI Tutor)** je dobila deep-dive sa kompletnim animacijama, komponentama, TypeScript interfejsima i Framer Motion config-om.

---

## 0. Potvrđeni input (V4 v2.0 nadogradnja)

Originalni V4 input (1-9) ostaje važeći:

1. **Obim V4:** `C` — komplet redesign sa design sistemom
2. **Vizuelni pravac:** `B` — modern SaaS
3. **UI osnova:** `A` — shadcn/ui
4. **Tema:** prljavo bela / beige varijanta (light-first)
5. **Animacije:** `A` — suptilne (sa izuzetkom AI tutor-a koji je richer)
6. **Specijalan tretman stranica:** sve ključne stranice
7. **Onboarding/empty states:** samo za AI feature-e
8. **Ne menjamo:** routing, API kontrakte (osim minor V3 tweak-a), React Query, backend
9. **Format plana:** kompletan + AI Tutor deep-dive

**Novi V4 v2.0 input (AI Tutor):**

- **Desktop layout:** Side-by-side (modal ostaje centar, chat klizi desno) — varijanta A
- **Esc/X behavior:** Zatvara samo chat, popup ostaje
- **AI input:** Stalno vidljiv u popup-u, kompaktan, fokus → resize u textarea
- **Mobile:** Bottom sheet sa drag handle (vaul library)
- **Context-aware:** AI uvek dobija popup pitanje + odgovor kao kontekst
- **Multi-turn:** Pamćenje unutar sesije + scroll back, max 5 turns
- **Persistencija:** Bez (clean state pri zatvaranju)
- **Loading:** Typing indicator (3 tačke pulse)
- **Sources:** Kartice ispod odgovora, klik otvara to pitanje u istom popup-u
- **Animation library:** Framer Motion
- **Style:** Linear/shadcn estetika, bez "AI gimmicks"
- **Header chat-a:** Sa Sparkles ikonom + naslovom "AI Tutor"
- **Bubble boje:** AI = violet accent, User = neutral
- **Backend tweak:** `POST /ai/ask` prihvata `context: { contextQuestionId, conversationHistory }` (mali backend dodatak ide u V4 scope)

---

## 1. Ciljevi i granice

### 1.1 Ciljevi
- Podići aplikaciju sa MVP estetike na polished produkcioni izgled.
- Uvesti konzistentan design sistem (tokens + reusable komponente).
- Poboljšati čitljivost i brzinu korišćenja na desktop i mobile uređajima.
- Posebno unaprediti UX oko V3 AI feature-a (`Pitaj pre zakazivanja` + AI tutor).
- Ostvariti "wow" demo efekat kroz koordinisane animacije AI tutor flow-a.

### 1.2 Van scope-a (za V4)
- Nema izmena backend endpoint-a osim **`POST /ai/ask` minor tweak** (dodavanje `context` field-a).
- Nema promene ruta (`src/App.tsx` ostaje funkcionalno isto).
- Nema refaktora auth/model/data sloja.
- Nema persistent chat istorije za studenta (gubi se pri zatvaranju popup-a).
- Nema streaming response-a (typing indicator + standardni request-response).

---

## 2. Design principles (V4)

1. **Clarity first** — najvažnije informacije su vidljive bez dodatnog klika.
2. **Progressive disclosure** — detalji se otvaraju kroz panel/modal, ne kroz prenatrpanu stranicu.
3. **Consistent affordances** — ista akcija izgleda isto svuda (primarni, sekundarni, destruktivni CTA).
4. **Mobile-first** — od 320px širine UX ostaje upotrebljiv bez horizontalnog skrola.
5. **Fast perception** — skeleton, loading states i mikrofidbek daju osećaj brzine.
6. **AI feels native** — AI tutor nije "feature dodatak", već prirodni produžetak browsing iskustva.

---

## 3. Vizuelni identitet (modern SaaS + beige)

### 3.1 Color palette (light theme, primarna)

Base neutral (beige family):
- `--background`: `#F7F2EA` (dirty white / beige)
- `--card`: `#FFFDF9`
- `--muted`: `#EFE7DB`
- `--border`: `#E2D7C8`
- `--foreground`: `#1F2937`
- `--muted-foreground`: `#6B7280`

Brand/accent:
- `--primary`: `#3B82F6` (SaaS plava)
- `--primary-foreground`: `#F8FAFC`
- `--accent`: `#8B5CF6` (violet accent — KORISTI SE ZA AI BUBBLES)
- `--accent-foreground`: `#FFFFFF`
- `--accent-muted`: `#F3EFFF` (light violet za AI background hint-ove)
- `--ring`: `#4F46E5`

Semantic:
- `--success`: `#16A34A`
- `--warning`: `#D97706`
- `--destructive`: `#DC2626`
- `--info`: `#0284C7`

AI-specific tokens (NOVO u V4 v2.0):
- `--ai-bubble-bg`: `#F3EFFF` (vrlo subtle violet)
- `--ai-bubble-fg`: `#1F2937`
- `--ai-bubble-border`: `#DDD6FE`
- `--user-bubble-bg`: `#FFFDF9` (neutral kao card)
- `--user-bubble-fg`: `#1F2937`
- `--user-bubble-border`: `#E2D7C8`

**Napomena:** Kontrast mora ostati WCAG AA minimum za tekst i CTA.

### 3.2 Dark mode strategija

- V4 isporuka je **light-first**.
- Tokeni ostaju kompatibilni sa postojećim `dark` class mehanizmom.
- Dark polish može u V4.1 bez menjanja komponenata (samo token override).

### 3.3 Tipografija i skala

- Font: `Inter` (fallback sistemski sans-serif).
- Type scale:
  - Display: 36/44
  - H1: 30/38
  - H2: 24/32
  - H3: 20/28
  - Body-lg: 18/28
  - Body: 16/24
  - Body-sm: 14/20
  - Caption: 12/16

### 3.4 Motion tokens (NOVO u V4 v2.0)

```typescript
// frontend/src/styles/motion.ts
export const motion = {
  duration: {
    fast: 0.15,      // hover, button feedback
    medium: 0.25,    // modal/drawer enter
    slow: 0.4        // koordinisane animacije (chat opening)
  },
  ease: {
    out: [0.16, 1, 0.3, 1],          // expo-out (smooth landing)
    inOut: [0.65, 0, 0.35, 1],       // expo-in-out
    spring: { type: "spring", stiffness: 350, damping: 30 }
  }
} as const;
```

---

## 4. Design system arhitektura

### 4.1 Token sloj

Centralizovati kroz:
- `frontend/src/styles/globals.css` (CSS vars)
- `frontend/tailwind.config.ts` (semantic color bindings)
- `frontend/src/styles/motion.ts` (Framer Motion config)

Dodati token grupe:
- Color, typography, spacing, radius, shadow, motion.

### 4.2 Komponentni sloj (shadcn/ui kao osnova)

Standardizovati komponente:
- **Layout:** `AppShell`, `TopNav`, `SideNav`, `PageHeader`
- **Data display:** `Card`, `Badge`, `Table`, `StatCard`, `EmptyState`
- **Inputs:** `Input`, `Textarea`, `Select`, `Combobox`, `Switch`
- **Feedback:** `Toast`, `Alert`, `Skeleton`, `Progress`, `Tooltip`
- **AI (NOVO):** `AiChatPanel`, `AiMessageBubble`, `AiTypingIndicator`, `AiSourceCard`, `AiConfidenceBadge`, `AiDisclaimer`, `AiInputBar`, `AiBottomSheet`

Pravilo:
- Stranice ne smeju sadržati "raw styling chaos"; sve kroz reusable komponente.

### 4.3 Grid i spacing sistem

- Layout max width: 1200-1280px.
- 8px spacing grid (`4, 8, 12, 16, 24, 32, 40, 48`).
- Radius:
  - `sm`: 8px
  - `md`: 12px
  - `lg`: 16px
  - `xl`: 20px

---

## 5. Dependencies (V4 + V4 v2.0)

### 5.1 Već prisutno (potvrditi)
- `react`, `react-dom` (>= 18)
- `@tanstack/react-query` (>= 5)
- `react-router-dom` (>= 6)
- `aws-amplify` (>= 6)
- Existing Radix paketi: dropdown-menu, dialog, select itd.

### 5.2 Instalirati za V4 (originalni)

```bash
cd frontend
npm install @radix-ui/react-tooltip @radix-ui/react-avatar \
            @radix-ui/react-separator @radix-ui/react-switch \
            @radix-ui/react-scroll-area @radix-ui/react-progress \
            @radix-ui/react-alert-dialog
npm install sonner
```

### 5.3 Instalirati za V4 v2.0 (NOVO za AI Tutor)

```bash
npm install framer-motion@^11
npm install vaul@^0.9          # Bottom sheet za mobile
npm install lucide-react       # Već možda postoji; potvrdi
```

### 5.4 shadcn/ui komponente (ako koristiš shadcn CLI)

```bash
npx shadcn-ui@latest init      # Ako nije već urađeno
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add sheet
npx shadcn-ui@latest add tooltip
npx shadcn-ui@latest add scroll-area
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add card
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add separator
```

---

## 6. IA i navigacija (bez promene ruta)

Ruta struktura ostaje ista kao u `src/App.tsx`.

UX unapređenja:
- Sticky top bar na desktop-u.
- Mobile nav preko `Sheet/Drawer`.
- Role-aware quick actions:
  - student: "Pretraži pitanja", "Pogledaj termine", "Moje rezervacije"
  - profesor: "Kreiraj termin", "Moji termini", "Rezimei"

---

## 7. Before/after po stranicama

### 7.1 `src/pages/Login.tsx`
- **Pre:** osnovna forma, minimalni vizuelni kontekst.
- **Posle:** split layout (leva strana branding + opis, desna strana forma), jasni inline error-i, bolje CTA hijerarhije.

### 7.2 `src/pages/Register.tsx`
- **Pre:** linearna forma.
- **Posle:** step-like grupisanje polja (nalog + profil), password hint, jasna potvrda posle submit-a.

### 7.3 `src/pages/student/Dashboard.tsx`
- **Pre:** funkcionalan pregled bez jasne prioritizacije.
- **Posle:** hero card "Sledeća konsultacija", tri quick action kartice i timeline aktivnosti.

### 7.4 `src/pages/student/BrowseTermini.tsx`
- **Pre:** lista termina bez napredne filtracije.
- **Posle:** filter bar (predmet, datum, status), responsive kartice, sticky filter na mobile-u.

### 7.5 `src/pages/student/PitajPreZakazivanja.tsx` ⭐ AI TUTOR DEEP-DIVE

> Ova sekcija je značajno proširena u V4 v2.0. Pogledaj sekciju **8** za kompletni AI Tutor UX deep-dive.

**Pre:**
- osnovna pretraga sa tagovima
- klik na pitanje → osnovni popup sa pitanjem/odgovorom + Da/Ne feedback + "Zakaži konsultacije"

**Posle:**
- real-time osećaj pretrage sa relevance score badge-om (`hybrid`/`tag`/`semantic`)
- klik na pitanje → polish-ovani popup sa AI tutor input-om u dnu
- focus na AI input → input se proširi u textarea, otkriva placeholder primere
- submit pitanja → koordinirana animacija:
  1. modal pomera ulevo ~150px (250ms ease-out)
  2. chat panel klizi sa desne strane (300ms ease-out, sa staggered messages)
  3. focus prelazi u chat input
- chat panel:
  - header sa Sparkles ikonom + "AI Tutor" + close button
  - scroll area sa user/AI bubbles
  - typing indicator dok AI generiše
  - source cards ispod AI odgovora (klik otvara to pitanje u istom popup-u)
  - confidence badge na dnu odgovora
  - disclaimer "Odgovor generisan AI-em" subtle u footer-u
  - input bar (sticky bottom) sa send dugmetom
- mobile (< md): bottom sheet sa drag handle umesto desnog panela

### 7.6 `src/pages/student/MojeRezervacije.tsx`
- **Pre:** lista rezervacija.
- **Posle:** grupisanje po statusu/vremenu, jasni countdown i akcioni dugmići za upravljanje rezervacijom.

### 7.7 `src/pages/profesor/Dashboard.tsx`
- **Pre:** osnovne informacije.
- **Posle:** KPI kartice (broj termina, broj rezervacija, pending pitanja), recent activity feed.

### 7.8 `src/pages/profesor/MojiTermini.tsx`
- **Pre:** standardna lista.
- **Posle:** card/table hibrid, badge statusi, brze akcije po terminu (uredi/objavi/pitanja/rezime).

### 7.9 `src/pages/profesor/KreirajTermin.tsx`
- **Pre:** forma bez jakog guidovanja.
- **Posle:** sectioned form (osnovno, slotovi, ograničenja), inline validacija, sticky "Sačuvaj" panel.

### 7.10 `src/pages/profesor/UrediTermin.tsx`
- **Pre:** sličan UX kao create.
- **Posle:** vizuelni diff trenutno vs novo, upozorenja za rizicne izmene.

### 7.11 `src/pages/profesor/ApprovePitanja.tsx`
- **Pre:** approval lista bez jasne prioritizacije.
- **Posle:** split view (lista + detalj), bulk approve akcije, status i quality indikatori.

### 7.12 `src/pages/profesor/Rezimei.tsx`
- **Pre:** funkcionalna lista rezimea.
- **Posle:** pregledne kartice sa datumom, predmetom, i CTA "Otvori rezime".

### 7.13 `src/pages/profesor/Rezime.tsx`
- **Pre:** sadržaj rezimea linearno prikazan.
- **Posle:** sekcije sa summary karticama, confidence badges, jasni eksport CTA.

### 7.14 `src/pages/TerminDetails.tsx`
- **Pre:** detalji termina i slotova.
- **Posle:** sticky detalji termina, jasni slot status indikatori, bolja mobile preglednost.

---

## 8. AI Tutor UX — kompletni deep-dive ⭐

Ova sekcija je **glavni V4 v2.0 sadržaj**. Cursor implementator treba da prati ovu sekciju kao "single source of truth" za AI Tutor.

### 8.1 Komponentna hijerarhija

```
PitajPreZakazivanja (page)
└── QuestionDetailDialog (Radix Dialog)
    ├── QuestionDetailContent
    │   ├── QuestionHeader (pitanje, tagovi, profesor)
    │   ├── AnswerBody (odgovor + scrollable)
    │   ├── FeedbackSection (V2: Da/Ne dugmad)
    │   ├── AiInputBar ← NOVO; trigger za AI Tutor
    │   └── ScheduleCta (V2: "Zakaži konsultacije")
    └── AiTutorPanel ← NOVO; klizi sa desne strane
        ├── AiTutorHeader (Sparkles ikona, "AI Tutor", close)
        ├── AiMessageList
        │   ├── AiMessageBubble (user variant — neutral)
        │   ├── AiMessageBubble (ai variant — violet accent)
        │   │   ├── AiConfidenceBadge
        │   │   └── AiSourceList → AiSourceCard[]
        │   └── AiTypingIndicator
        ├── AiTutorInput (textarea + send button)
        └── AiDisclaimerFooter
```

Mobile varianta:
```
PitajPreZakazivanja (page)
└── QuestionDetailDialog
    ├── QuestionDetailContent (full screen)
    │   ├── ...kao gore...
    │   └── AiInputBar (trigger)
    └── AiTutorBottomSheet (vaul Drawer) ← klizi odozdo
        ├── AiTutorHeader (drag handle + close)
        ├── AiMessageList
        ├── AiTutorInput
        └── AiDisclaimerFooter
```

### 8.2 State management

```typescript
// frontend/src/hooks/useAiTutorSession.ts

interface AiTutorMessage {
  id: string;
  role: "user" | "ai";
  content: string;
  confidence?: "high" | "medium" | "low";
  sources?: AiSourceRef[];
  preporukaZakazivanja?: boolean;
  createdAt: string;
}

interface AiSourceRef {
  questionId: string;
  pitanje: string;
  predmet: string;
  terminId: string;
}

interface AiTutorSessionState {
  isOpen: boolean;
  contextQuestionId: string | null;
  contextQuestion: string | null;
  contextAnswer: string | null;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  error: string | null;
}

// State ne persistira preko `localStorage` — clean na zatvaranju popup-a.
// Lives in React state inside QuestionDetailDialog.
```

### 8.3 Layout — desktop (md i veće)

#### State 1: Closed (modal samo)

```text
                              ┌─────────────────────┐
                              │   Search rezultati  │
                              │   (background       │
                              │    blur-uje se)     │
                              │                     │
              ┌──────────────┐│                     │
              │   Modal      ││                     │
              │   centriran  ││                     │
              │              ││                     │
              │   - pitanje  ││                     │
              │   - odgovor  ││                     │
              │   - feedback ││                     │
              │   - AI input ││                     │
              │   - CTA      ││                     │
              └──────────────┘│                     │
                              └─────────────────────┘
```

Modal pozicija: `transform: translateX(0)`
Chat panel: `translateX(100%)` (skriven van ekrana desno)

#### State 2: Active (chat otvoren)

```text
                  ┌──────────────┐  ┌──────────────────┐
                  │   Modal      │  │  AI Tutor Panel  │
                  │   pomeren    │  │                  │
                  │   ulevo      │  │  [Header]        │
                  │              │  │                  │
                  │   - pitanje  │  │  ▔▔▔▔▔▔▔▔▔▔▔     │
                  │   - odgovor  │  │  user msg        │
                  │   - feedback │  │  ai msg          │
                  │   - AI input │  │  user msg        │
                  │   - CTA      │  │  ai msg ...      │
                  │              │  │                  │
                  │              │  │  [Input + Send]  │
                  │              │  │  [Disclaimer]    │
                  └──────────────┘  └──────────────────┘
```

Modal pozicija: `transform: translateX(-150px)`
Chat panel: `translateX(0)`, width 400px, height = modal height

### 8.4 Layout — mobile (< md)

#### State 1: Closed
```text
┌─────────────────┐
│  Modal          │
│  full-screen    │
│                 │
│  - pitanje      │
│  - odgovor      │
│  - feedback     │
│  - AI input ▔▔▔ │  ← tap fokusira → expand
│  - CTA          │
└─────────────────┘
```

#### State 2: AI input fokusiran (još bez submit-a)
```text
┌─────────────────┐
│  Modal          │
│                 │
│  - pitanje      │
│  - odgovor      │
│  - feedback     │
│ ┌─────────────┐ │
│ │ AI Tutor    │ │  ← input expand-ovan u textarea
│ │ Pitaj me... │ │
│ │             │ │
│ │      [Send] │ │
│ └─────────────┘ │
│  - CTA          │
└─────────────────┘
```

#### State 3: Chat aktiviran (bottom sheet)
```text
┌─────────────────┐
│  Modal          │
│  (background    │
│   blur 30%)     │
│                 │
├─────────────────┤  ← drag handle (vaul)
│  ▂▂▂▂▂▂▂▂▂▂▂▂▂  │
│  AI Tutor   [×] │
│  ▔▔▔▔▔▔▔▔▔▔▔▔▔  │
│  user msg       │
│  ai msg         │
│  ▔▔▔▔▔▔▔▔▔▔▔▔▔  │
│  [Input + Send] │
│  [Disclaimer]   │
└─────────────────┘
```

Bottom sheet pokriva ~70% visine, drag-uje se gore/dole, tap na backdrop zatvara.

### 8.5 Animation choreography (Framer Motion)

#### 8.5.1 Modal shift (kad chat otvori)

```typescript
// frontend/src/components/ai/QuestionDetailDialog.tsx
import { motion } from "framer-motion";

const modalVariants = {
  centered: {
    x: 0,
    transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] }
  },
  shifted: {
    x: -150,
    transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] }
  }
};

<motion.div
  variants={modalVariants}
  animate={isChatOpen ? "shifted" : "centered"}
  className="..."
>
  {/* modal content */}
</motion.div>
```

#### 8.5.2 Chat panel slide-in

```typescript
// frontend/src/components/ai/AiTutorPanel.tsx
const panelVariants = {
  hidden: {
    x: "100%",
    opacity: 0,
    transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] }
  },
  visible: {
    x: 0,
    opacity: 1,
    transition: { 
      duration: 0.3, 
      ease: [0.16, 1, 0.3, 1],
      // chat panel kreće 50ms posle modala da bi izgledalo orchestrirano
      delay: 0.05
    }
  }
};

<motion.aside
  variants={panelVariants}
  initial="hidden"
  animate="visible"
  exit="hidden"
  className="..."
>
  {/* chat content */}
</motion.aside>
```

#### 8.5.3 Message bubble appearance (staggered)

```typescript
// frontend/src/components/ai/AiMessageBubble.tsx
const bubbleVariants = {
  hidden: { 
    opacity: 0, 
    y: 8,
    scale: 0.96
  },
  visible: { 
    opacity: 1, 
    y: 0,
    scale: 1,
    transition: { 
      duration: 0.2, 
      ease: [0.16, 1, 0.3, 1] 
    }
  }
};

<motion.div
  variants={bubbleVariants}
  initial="hidden"
  animate="visible"
  className="..."
>
  {message.content}
</motion.div>
```

#### 8.5.4 Typing indicator (3 tačke pulse)

```typescript
// frontend/src/components/ai/AiTypingIndicator.tsx
import { motion } from "framer-motion";

const dotVariants = {
  initial: { y: 0, opacity: 0.4 },
  animate: { 
    y: [-2, 0, -2], 
    opacity: [0.4, 1, 0.4],
    transition: {
      duration: 1.2,
      repeat: Infinity,
      ease: "easeInOut"
    }
  }
};

export function AiTypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3 bg-accent-muted rounded-lg w-fit">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          variants={dotVariants}
          initial="initial"
          animate="animate"
          transition={{ delay: i * 0.15 }}
          className="w-1.5 h-1.5 rounded-full bg-accent"
        />
      ))}
    </div>
  );
}
```

#### 8.5.5 Send button feedback

```typescript
// frontend/src/components/ai/AiTutorInput.tsx
<motion.button
  whileTap={{ scale: 0.95 }}
  whileHover={{ scale: 1.02 }}
  transition={{ duration: 0.15 }}
  onClick={handleSend}
  className="..."
>
  <Send className="w-4 h-4" />
</motion.button>
```

#### 8.5.6 Source card hover

```typescript
// frontend/src/components/ai/AiSourceCard.tsx
<motion.button
  whileHover={{ y: -2, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
  transition={{ duration: 0.15 }}
  onClick={() => onSourceClick(source.questionId)}
  className="..."
>
  {/* source content */}
</motion.button>
```

### 8.6 TypeScript interfaces (kompletni)

```typescript
// frontend/src/types/ai-tutor.ts

export type AiConfidence = "high" | "medium" | "low";
export type AiMessageRole = "user" | "ai";

export interface AiSourceRef {
  questionId: string;
  pitanje: string;
  predmet: string;
  terminId: string;
}

export interface AiTutorMessage {
  id: string;                          // ULID
  role: AiMessageRole;
  content: string;
  // AI-only fields:
  confidence?: AiConfidence;
  sources?: AiSourceRef[];
  preporukaZakazivanja?: boolean;
  // Common:
  createdAt: string;                   // ISO timestamp
}

export interface AiTutorContext {
  contextQuestionId: string;           // popup pitanje ID
  contextQuestion: string;             // tekst pitanja
  contextAnswer: string;               // tekst odgovora
  predmet: string;
  terminId: string | null;
}

export interface AiTutorSessionState {
  isOpen: boolean;
  context: AiTutorContext | null;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  error: string | null;
}

// API contract (matches V3 backend tweak — see section 9)
export interface AiAskRequest {
  predmet: string;
  question: string;
  terminId: string | null;
  context?: {
    contextQuestionId: string;
    contextQuestion: string;
    contextAnswer: string;
    conversationHistory: Array<{
      role: AiMessageRole;
      content: string;
    }>;
  };
}

export interface AiAskResponse {
  odgovor: string;
  confidence: AiConfidence;
  sources: string[];                   // questionId-i
  preporukaZakazivanja: boolean;
}
```

### 8.7 Komponentne implementacije

#### 8.7.1 `AiInputBar.tsx` — trigger u popup-u

```typescript
// frontend/src/components/ai/AiInputBar.tsx
import { useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

interface AiInputBarProps {
  onSubmit: (question: string) => void;
  placeholder?: string;
  isCompactByDefault?: boolean;
}

export function AiInputBar({ 
  onSubmit, 
  placeholder = "Pitaj AI tutora...",
  isCompactByDefault = true 
}: AiInputBarProps) {
  const [isExpanded, setIsExpanded] = useState(!isCompactByDefault);
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    if (value.trim().length < 10) return;
    onSubmit(value.trim());
    setValue("");
    setIsExpanded(false);
  };

  return (
    <motion.div
      animate={{ height: isExpanded ? "auto" : 48 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-lg border border-border bg-accent-muted/30 overflow-hidden"
    >
      <div className="flex items-start gap-2 p-3">
        <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" />
        
        {!isExpanded ? (
          <button
            onClick={() => setIsExpanded(true)}
            className="flex-1 text-left text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {placeholder}
          </button>
        ) : (
          <div className="flex-1 flex flex-col gap-2">
            <Textarea
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  handleSubmit();
                }
                if (e.key === "Escape") {
                  setIsExpanded(false);
                  setValue("");
                }
              }}
              placeholder="Detaljno pitanje za AI tutora..."
              className="min-h-[80px] resize-none border-0 bg-transparent focus-visible:ring-0 text-sm p-0"
              maxLength={500}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {value.length}/500 · ⌘+Enter za slanje
              </span>
              <motion.button
                whileTap={{ scale: 0.95 }}
                whileHover={{ scale: 1.02 }}
                onClick={handleSubmit}
                disabled={value.trim().length < 10}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent text-accent-foreground text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-3.5 h-3.5" />
                Pitaj
              </motion.button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
```

#### 8.7.2 `AiTutorPanel.tsx` — desktop panel

```typescript
// frontend/src/components/ai/AiTutorPanel.tsx
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, X } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AiMessageBubble } from "./AiMessageBubble";
import { AiTypingIndicator } from "./AiTypingIndicator";
import { AiTutorInput } from "./AiTutorInput";
import { AiDisclaimerFooter } from "./AiDisclaimerFooter";
import type { AiTutorMessage } from "@/types/ai-tutor";

interface AiTutorPanelProps {
  isOpen: boolean;
  onClose: () => void;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  onSendMessage: (content: string) => void;
  onSourceClick: (questionId: string) => void;
}

const panelVariants = {
  hidden: {
    x: "100%",
    opacity: 0,
    transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] }
  },
  visible: {
    x: 0,
    opacity: 1,
    transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1], delay: 0.05 }
  }
};

export function AiTutorPanel({
  isOpen,
  onClose,
  messages,
  isGenerating,
  onSendMessage,
  onSourceClick
}: AiTutorPanelProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          variants={panelVariants}
          initial="hidden"
          animate="visible"
          exit="hidden"
          className="fixed top-0 right-0 h-full w-[400px] bg-card border-l border-border shadow-xl flex flex-col z-50"
        >
          {/* Header */}
          <header className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-semibold">AI Tutor</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md hover:bg-muted transition-colors"
              aria-label="Zatvori chat"
            >
              <X className="w-4 h-4" />
            </button>
          </header>

          {/* Messages */}
          <ScrollArea className="flex-1 px-4 py-4">
            <div className="flex flex-col gap-4">
              {messages.map((msg) => (
                <AiMessageBubble
                  key={msg.id}
                  message={msg}
                  onSourceClick={onSourceClick}
                />
              ))}
              {isGenerating && <AiTypingIndicator />}
            </div>
          </ScrollArea>

          {/* Input */}
          <AiTutorInput onSend={onSendMessage} disabled={isGenerating} />

          {/* Disclaimer */}
          <AiDisclaimerFooter />
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
```

#### 8.7.3 `AiMessageBubble.tsx`

```typescript
// frontend/src/components/ai/AiMessageBubble.tsx
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { AiConfidenceBadge } from "./AiConfidenceBadge";
import { AiSourceCard } from "./AiSourceCard";
import type { AiTutorMessage } from "@/types/ai-tutor";

interface AiMessageBubbleProps {
  message: AiTutorMessage;
  onSourceClick: (questionId: string) => void;
}

const bubbleVariants = {
  hidden: { opacity: 0, y: 8, scale: 0.96 },
  visible: { 
    opacity: 1, y: 0, scale: 1,
    transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] }
  }
};

export function AiMessageBubble({ message, onSourceClick }: AiMessageBubbleProps) {
  const isAi = message.role === "ai";

  return (
    <motion.div
      variants={bubbleVariants}
      initial="hidden"
      animate="visible"
      className={`flex flex-col gap-2 ${isAi ? "items-start" : "items-end"}`}
    >
      {isAi && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground px-1">
          <Sparkles className="w-3 h-3 text-accent" />
          AI Tutor
        </div>
      )}
      
      <div
        className={`
          max-w-[85%] px-4 py-3 rounded-2xl text-sm
          ${isAi 
            ? "bg-accent-muted border border-accent/20 text-foreground rounded-tl-sm" 
            : "bg-card border border-border text-foreground rounded-tr-sm"
          }
        `}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
      </div>

      {isAi && message.confidence && (
        <div className="flex items-center gap-2 px-1">
          <AiConfidenceBadge confidence={message.confidence} />
        </div>
      )}

      {isAi && message.sources && message.sources.length > 0 && (
        <div className="w-full flex flex-col gap-1.5 mt-1">
          <span className="text-xs text-muted-foreground px-1">
            Bazirano na pitanjima:
          </span>
          <div className="flex flex-col gap-1.5">
            {message.sources.map((src) => (
              <AiSourceCard
                key={src.questionId}
                source={src}
                onClick={() => onSourceClick(src.questionId)}
              />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
```

#### 8.7.4 `AiTypingIndicator.tsx`

```typescript
// frontend/src/components/ai/AiTypingIndicator.tsx
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export function AiTypingIndicator() {
  return (
    <div className="flex flex-col gap-2 items-start">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground px-1">
        <Sparkles className="w-3 h-3 text-accent" />
        AI Tutor
      </div>
      <div className="flex items-center gap-1 px-4 py-3 bg-accent-muted border border-accent/20 rounded-2xl rounded-tl-sm">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-accent"
            animate={{
              y: [0, -3, 0],
              opacity: [0.4, 1, 0.4]
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.15
            }}
          />
        ))}
      </div>
    </div>
  );
}
```

#### 8.7.5 `AiConfidenceBadge.tsx`

```typescript
// frontend/src/components/ai/AiConfidenceBadge.tsx
import type { AiConfidence } from "@/types/ai-tutor";

const config: Record<AiConfidence, { label: string; classes: string }> = {
  high: {
    label: "Visoka pouzdanost",
    classes: "bg-success/10 text-success border-success/20"
  },
  medium: {
    label: "Srednja pouzdanost",
    classes: "bg-warning/10 text-warning border-warning/20"
  },
  low: {
    label: "Niska pouzdanost — preporučuju se konsultacije",
    classes: "bg-destructive/10 text-destructive border-destructive/20"
  }
};

export function AiConfidenceBadge({ confidence }: { confidence: AiConfidence }) {
  const { label, classes } = config[confidence];
  return (
    <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full border ${classes}`}>
      {label}
    </span>
  );
}
```

#### 8.7.6 `AiSourceCard.tsx`

```typescript
// frontend/src/components/ai/AiSourceCard.tsx
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import type { AiSourceRef } from "@/types/ai-tutor";

interface AiSourceCardProps {
  source: AiSourceRef;
  onClick: () => void;
}

export function AiSourceCard({ source, onClick }: AiSourceCardProps) {
  return (
    <motion.button
      whileHover={{ y: -1 }}
      transition={{ duration: 0.15 }}
      onClick={onClick}
      className="flex items-start justify-between gap-2 p-2.5 rounded-md bg-card border border-border hover:border-accent/40 hover:shadow-sm transition-all text-left"
    >
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-foreground line-clamp-2">
          {source.pitanje}
        </p>
        <p className="text-[10px] text-muted-foreground mt-0.5">
          {source.predmet}
        </p>
      </div>
      <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
    </motion.button>
  );
}
```

#### 8.7.7 `AiTutorInput.tsx`

```typescript
// frontend/src/components/ai/AiTutorInput.tsx
import { useState } from "react";
import { motion } from "framer-motion";
import { Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

interface AiTutorInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function AiTutorInput({ onSend, disabled }: AiTutorInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed.length < 10 || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  return (
    <div className="border-t border-border p-3 bg-background">
      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Postavi pitanje..."
          className="min-h-[44px] max-h-[120px] resize-none text-sm flex-1"
          maxLength={500}
          disabled={disabled}
        />
        <motion.button
          whileTap={{ scale: 0.95 }}
          whileHover={{ scale: 1.05 }}
          onClick={handleSubmit}
          disabled={value.trim().length < 10 || disabled}
          className="shrink-0 inline-flex items-center justify-center w-10 h-10 rounded-md bg-accent text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Pošalji"
        >
          <Send className="w-4 h-4" />
        </motion.button>
      </div>
      <div className="text-[10px] text-muted-foreground mt-1.5 px-1">
        {value.length}/500
      </div>
    </div>
  );
}
```

#### 8.7.8 `AiDisclaimerFooter.tsx`

```typescript
// frontend/src/components/ai/AiDisclaimerFooter.tsx
import { Info } from "lucide-react";

export function AiDisclaimerFooter() {
  return (
    <div className="px-4 py-2.5 bg-muted/40 border-t border-border">
      <p className="text-[10px] text-muted-foreground flex items-start gap-1.5 leading-relaxed">
        <Info className="w-3 h-3 shrink-0 mt-0.5" />
        <span>
          Odgovor je generisan AI-em. Za potpuno pouzdan odgovor zakaži konsultacije sa profesorom.
        </span>
      </p>
    </div>
  );
}
```

#### 8.7.9 `AiTutorBottomSheet.tsx` — mobile

```typescript
// frontend/src/components/ai/AiTutorBottomSheet.tsx
import { Drawer } from "vaul";
import { Sparkles, X } from "lucide-react";
import { AiMessageBubble } from "./AiMessageBubble";
import { AiTypingIndicator } from "./AiTypingIndicator";
import { AiTutorInput } from "./AiTutorInput";
import { AiDisclaimerFooter } from "./AiDisclaimerFooter";
import type { AiTutorMessage } from "@/types/ai-tutor";

interface AiTutorBottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  onSendMessage: (content: string) => void;
  onSourceClick: (questionId: string) => void;
}

export function AiTutorBottomSheet({
  isOpen,
  onClose,
  messages,
  isGenerating,
  onSendMessage,
  onSourceClick
}: AiTutorBottomSheetProps) {
  return (
    <Drawer.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 bg-black/40 z-50" />
        <Drawer.Content className="fixed bottom-0 left-0 right-0 h-[75vh] bg-card border-t border-border rounded-t-xl flex flex-col z-50">
          {/* Drag handle */}
          <div className="flex justify-center pt-3 pb-1">
            <div className="w-10 h-1 rounded-full bg-border" />
          </div>

          {/* Header */}
          <header className="flex items-center justify-between px-5 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-semibold">AI Tutor</h2>
            </div>
            <button onClick={onClose} className="p-1 rounded-md hover:bg-muted">
              <X className="w-4 h-4" />
            </button>
          </header>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4">
            <div className="flex flex-col gap-4">
              {messages.map((msg) => (
                <AiMessageBubble
                  key={msg.id}
                  message={msg}
                  onSourceClick={onSourceClick}
                />
              ))}
              {isGenerating && <AiTypingIndicator />}
            </div>
          </div>

          {/* Input + Disclaimer */}
          <AiTutorInput onSend={onSendMessage} disabled={isGenerating} />
          <AiDisclaimerFooter />
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
```

### 8.8 Hook za session management

```typescript
// frontend/src/hooks/useAiTutorSession.ts
import { useState, useCallback } from "react";
import { ulid } from "ulid";
import { askAiTutor } from "@/api/ai";
import type { AiTutorMessage, AiTutorContext } from "@/types/ai-tutor";

const MAX_HISTORY_TURNS = 5; // 5 user + 5 ai = 10 poruka u istoriji

export function useAiTutorSession() {
  const [isOpen, setIsOpen] = useState(false);
  const [context, setContext] = useState<AiTutorContext | null>(null);
  const [messages, setMessages] = useState<AiTutorMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openWithContext = useCallback((ctx: AiTutorContext, firstQuestion?: string) => {
    setContext(ctx);
    setMessages([]);
    setError(null);
    setIsOpen(true);
    if (firstQuestion) {
      // Šaljemo prvo pitanje odmah
      void sendMessage(firstQuestion, ctx);
    }
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    // Cleanup nakon animacije zatvaranja
    setTimeout(() => {
      setContext(null);
      setMessages([]);
      setError(null);
    }, 350);
  }, []);

  const sendMessage = useCallback(async (
    content: string, 
    ctxOverride?: AiTutorContext
  ) => {
    const ctx = ctxOverride || context;
    if (!ctx) return;

    const userMessage: AiTutorMessage = {
      id: ulid(),
      role: "user",
      content,
      createdAt: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsGenerating(true);
    setError(null);

    try {
      // Prepare conversation history (max N turns)
      const recentHistory = messages
        .slice(-MAX_HISTORY_TURNS * 2)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await askAiTutor({
        predmet: ctx.predmet,
        question: content,
        terminId: ctx.terminId,
        context: {
          contextQuestionId: ctx.contextQuestionId,
          contextQuestion: ctx.contextQuestion,
          contextAnswer: ctx.contextAnswer,
          conversationHistory: recentHistory
        }
      });

      const aiMessage: AiTutorMessage = {
        id: ulid(),
        role: "ai",
        content: response.odgovor,
        confidence: response.confidence,
        sources: [], // backend vraća questionIds, frontend ih hydrira
        preporukaZakazivanja: response.preporukaZakazivanja,
        createdAt: new Date().toISOString()
      };

      // TODO: hydrate sources by fetching pitanja po questionId-ima
      // (Lambda already returns enough data, ili posebnan call)

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err: any) {
      const message = err?.response?.status === 429
        ? "Dnevni limit AI pitanja je 20. Pokušaj sutra ili zakaži konsultacije."
        : "Došlo je do greške. Pokušaj ponovo.";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  }, [context, messages]);

  return {
    isOpen,
    context,
    messages,
    isGenerating,
    error,
    openWithContext,
    close,
    sendMessage
  };
}
```

### 8.9 Integracija u `QuestionDetailDialog`

```typescript
// frontend/src/components/question/QuestionDetailDialog.tsx
import { motion } from "framer-motion";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useAiTutorSession } from "@/hooks/useAiTutorSession";
import { AiInputBar } from "@/components/ai/AiInputBar";
import { AiTutorPanel } from "@/components/ai/AiTutorPanel";
import { AiTutorBottomSheet } from "@/components/ai/AiTutorBottomSheet";
// ... ostali importi

interface QuestionDetailDialogProps {
  question: SearchQuestionResult | null;
  isOpen: boolean;
  onClose: () => void;
  onChangeQuestion: (questionId: string) => void;
}

export function QuestionDetailDialog({ 
  question, isOpen, onClose, onChangeQuestion 
}: QuestionDetailDialogProps) {
  const isDesktop = useMediaQuery("(min-width: 768px)");
  const tutor = useAiTutorSession();

  const handleAiTrigger = (firstQuestion: string) => {
    if (!question) return;
    tutor.openWithContext({
      contextQuestionId: question.questionId,
      contextQuestion: question.pitanje,
      contextAnswer: question.odgovor,
      predmet: question.predmet,
      terminId: question.terminId
    }, firstQuestion);
  };

  const handleSourceClick = (questionId: string) => {
    onChangeQuestion(questionId);
    tutor.close();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogPortal>
        <DialogOverlay className="bg-black/50 backdrop-blur-sm" />
        
        <motion.div
          animate={{ x: tutor.isOpen && isDesktop ? -150 : 0 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50"
        >
          <DialogContent className="w-[600px] max-w-[90vw] max-h-[85vh] bg-card border-border">
            {/* Question header */}
            <QuestionHeader question={question} />
            
            {/* Answer */}
            <AnswerBody answer={question?.odgovor} />
            
            {/* V2 feedback */}
            <FeedbackSection questionId={question?.questionId} />
            
            {/* AI Input — trigger za chat */}
            <AiInputBar onSubmit={handleAiTrigger} />
            
            {/* V2 schedule CTA */}
            <ScheduleCta terminId={question?.terminId} />
          </DialogContent>
        </motion.div>

        {/* AI Tutor — desktop panel */}
        {isDesktop && (
          <AiTutorPanel
            isOpen={tutor.isOpen}
            onClose={tutor.close}
            messages={tutor.messages}
            isGenerating={tutor.isGenerating}
            onSendMessage={tutor.sendMessage}
            onSourceClick={handleSourceClick}
          />
        )}

        {/* AI Tutor — mobile bottom sheet */}
        {!isDesktop && (
          <AiTutorBottomSheet
            isOpen={tutor.isOpen}
            onClose={tutor.close}
            messages={tutor.messages}
            isGenerating={tutor.isGenerating}
            onSendMessage={tutor.sendMessage}
            onSourceClick={handleSourceClick}
          />
        )}
      </DialogPortal>
    </Dialog>
  );
}
```

### 8.10 Edge cases checklist

| Scenario | Handling |
|----------|----------|
| Student kuca < 10 karaktera u AI input | Submit dugme disabled |
| Student kuca > 500 karaktera | Counter postaje crven, max-length blokira dalje kucanje |
| Backend vraća 429 (rate limit) | Toast + chat error state sa porukom |
| Backend vraća 500 | Error state u chat-u sa "Pokušaj ponovo" CTA |
| Backend vraća 503 (Bedrock down) | Error state sa porukom "AI tutor trenutno nije dostupan" |
| Network drop tokom generisanja | Error state, message ostaje u istoriji |
| Student spam-uje send | Send disabled tokom `isGenerating` |
| Source kartica se klikne | Trenutni popup se menja na novo pitanje, chat se zatvara |
| Confidence "low" + preporukaZakazivanja=true | Dodatna CTA kartica "Zakaži konsultacije" pre disclaimer-a |
| AI vraća prazan `sources` array | Source sekcija se ne renderuje |
| Modal close (X) tokom otvorenog chat-a | Prvo zatvara chat (animacija), pa popup |
| Esc key tokom chat-a | Zatvara chat, popup ostaje |
| Esc key kad chat zatvoren | Zatvara popup |
| Drag-down na bottom sheet (mobile) | Zatvara chat, popup ostaje |
| Tap na backdrop iza bottom sheet-a | Zatvara chat, popup ostaje |
| AI input fokusiran a popup zatvori | Cleanup unutrašnjeg state-a |
| Više od 5 turns u istoriji | Stari turns se seku iz konteksta (NE iz prikaza) |

---

## 9. Backend tweak za AI Tutor (V4 v2.0)

V3 plan već pokriva `POST /ai/ask` endpoint. V4 v2.0 dodaje **opciono polje `context`** za context-aware multi-turn chat.

### 9.1 Šta se menja

**Lambda:** `backend/lambdas/ai/ask.py`

**Promena:** Prihvatanje opcionog `context` field-a u request body-ju, koji se koristi za izgradnju Bedrock prompt-a sa popup pitanjem + history.

### 9.2 Novi request shape

```json
{
  "predmet": "Programiranje 1",
  "question": "Možeš li to pojednostaviti?",
  "terminId": "t_001",
  "context": {
    "contextQuestionId": "q_42",
    "contextQuestion": "Šta je rekurzija?",
    "contextAnswer": "Rekurzija je tehnika...",
    "conversationHistory": [
      { "role": "user", "content": "Ne razumem zašto stack pukne" },
      { "role": "ai", "content": "Stack ima ograničenje..." }
    ]
  }
}
```

### 9.3 Backend implementation skica

```python
# backend/lambdas/ai/ask.py (delta)

class AskContext(BaseModel):
    contextQuestionId: str
    contextQuestion: str = Field(max_length=2000)
    contextAnswer: str = Field(max_length=5000)
    conversationHistory: list[dict] = Field(default_factory=list, max_length=10)

class AskRequest(BaseModel):
    predmet: str
    question: str = Field(min_length=10, max_length=500)
    terminId: str | None = None
    context: AskContext | None = None  # NOVO

def build_prompt(req: AskRequest, semantic_results: list[dict]) -> tuple[str, str]:
    system = (
        "Ti si AI tutor za predmet {predmet}. "
        "Odgovaras na srpskom, jasno i kratko. "
        "Koristis dati kontekst (popup pitanje, istorija razgovora, slicna pitanja). "
        "Ako kontekst nije dovoljan, reci da nisi siguran i predlozi konsultacije. "
        "Vrati iskljucivo JSON sa poljima: odgovor, confidence, sources, preporukaZakazivanja."
    ).format(predmet=req.predmet)

    parts = []
    
    # Context pitanje iz popup-a (NOVO)
    if req.context:
        parts.append(
            "TRENUTNO PITANJE (iz popup-a):\n"
            f"P: {req.context.contextQuestion}\n"
            f"O: {req.context.contextAnswer}\n"
        )
        
        # Istorija razgovora (NOVO)
        if req.context.conversationHistory:
            parts.append("ISTORIJA RAZGOVORA:")
            for msg in req.context.conversationHistory[-10:]:  # cap u Lambdi
                role_label = "Student" if msg["role"] == "user" else "AI tutor"
                parts.append(f"{role_label}: {msg['content']}")
            parts.append("")
    
    # Slicna pitanja iz semantic search-a
    parts.append("SLICNA PITANJA IZ BAZE:")
    for s in semantic_results[:5]:
        parts.append(f"- {s['pitanje']}")
        parts.append(f"  {s['odgovor'][:300]}")
    
    parts.append("")
    parts.append(f"NOVO PITANJE STUDENTA: {req.question}")
    
    user = "\n".join(parts)
    return system, user
```

### 9.4 Token cap protection

Sa context + history + semantic results, input može lako da ode preko 8K tokena. Cap-ovi koji se primenjuju:
- `contextQuestion`: max 2000 chars
- `contextAnswer`: max 5000 chars
- `conversationHistory`: max 10 entries (Pydantic), Lambda dodatno cap-uje na poslednjih 10
- Semantic results: top 5
- Material excerpt: 5000 chars (V3 default)
- `max_tokens` output: 600 (V3 default)

Procenjeni input cap: ~8K tokena (~$0.008 po pozivu, marginalno više od V3 baseline-a $0.007).

### 9.5 Bez breaking changes

`context` polje je **opciono**. Postojeći klijenti koji ga ne šalju nastavljaju da rade isto kao u V3.

---

## 10. Mobile-first pravila

- Breakpoints:
  - `sm`: 640
  - `md`: 768 (AI tutor mobile/desktop split)
  - `lg`: 1024
  - `xl`: 1280
- Na mobile:
  - top nav ide u `Sheet`,
  - kartice prelaze u 1-kolonu,
  - filter bar postaje horizontal scroll chip row,
  - forme prelaze u stacked layout sa većim tap target-ima (min 44px),
  - **AI tutor → vaul bottom sheet** (75vh).

Performance UX:
- Izbeći teške animacije i velike shadow-e na low-end uređajima.
- Koristiti skeleton i progressive rendering za data-heavy stranice.
- Framer Motion `LazyMotion` za smanjenje bundle-a na ekranima koji ne koriste animacije.

---

## 11. Animacije i mikro-interakcije (suptilne)

### Dozvoljeno globalno
- `transition-colors`, `transition-shadow`, `transition-transform` do 150-200ms.
- Hover elevation na card komponentama.
- Fade/slide enter za modal/drawer.

### AI tutor specifične (richer ali kontrolisane)
- Modal shift ulevo (250ms)
- Chat panel slide-in sa staggered delay (300ms + 50ms delay)
- Message bubble appearance (200ms staggered)
- Typing indicator pulse (1.2s loop)
- Send button tap feedback (150ms)
- Source card hover elevation (150ms)

### Nije u planu (NIJE V4)
- Kompleksne page transitions
- Scroll-driven animacije
- Glowing borders / gradient shimmers / "AI shimmer" effects
- Motion koji usporava interakciju na mobile-u

---

## 12. AI-only empty states i onboarding

Primena samo u AI kontekstu:

1. **`PitajPreZakazivanja` bez rezultata:**
   - Empty state komponenta sa porukom "Nema direktnog poklapanja. Probaj AI tutora ili preformuliši upit."
   - CTA "Pitaj AI tutora direktno"

2. **Chat panel — prazno stanje (pre prvog pitanja):**
   - Welcome message AI tutor-a:
     ```
     Pitaj me bilo šta o pitanju "{contextQuestion}".
     Mogu da pojednostavim, dam primere ili objasnim detaljnije.
     ```
   - 3-4 placeholder example chips:
     - "Pojednostavi ovo"
     - "Daj mi konkretan primer"
     - "Objasni sa analogijom"
     - "Šta je veza sa drugim temama?"

3. **Chat odgovor low confidence:**
   - Confidence badge "Niska pouzdanost"
   - Istaknut CTA kartica iznad disclaimer-a: "Razmotri zakazivanje konsultacija"

4. **Prvi ulazak u AI sekciju (per-user, lokalno tracked u localStorage):**
   - Tooltip 1 (na AI input bar): "💬 Pitaj AI tutora detaljnija pitanja"
   - Tooltip 2 (kad chat otvori): "Confidence badge ti pokazuje koliko je AI siguran"
   - Tooltip-i se prikazuju jednom, dismiss store-uje u `localStorage["ai-onboarding-seen"]`

---

## 13. File-by-file implementacioni plan

### 13.1 Core styling (POSTOJEĆI + V4 v2.0)
- `frontend/src/styles/globals.css`
  - nova beige token tema,
  - semantic color tokeni,
  - **AI tokens (`--ai-bubble-bg`, `--user-bubble-bg`, etc.)**,
  - tipografija i radius standardizacija.
- `frontend/tailwind.config.ts`
  - proširenje token mapa, spacing i shadow utility,
  - **AI semantic colors**.
- `frontend/src/styles/motion.ts` (NOVO)
  - Framer Motion config konstante (durations, easings).

### 13.2 Shared layout i UI infra (POSTOJEĆI)
- `frontend/src/components/common/Layout.tsx`
- `components/common/PageHeader.tsx`
- `components/common/StatCard.tsx`
- `components/common/EmptyState.tsx`

### 13.3 AI komponente (NOVO za V4 v2.0)

Sve u `frontend/src/components/ai/`:

- `AiInputBar.tsx` — trigger u popup-u (compact → expanded)
- `AiTutorPanel.tsx` — desktop side panel
- `AiTutorBottomSheet.tsx` — mobile bottom sheet (vaul)
- `AiMessageBubble.tsx` — user + ai variant
- `AiTypingIndicator.tsx` — 3 tačke pulse
- `AiConfidenceBadge.tsx` — high/medium/low badge
- `AiSourceCard.tsx` — clickable izvor
- `AiTutorInput.tsx` — sticky bottom textarea + send
- `AiDisclaimerFooter.tsx` — legalese
- `AiOnboardingTooltip.tsx` — first-use guidance
- `AiEmptyState.tsx` — welcome state pre prvog pitanja
- `index.ts` — barrel export

### 13.4 Hooks (NOVO za V4 v2.0)

- `frontend/src/hooks/useAiTutorSession.ts` — session state management
- `frontend/src/hooks/useMediaQuery.ts` — responsive utility (ako ne postoji)
- `frontend/src/hooks/useFirstTimeFlag.ts` — onboarding tracking

### 13.5 API client (UPDATE V3 + V4 tweak)

- `frontend/src/api/ai.ts`:
  - `askAiTutor(req: AiAskRequest): Promise<AiAskResponse>` — sa `context` field-om

### 13.6 Types

- `frontend/src/types/ai-tutor.ts` (NOVO) — sve interfaces iz sekcije 8.6

### 13.7 Pages — modifikacije

- `frontend/src/pages/student/PitajPreZakazivanja.tsx`
  - integrisanje `QuestionDetailDialog` sa AI tutor logikom
  - hookup `useAiTutorSession`
  - source click handler

- `frontend/src/components/question/QuestionDetailDialog.tsx`
  - integrisan AI tutor panel/bottom sheet
  - modal shift animacija
  - context propagation

### 13.8 Backend (delta — V4 v2.0)

- `backend/lambdas/ai/ask.py`
  - dodati `AskContext` Pydantic model
  - ažurirati `build_prompt` da koristi context + history
  - dodati cap-ove na input length

- `backend/shared/models.py`
  - exporti za `AskContext` ako je shared

- Test:
  - `backend/tests/unit/test_ask_with_context.py` (NOVO)

---

## 14. Faze implementacije i procena

### Originalni V4 fazni plan
1. **Foundation (2 dana)**
2. **Auth + shared pages (2 dana)**
3. **Student flow redesign (3 dana)** — bez AI deep-dive
4. **Profesor flow redesign (3 dana)**
5. **Polish + responsive QA (2 dana)**

### V4 v2.0 dodaci
6. **AI Tutor implementacija (3 dana)** — NOVO
   - 6.1 (0.5d) — backend tweak `POST /ai/ask` sa `context`
   - 6.2 (1d) — AI komponente (panel, bubbles, indicators)
   - 6.3 (1d) — desktop animations (modal shift + chat slide)
   - 6.4 (0.5d) — mobile bottom sheet integration

7. **AI tutor polish + edge cases (1 dan)** — NOVO
   - error states, rate limit UX, onboarding tooltips, source navigation

**Ukupno V4 v2.0:** **~16 dana** solo developera.

---

## 15. QA checklist za V4 v2.0

### Generalni V4 (postojeće)
- [ ] Sve postojeće rute funkcionišu bez izmene URL strukture.
- [ ] Nema regresije u API pozivima i form submit flow-ovima.
- [ ] Light beige tema konzistentna na svim ekranima.
- [ ] Mobile (320px-430px) bez horizontalnog skrola.
- [ ] Keyboard focus i tab order rade na formama i modalima.
- [ ] Lighthouse (Performance/Accessibility/Best Practices) bez ozbiljnih regresija.

### AI Tutor specifično (V4 v2.0)
- [ ] AI input bar je vidljiv u popup-u, fokusabilan tastature.
- [ ] Submit AI pitanja pokreće koordiniranu animaciju (modal shift + chat slide).
- [ ] Chat panel ima header sa Sparkles + naslovom + close.
- [ ] User i AI message bubbles razlikuju vizuelno (neutral vs violet).
- [ ] Typing indicator se prikazuje tokom `isGenerating`.
- [ ] Confidence badge prikazuje pravu boju (success/warning/destructive).
- [ ] Source kartice klikabilne, klik menja popup pitanje.
- [ ] Disclaimer footer subtle, čitljiv.
- [ ] Multi-turn radi: sledeće pitanje pamti kontekst razgovora.
- [ ] Rate limit 429 prikazuje user-friendly poruku.
- [ ] Mobile: bottom sheet sa drag handle, drag-down zatvara.
- [ ] Mobile: tap na backdrop zatvara bottom sheet.
- [ ] Esc tokom chat-a zatvara samo chat (popup ostaje).
- [ ] Esc kad chat zatvoren zatvara popup.
- [ ] Onboarding tooltip-i se prikazuju samo prvi put.
- [ ] AI tokens (--ai-bubble-bg, --user-bubble-bg) se primenjuju.
- [ ] Animacije rade na 60fps na mobile-u (Chrome DevTools throttle).
- [ ] Bez "pop-in flicker"-a tokom panel/sheet enter animacije.
- [ ] AI panel ne pravi layout shift glavnog sadržaja.

---

## 16. Definition of done (V4 v2.0)

### Generalni V4 (postojeće)
- [ ] Implementiran design sistem (tokeni + reusable komponente).
- [ ] Redizajnirane sve ključne student i profesor stranice.
- [ ] Primenjen modern SaaS stil sa prljavo belom/beige bazom.
- [ ] Suptilne animacije postoje, bez negativnog uticaja na performanse.
- [ ] Onboarding/empty states dodati samo u AI feature flow-u.
- [ ] Dokumentovana dependency lista i rollout koraci.

### AI Tutor specifično (V4 v2.0)
- [ ] `AiInputBar` integrisan u `QuestionDetailDialog`.
- [ ] `AiTutorPanel` (desktop) sa svim animacijama radi end-to-end.
- [ ] `AiTutorBottomSheet` (mobile) sa vaul drag UX-om radi.
- [ ] `useAiTutorSession` hook upravlja kompletnim session state-om.
- [ ] Backend tweak `POST /ai/ask` prihvata `context` field bez breaking change-a.
- [ ] Source navigation (klik na karticu menja popup) radi.
- [ ] Multi-turn conversation sa max 5 turns history-jem radi.
- [ ] Rate limit + error states + disclaimer prisutni.
- [ ] Onboarding tooltip-i se prikazuju jednom (localStorage flag).

---

## 17. Rizici i mitigacije

### Generalni V4
1. **Preširok scope redesign-a**
   - Mitigacija: fazna isporuka i strogo praćenje file-by-file plana.
2. **Nekonzistentan stil između starih i novih komponenti**
   - Mitigacija: prvo završiti foundation layer pre page migracije.
3. **Regresije u postojećem flow-u**
   - Mitigacija: manual regression checklist po ruti.
4. **Performance pad zbog previše vizuelnih efekata**
   - Mitigacija: suptilan motion-only pristup i profilisanje na mobile-u.

### AI Tutor specifično (V4 v2.0)
5. **Animacija orchestration ne radi glatko**
   - Mitigacija: koristiti `motion.ts` konstante, izbegavati istovremeni layout + animation update; testirati na low-end uređajima.

6. **Bundle size raste preko granice**
   - Mitigacija: Framer Motion `LazyMotion` za stranice koje ga ne koriste; vaul je tree-shaken.

7. **Multi-turn cost runaway**
   - Mitigacija: history cap na 5 turns u frontu + Pydantic max_length na backendu.

8. **Source links ka neodobrenim/obrisanim pitanjima**
   - Mitigacija: backend filter (samo approved questions u semantic search-u, već V3 GSI5 obezbeđuje).

9. **Mobile bottom sheet conflict sa keyboard otvaranjem**
   - Mitigacija: `interact-outside={false}` kad je input fokusiran; testirati iOS Safari + Android Chrome.

10. **Breaking change za V3 klijente**
    - Mitigacija: `context` field je opciono → V3 i V4 klijenti mogu da koegzistiraju.

---

## 18. Cursor agent — kako koristiti ovaj plan

> Ovaj plan je optimizovan za direktnu implementaciju kroz Cursor agent.

### Predloženi prompt za Cursor:

```
Implementiraj V4 v2.0 frontend redesign prema dokumentu IMPLEMENTATION_PLAN_V4.md.

Kreni sa fazom 6 (AI Tutor) ako je foundation (faze 1-5) već gotov.

Konkretno za fazu 6:
1. Instaliraj dependencies iz sekcije 5.3.
2. Dodaj AI tokens u globals.css i tailwind.config.ts (sekcija 3.1).
3. Kreiraj motion.ts (sekcija 3.4).
4. Kreiraj sve AI komponente iz sekcije 8.7 — koristi gotove TypeScript snippets.
5. Kreiraj useAiTutorSession hook (sekcija 8.8).
6. Integriši u QuestionDetailDialog (sekcija 8.9).
7. Implementiraj backend tweak (sekcija 9).
8. Pokreni QA checklist iz sekcije 15.

Kad bilo šta nije jasno, pitaj pre nego što improvizuješ. 
Ne menjaj routing, API kontrakte (osim sekcija 9 koja je dozvoljena), ni postojeće feature-e van scope-a V4.
```

### Za parcijalnu implementaciju (samo jedna komponenta):

```
Implementiraj komponentu X iz IMPLEMENTATION_PLAN_V4.md, sekcija 8.7.{N}.
Koristi tačno onaj TypeScript kod iz dokumenta (sa istim Tailwind klasama).
Posle kreiranja, dodaj export u components/ai/index.ts.
```

### Za debugovanje animacije:

```
Animacija X iz sekcije 8.5.{N} ne radi kako treba. 
Pokaži mi trenutnu implementaciju i predloži fix u skladu sa motion.ts konstantama.
Ne menjaj duration/ease iz dokumenta — ako misliš da treba drugačije, pitaj.
```

---

**Kraj dokumenta. V4 v2.0 — spreman za Cursor implementaciju.**
