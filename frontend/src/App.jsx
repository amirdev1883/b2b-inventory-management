import { useState } from 'react';
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Boxes,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Settings2,
  ShieldCheck,
  Truck,
  Users,
  X,
} from 'lucide-react';
import { useSession } from './session';
import { initials, label } from './utils';
import { ErrorBanner, Spinner } from './ui';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Inventory from './pages/Inventory';
import Suppliers from './pages/Suppliers';
import Orders from './pages/Orders';
import Activity from './pages/Activity';
import Team from './pages/Team';
import Settings from './pages/Settings';
import Account from './pages/Account';

const links = [
  ['/', 'Overview', LayoutDashboard],
  ['/inventory', 'Inventory', Boxes],
  ['/sales', 'Sales orders', ArrowUpFromLine],
  ['/purchases', 'Purchase orders', ArrowDownToLine],
  ['/suppliers', 'Suppliers', Truck],
  ['/activity', 'Stock activity', ChartNoAxesCombined],
];
export default function App() {
  const { session, loading, error, isAdmin, signOut } = useSession();
  const [navOpen, setNavOpen] = useState(false);
  const [logoutError, setLogoutError] = useState(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const location = useLocation();
  if (loading)
    return (
      <div className="boot">
        <Spinner />
      </div>
    );
  if (!session) return <Auth startupError={error} />;
  const title =
    [...links, ['/team', 'Team'], ['/settings', 'Settings'], ['/account', 'My account']].find(
      ([path]) => path === location.pathname,
    )?.[1] || 'Workspace';
  async function logout() {
    setLoggingOut(true);
    try {
      await signOut();
    } catch (error) {
      setLogoutError(error);
    } finally {
      setLoggingOut(false);
    }
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      {navOpen && (
        <button
          className="nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        />
      )}
      <aside className={`sidebar ${navOpen ? 'open' : ''}`}>
        <NavLink to="/" className="brand" onClick={() => setNavOpen(false)}>
          <span className="brand-mark">
            <Package size={25} />
          </span>
          <span>
            stockroom<span className="brand-dot">.</span>
            <small>BUSINESS WORKSPACE</small>
          </span>
        </NavLink>
        <button
          className="mobile-close icon-button"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        >
          <X size={20} />
        </button>
        <div className="business-switch">
          <div className="business-avatar">{session.business.name[0]}</div>
          <div>
            <strong>{session.business.name}</strong>
            <span>{session.business.currency} workspace</span>
          </div>
          <ShieldCheck size={16} />
        </div>
        <p className="nav-label">OPERATIONS</p>
        <nav aria-label="Main navigation">
          {links.map(([path, text, Icon]) => (
            <NavLink key={path} to={path} end={path === '/'} onClick={() => setNavOpen(false)}>
              <Icon size={19} />
              <span>{text}</span>
              <ChevronRight size={14} className="nav-chevron" />
            </NavLink>
          ))}
          {isAdmin && (
            <>
              <p className="nav-label">ADMINISTRATION</p>
              <NavLink to="/team" onClick={() => setNavOpen(false)}>
                <Users size={19} />
                <span>Team members</span>
              </NavLink>
              <NavLink to="/settings" onClick={() => setNavOpen(false)}>
                <Settings2 size={19} />
                <span>Business settings</span>
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <a className="docs-link" href="/api/docs/" target="_blank" rel="noreferrer">
            <CircleHelp size={18} />
            API documentation
            <ChevronRight size={14} />
          </a>
          <NavLink className="docs-link" to="/account" onClick={() => setNavOpen(false)}>
            My account
            <ChevronRight size={14} />
          </NavLink>
          <div className="sidebar-user">
            <span className="avatar">{initials(session.user)}</span>
            <div>
              <strong>{session.user.first_name || session.user.email}</strong>
              <small>{label(session.user.role)}</small>
            </div>
            <button aria-label="Sign out" disabled={loggingOut} onClick={logout}>
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              onClick={() => setNavOpen(true)}
            >
              <Menu size={22} />
            </button>
            <span className="muted">Workspace</span>
            <ChevronRight size={14} />
            <strong>{title}</strong>
          </div>
          <span className="workspace-status">
            <span />
            {session.business.currency} · {label(session.user.role)}
          </span>
        </header>
        <main id="main">
          <ErrorBanner error={logoutError} />
          <Routes>
            <Route path="/account" element={<Account />} />
            <Route path="/" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/sales" element={<Orders kind="sales" key="sales" />} />
            <Route path="/purchases" element={<Orders kind="purchase" key="purchase" />} />
            <Route path="/activity" element={<Activity />} />
            <Route path="/team" element={isAdmin ? <Team /> : <Navigate to="/" replace />} />
            <Route
              path="/settings"
              element={isAdmin ? <Settings /> : <Navigate to="/" replace />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="app-footer">
          Stockroom <span>Built for your everyday operations.</span>
        </footer>
      </div>
    </div>
  );
}
