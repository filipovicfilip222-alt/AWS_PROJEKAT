// =============================================================
// PredZnanje — Screens
// Login · Dashboard (home) · Termini (search) · TerminDetail
// AITutor · MyReservations
// =============================================================

const { useState, useMemo } = React;

// ---------- Mock data ----------
const SUBJECTS = [
  "Algoritmi i strukture podataka",
  "Operativni sistemi",
  "Baze podataka",
  "Računarske mreže",
  "Diskretna matematika",
  "Veb programiranje",
];

const PROFESSORS = [
  { id: "p1", name: "Ana Marković", title: "prof. dr", subject: "Algoritmi i strukture podataka" },
  { id: "p2", name: "Marko Jovanović", title: "prof. dr", subject: "Operativni sistemi" },
  { id: "p3", name: "Jovana Petrović", title: "doc. dr", subject: "Baze podataka" },
];

const TERMINI = [
  { id: "t1", subject: "Algoritmi i strukture podataka", professor: PROFESSORS[0], date: "2026-05-14", start: "09:00", end: "10:30", slots: 3, totalSlots: 6, status: "objavljen" },
  { id: "t2", subject: "Operativni sistemi", professor: PROFESSORS[1], date: "2026-05-16", start: "11:00", end: "12:30", slots: 5, totalSlots: 6, status: "objavljen" },
  { id: "t3", subject: "Baze podataka", professor: PROFESSORS[2], date: "2026-05-18", start: "13:00", end: "14:30", slots: 0, totalSlots: 6, status: "popunjen" },
  { id: "t4", subject: "Algoritmi i strukture podataka", professor: PROFESSORS[0], date: "2026-05-21", start: "10:00", end: "11:30", slots: 4, totalSlots: 6, status: "objavljen" },
];

