// =============================================================
// PredZnanje — App entry: state + routing
// =============================================================

const { useState } = React;

function App() {
  const [user, setUser] = useState(null);
  const [route, setRoute] = useState("home");
  const [terminId, setTerminId] = useState(null);

  if (!user) {
    return <LoginScreen onLogin={(u) => setUser(u)} />;
  }

  const goto = (r) => { setRoute(r); setTerminId(null); };
  const openTermin = (id) => { setTerminId(id); setRoute("detail"); };

  return (
    <div className="app">
      <Header
        user={user}
        route={route}
        onRoute={goto}
        onLogout={() => setUser(null)}
      />
      <main className="app-main">
        {route === "home" && <Dashboard user={user} onRoute={goto} onOpenTermin={openTermin} />}
        {route === "termini" && <TerminiScreen onOpenTermin={openTermin} />}
        {route === "detail" && <TerminDetailScreen terminId={terminId} onBack={() => goto("termini")} onRoute={goto} />}
        {route === "ai" && <AITutorScreen />}
        {route === "rezervacije" && <MyReservationsScreen onOpenTermin={openTermin} />}
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
