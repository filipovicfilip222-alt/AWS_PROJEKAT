// =============================================================
// PredZnanje — Shared UI primitives
// All exported to window so app.jsx and screens.jsx can use them.
// =============================================================

const { useState } = React;

// ---- Icon (Lucide-style inline SVG) ----
function Icon({ name, size = 16, className = "", style }) {
  const props = {
    width: size, height: size, viewBox: "0 0 24 24",
    fill: "none", stroke: "currentColor", strokeWidth: 2,
    strokeLinecap: "round", strokeLinejoin: "round",
    className, style,
  };
  switch (name) {
    case "sparkles": return <svg {...props}><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>;
    case "calendar": return <svg {...props}><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>;
    case "clock": return <svg {...props}><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>;
    case "book-open": return <svg {...props}><path d="M2 3h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z"/></svg>;
    case "graduation-cap": return <svg {...props}><path d="M22 10v6"/><path d="M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>;
    case "message-square": return <svg {...props}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>;
    case "search": return <svg {...props}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>;
    case "arrow-right": return <svg {...props}><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>;
    case "arrow-left": return <svg {...props}><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>;
    case "thumbs-up": return <svg {...props}><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H7"/></svg>;
    case "thumbs-down": return <svg {...props}><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H17"/></svg>;
    case "send": return <svg {...props}><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>;
    case "log-out": return <svg {...props}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/></svg>;
    case "x": return <svg {...props}><path d="M18 6 6 18M6 6l12 12"/></svg>;
    case "check": return <svg {...props}><path d="M20 6 9 17l-5-5"/></svg>;
    case "shield-check": return <svg {...props}><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>;
    case "user": return <svg {...props}><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>;
    case "mail": return <svg {...props}><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>;
    case "lock": return <svg {...props}><rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>;
    case "filter": return <svg {...props}><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>;
    case "plus": return <svg {...props}><path d="M5 12h14"/><path d="M12 5v14"/></svg>;
    default: return null;
  }
}

// ---- Logo lockup ----
function Logo({ role = "student" }) {
  return (
    <div className="lockup">
      <span className="lockup-badge">
        <Icon name={role === "professor" ? "book-open" : "graduation-cap"} size={14} />
      </span>
      <span className="lockup-word">PredZnanje</span>
    </div>
  );
}

// ---- AI brand mark ----
function AIMark({ size = 32 }) {
  return (
    <span className="ai-mark" style={{ width: size, height: size }}>
      <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: size * 0.5, height: size * 0.5 }}>
        <path d="M12 2 L13.2 9.4 L20.5 8 L15.6 13.2 L20.5 18.4 L13.2 17 L12 24 L10.8 17 L3.5 18.4 L8.4 13.2 L3.5 8 L10.8 9.4 Z" />
      </svg>
    </span>
  );
}

// ---- Button ----
function Button({ variant = "default", size = "md", children, className = "", ...rest }) {
  const cls = [
    "btn",
    `btn-${variant}`,
    `btn-${size}`,
    className,
  ].filter(Boolean).join(" ");
  return <button className={cls} {...rest}>{children}</button>;
}

// ---- Badge ----
function Badge({ variant = "secondary", children, className = "" }) {
  return <span className={`badge badge-${variant} ${className}`}>{children}</span>;
}

// ---- Card ----
function Card({ children, hover = false, className = "", ...rest }) {
  return <div className={`card ${hover ? "card-hover" : ""} ${className}`} {...rest}>{children}</div>;
}

// ---- Input / Field ----
function Field({ label, hint, children }) {
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

function Input({ leftIcon, ...rest }) {
  if (leftIcon) {
    return (
      <span className="input-wrap">
        <Icon name={leftIcon} size={16} className="input-icon" />
        <input className="input input-with-icon" {...rest} />
      </span>
    );
  }
  return <input className="input" {...rest} />;
}

function Select({ leftIcon, children, ...rest }) {
  if (leftIcon) {
    return (
      <span className="input-wrap">
        <Icon name={leftIcon} size={16} className="input-icon" />
        <select className="input input-with-icon" {...rest}>{children}</select>
      </span>
    );
  }
  return <select className="input" {...rest}>{children}</select>;
}

// ---- Avatar ----
function Avatar({ name = "?", size = 32, tone = "accent" }) {
  const initials = name.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <span className={`avatar avatar-${tone}`} style={{ width: size, height: size, fontSize: size * 0.38 }}>
      {initials}
    </span>
  );
}

// ---- Header (sticky nav) ----
function Header({ user, route, onRoute, onLogout }) {
  const links = [
    { id: "home", label: "Početna" },
    { id: "termini", label: "Termini" },
    { id: "ai", label: "\u201CPitajPreZakazivanja\u201D", featured: true },
    { id: "rezervacije", label: "Moje rezervacije" },
  ];
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <div className="app-header-left">
          <Logo role={user?.role || "student"} />
          <nav className="nav">
            {links.map(l => (
              <button
                key={l.id}
                className={`nav-link ${l.featured ? "nav-link-feat" : ""} ${route === l.id ? "active" : ""}`}
                onClick={() => onRoute(l.id)}
              >
                {l.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="app-header-right">
          <div className="user-chip">
            <Avatar name={user?.name || "Filip Petrović"} size={26} />
            <div className="user-meta">
              <div className="user-name">{user?.name || "Filip Petrović"}</div>
              <div className="user-role">{user?.role === "professor" ? "Profesor" : "Student"}</div>
            </div>
          </div>
          <Button variant="ghost" size="icon" aria-label="Odjava" onClick={onLogout}>
            <Icon name="log-out" size={16} />
          </Button>
        </div>
      </div>
    </header>
  );
}

// Export to window so other Babel scripts can pick them up.
Object.assign(window, {
  Icon, Logo, AIMark,
  Button, Badge, Card,
  Field, Input, Select,
  Avatar, Header,
});