// ---------- LOGIN ----------
function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState("filip.petrovic@fakultet.rs");
  const [password, setPassword] = useState("aqaqaq");
  const [role, setRole] = useState("student");
  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <Logo role={role} />
        </div>
        <h1 className="auth-title">Dobrodošli nazad.</h1>
        <p className="auth-sub">Prijavi se da pretražiš termine konsultacija ili pitaš AI tutora.</p>

        <div className="role-toggle">
          <button className={`role-pill ${role === "student" ? "active" : ""}`} onClick={() => setRole("student")}>
            <Icon name="graduation-cap" size={14} /> Student
          </button>
          <button className={`role-pill ${role === "professor" ? "active" : ""}`} onClick={() => setRole("professor")}>
            <Icon name="book-open" size={14} /> Profesor
          </button>
        </div>

        <form className="auth-form" onSubmit={(e) => { e.preventDefault(); onLogin({ email, role, name: role === "professor" ? "Ana Marković" : "Filip Petrović" }); }}>
          <Field label="Email">
            <Input leftIcon="mail" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ime.prezime@fakultet.rs" />
          </Field>
          <Field label="Lozinka">
            <Input leftIcon="lock" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Button variant="default" size="lg" type="submit" className="auth-submit">
            Prijavi se
            <Icon name="arrow-right" size={16} />
          </Button>
        </form>

        <div className="auth-foot">
          Nemaš nalog? <a href="#">Registruj se</a>
        </div>
      </div>

      <div className="auth-aside">
        <div className="aside-blob a"></div>
        <div className="aside-blob b"></div>
        <div className="aside-grid"></div>
        <div className="aside-content">
          <div className="aside-eyebrow">
            <Icon name="sparkles" size={12} /> AI Tutor
          </div>
          <div className="aside-quote">
            &ldquo;PitajPreZakazivanja&rdquo;
          </div>
          <p className="aside-blurb">
            Postavi pitanje, dobij odgovor sa procenom pouzdanosti, pa zakaži termin samo ako ti AI nije bio dovoljan.
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------- DASHBOARD ----------
function Dashboard({ user, onRoute, onOpenTermin }) {
  const next = TERMINI[0];
  const stats = [
    { label: "Termini ovog meseca", value: 12, hint: "8 objavljenih", icon: "calendar", tone: "muted" },
    { label: "Rezervacije", value: 38, hint: "+6 ove nedelje", icon: "book-open", tone: "primary" },
    { label: "AI pretrage", value: 204, hint: "Hibridno + tag", icon: "sparkles", tone: "accent" },
    { label: "\u201CJasno?\u201D odobreno", value: "87%", hint: "Yes / no votes", icon: "thumbs-up", tone: "success" },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Početna</div>
          <h1 className="page-title">Zdravo, {user.name.split(" ")[0]}.</h1>
          <p className="page-sub">Tvoja sledeća konsultacija je za 6 dana — AI tutor je dostupan dok čekaš.</p>
        </div>
        <div className="page-head-actions">
          <Button variant="outline" onClick={() => onRoute("termini")}>
            <Icon name="search" size={14} /> Pretraži termine
          </Button>
          <Button variant="accent" onClick={() => onRoute("ai")}>
            <Icon name="sparkles" size={14} /> Pitaj AI
          </Button>
        </div>
      </div>

      <div className="stats-grid">
        {stats.map((s, i) => (
          <Card key={i} className="stat-card">
            <div className="stat-head">
              <span className="eyebrow">{s.label}</span>
              <span className={`stat-icon stat-icon-${s.tone}`}><Icon name={s.icon} size={16} /></span>
            </div>
            <div className={`stat-value stat-value-${s.tone}`}>{s.value}</div>
            <div className="stat-hint">{s.hint}</div>
          </Card>
        ))}
      </div>

      <div className="hero-grid">
        <div className="hero-block">
          <div className="hero-blob a"></div>
          <div className="hero-blob b"></div>
          <div className="hero-grid-tex"></div>
          <span className="hero-eyebrow"><Icon name="sparkles" size={12} /> Sledeća konsultacija</span>
          <h2 className="hero-title">{next.subject}</h2>
          <p className="hero-sub">
            {formatDate(next.date)} · {next.start}–{next.end} · {next.professor.title} {next.professor.name}
          </p>
          <div className="hero-actions">
            <Button variant="default" onClick={() => onOpenTermin(next.id)}>
              Otvori termin <Icon name="arrow-right" size={14} />
            </Button>
            <Button variant="ghost-on-dark" onClick={() => onRoute("ai")}>
              <Icon name="sparkles" size={14} /> Pripremi se sa AI
            </Button>
          </div>
        </div>

        <Card className="ai-promo">
          <div className="ai-promo-head">
            <AIMark size={40} />
            <div>
              <div className="ai-promo-title">&ldquo;PitajPreZakazivanja&rdquo;</div>
              <div className="ai-promo-sub">AI Tutor · Powered by Claude</div>
            </div>
          </div>
          <p className="ai-promo-blurb">
            Pre nego što rezervišeš slot, proveri da li ti AI tutor može odgovoriti odmah. Ako da — uštedećeš sebi i profesoru vreme.
          </p>
          <Button variant="accent" onClick={() => onRoute("ai")}>
            Otvori AI Tutora <Icon name="arrow-right" size={14} />
          </Button>
        </Card>
      </div>

      <div className="section">
        <div className="section-head">
          <h3 className="section-title">Predstojeći termini</h3>
          <button className="link-btn" onClick={() => onRoute("termini")}>
            Svi termini <Icon name="arrow-right" size={12} />
          </button>
        </div>
        <div className="termini-grid">
          {TERMINI.slice(0, 3).map(t => (
            <TerminCard key={t.id} termin={t} onOpen={() => onOpenTermin(t.id)} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------- TERMINI / SEARCH ----------
function TerminiScreen({ onOpenTermin }) {
  const [q, setQ] = useState("");
  const [subject, setSubject] = useState("all");

  const filtered = useMemo(() => TERMINI.filter(t =>
    (subject === "all" || t.subject === subject) &&
    (q === "" || (t.subject + " " + t.professor.name).toLowerCase().includes(q.toLowerCase()))
  ), [q, subject]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Pretraga</div>
          <h1 className="page-title">Termini konsultacija</h1>
          <p className="page-sub">Pretraži objavljene konsultacije po predmetu i datumu, izaberi slobodan slot.</p>
        </div>
      </div>

      <Card className="filter-bar">
        <Field>
          <Input leftIcon="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Pretraži po predmetu ili profesoru..." />
        </Field>
        <Field>
          <Select leftIcon="book-open" value={subject} onChange={(e) => setSubject(e.target.value)}>
            <option value="all">Svi predmeti</option>
            {SUBJECTS.map(s => <option key={s} value={s}>{s}</option>)}
          </Select>
        </Field>
        <Button variant="outline" onClick={() => { setQ(""); setSubject("all"); }}>
          <Icon name="x" size={14} /> Resetuj
        </Button>
      </Card>

      <div className="termini-grid termini-grid-2">
        {filtered.map(t => <TerminCard key={t.id} termin={t} onOpen={() => onOpenTermin(t.id)} />)}
        {filtered.length === 0 && <Card className="empty">Nema rezultata. Pokušaj drugu pretragu.</Card>}
      </div>
    </div>
  );
}

function TerminCard({ termin, onOpen }) {
  const t = termin;
  const full = t.slots === 0;
  return (
    <Card hover className="termin-card" onClick={() => !full && onOpen()}>
      <div className="termin-card-top">
        <div>
          <div className="termin-subject">{t.subject}</div>
          <div className="termin-prof">{t.professor.title} {t.professor.name}</div>
        </div>
        <Badge variant="accent">Q&amp;A</Badge>
      </div>
      <div className="termin-meta">
        <span><Icon name="calendar" size={12} /> {formatDate(t.date)}</span>
        <span><Icon name="clock" size={12} /> {t.start}–{t.end}</span>
      </div>
      <div className="termin-bottom">
        <Badge variant={full ? "destructive" : "secondary"}>
          {full ? "Popunjen" : `${t.slots} ${t.slots === 1 ? "slot" : "slota"}`}
        </Badge>
        <span className="termin-arrow">
          {full ? "Nedostupno" : "Detalji"} {!full && <Icon name="arrow-right" size={12} />}
        </span>
      </div>
    </Card>
  );
}

// ---------- TERMIN DETAIL (reservation flow) ----------
function TerminDetailScreen({ terminId, onBack, onRoute, onConfirm }) {
  const t = TERMINI.find(x => x.id === terminId) || TERMINI[0];
  const slots = useMemo(() => generateSlots(t), [t.id]);
  const [selected, setSelected] = useState(null);
  const [reason, setReason] = useState("");
  const [done, setDone] = useState(false);

  if (done) {
    return (
      <div className="page">
        <Card className="confirm-card">
          <div className="confirm-icon"><Icon name="check" size={28} /></div>
          <h2 className="confirm-title">Slot rezervisan.</h2>
          <p className="confirm-sub">
            {t.subject} · {formatDate(t.date)} · {selected} kod {t.professor.title} {t.professor.name}.
          </p>
          <div className="confirm-actions">
            <Button variant="outline" onClick={onBack}><Icon name="arrow-left" size={14} /> Nazad na termine</Button>
            <Button variant="accent" onClick={() => onRoute("ai")}><Icon name="sparkles" size={14} /> Pripremi pitanje sa AI</Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="page">
      <button className="link-btn back" onClick={onBack}>
        <Icon name="arrow-left" size={12} /> Svi termini
      </button>

      <div className="page-head">
        <div>
          <div className="eyebrow">Termin</div>
          <h1 className="page-title">{t.subject}</h1>
          <p className="page-sub">
            {formatDate(t.date)} · {t.start}–{t.end} · {t.professor.title} {t.professor.name}
          </p>
        </div>
        <Badge variant="accent">{t.slots} slobodnih slotova</Badge>
      </div>

      <div className="detail-grid">
        <Card className="slots-card">
          <h3 className="card-title">Izaberi slot</h3>
          <p className="card-sub">15-minutni intervali u okviru termina.</p>
          <div className="slot-grid">
            {slots.map(s => (
              <button
                key={s.label}
                disabled={s.taken}
                className={`slot ${selected === s.label ? "selected" : ""} ${s.taken ? "taken" : ""}`}
                onClick={() => setSelected(s.label)}
              >
                {s.label}
              </button>
            ))}
          </div>
        </Card>

        <Card className="reason-card">
          <h3 className="card-title">Razlog konsultacije</h3>
          <p className="card-sub">Profesor će videti kratak opis pre termina.</p>
          <textarea
            className="textarea"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="npr. nejasna rekurzija u zadatku 3..."
          />
          <div className="reason-tip">
            <AIMark size={28} />
            <div>
              <div className="reason-tip-title">Probaj AI tutora prvo?</div>
              <div className="reason-tip-sub">AI često reši jednostavne nedoumice odmah, sa procenom pouzdanosti.</div>
            </div>
            <Button variant="ghost" onClick={() => onRoute("ai")}>
              Otvori AI <Icon name="arrow-right" size={12} />
            </Button>
          </div>
        </Card>
      </div>

      <div className="detail-foot">
        <Button variant="outline" onClick={onBack}>Otkaži</Button>
        <Button
          variant="default"
          disabled={!selected}
          onClick={() => setDone(true)}
        >
          Potvrdi rezervaciju <Icon name="arrow-right" size={14} />
        </Button>
      </div>
    </div>
  );
}

// ---------- AI TUTOR ----------
function AITutorScreen() {
  const [messages, setMessages] = useState([
    { role: "ai", text: "Zdravo! Ja sam tvoj AI tutor. Pitaj me bilo šta o gradivu — pre nego što rezervišeš termin sa profesorom.", confidence: null },
  ]);
  const [input, setInput] = useState("Možeš li mi objasniti kako tačno radi rekurzivni poziv kod binary searcha?");
  const [thinking, setThinking] = useState(false);

  const send = () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", text: input };
    setMessages(m => [...m, userMsg]);
    setInput("");
    setThinking(true);
    setTimeout(() => {
      setMessages(m => [...m, {
        role: "ai",
        text: "Ideja je da svaki rekurzivni poziv prepolovi opseg pretrage. Kada je niz sortiran, gledaš srednji element — ako je traženi veći, ideš desno; ako je manji, levo. Stack se gradi do log\u2082(n) dubine, što je razlog zašto je binary search O(log n).",
        confidence: "high",
      }]);
      setThinking(false);
    }, 900);
  };

  return (
    <div className="page ai-page">
      <div className="page-head">
        <div className="ai-page-title-wrap">
          <AIMark size={44} />
          <div>
            <div className="eyebrow">AI Tutor</div>
            <h1 className="page-title">&ldquo;PitajPreZakazivanja&rdquo;</h1>
            <p className="page-sub">Postavi pitanje · dobij odgovor · proceni pouzdanost · zakaži termin samo ako treba.</p>
          </div>
        </div>
      </div>

      <Card className="chat-card">
        <div className="chat-stream">
          {messages.map((m, i) => (
            <div key={i} className={`bubble-row ${m.role === "user" ? "right" : ""}`}>
              {m.role === "ai" && (
                <div className="bubble-who">
                  <Icon name="sparkles" size={12} /> AI Tutor
                </div>
              )}
              <div className={`bubble bubble-${m.role}`}>{m.text}</div>
              {m.confidence === "high" && (
                <div className="bubble-foot">
                  <Badge variant="success"><Icon name="shield-check" size={11} /> Visoka pouzdanost</Badge>
                  <button className="vote-btn"><Icon name="thumbs-up" size={12} /> Jasno</button>
                  <button className="vote-btn"><Icon name="thumbs-down" size={12} /> Nije jasno</button>
                </div>
              )}
            </div>
          ))}
          {thinking && (
            <div className="bubble-row">
              <div className="bubble-who"><Icon name="sparkles" size={12} /> AI Tutor</div>
              <div className="bubble bubble-ai bubble-thinking">
                <span className="dot"></span><span className="dot"></span><span className="dot"></span>
              </div>
            </div>
          )}
        </div>
        <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <textarea
            className="textarea chat-textarea"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Detaljno pitanje za AI tutora..."
            rows={2}
          />
          <Button variant="accent" type="submit">
            <Icon name="send" size={14} /> Pošalji
          </Button>
        </form>
      </Card>
    </div>
  );
}

// ---------- MY RESERVATIONS ----------
function MyReservationsScreen({ onOpenTermin }) {
  const reservations = [
    { ...TERMINI[0], slot: "09:15" },
    { ...TERMINI[1], slot: "11:30" },
  ];
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Rezervacije</div>
          <h1 className="page-title">Moje rezervacije</h1>
          <p className="page-sub">Prati svoje termine i pripremi se sa AI tutorom pre svakog.</p>
        </div>
      </div>

      <div className="rezervacije-list">
        {reservations.map(r => (
          <Card key={r.id} className="rez-card">
            <div className="rez-left">
              <div className="rez-day">
                <div className="rez-month">{formatDate(r.date, "month")}</div>
                <div className="rez-num">{formatDate(r.date, "day")}</div>
              </div>
              <div>
                <div className="rez-subject">{r.subject}</div>
                <div className="rez-prof">{r.professor.title} {r.professor.name}</div>
                <div className="rez-meta">
                  <span><Icon name="clock" size={11} /> {r.slot} · {r.start}–{r.end}</span>
                  <Badge variant="success"><Icon name="check" size={10} /> Potvrđeno</Badge>
                </div>
              </div>
            </div>
            <div className="rez-actions">
              <Button variant="ghost" onClick={() => onOpenTermin(r.id)}>Detalji</Button>
              <Button variant="accent" size="sm"><Icon name="sparkles" size={12} /> Pripremi sa AI</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------- helpers ----------
function formatDate(iso, mode = "long") {
  const months = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "avg", "sep", "okt", "nov", "dec"];
  const monthsLong = ["januar", "februar", "mart", "april", "maj", "jun", "jul", "avgust", "septembar", "oktobar", "novembar", "decembar"];
  const d = new Date(iso);
  if (mode === "month") return months[d.getMonth()];
  if (mode === "day") return d.getDate();
  return `${d.getDate()}. ${monthsLong[d.getMonth()]}`;
}

function generateSlots(termin) {
  const start = parseTime(termin.start);
  const end = parseTime(termin.end);
  const out = [];
  for (let m = start; m < end; m += 15) {
    const label = `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
    const taken = (m === start + 30) || (m === start + 45);
    out.push({ label, taken });
  }
  return out;
}
function parseTime(s) { const [h, m] = s.split(":").map(Number); return h * 60 + m; }
function pad(n) { return String(n).padStart(2, "0"); }

// Export
Object.assign(window, {
  LoginScreen, Dashboard, TerminiScreen, TerminDetailScreen, AITutorScreen, MyReservationsScreen,
  TERMINI, SUBJECTS, PROFESSORS,
});
