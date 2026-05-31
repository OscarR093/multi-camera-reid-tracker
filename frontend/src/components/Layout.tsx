import { Outlet, NavLink } from 'react-router-dom'
import CountBadge from './CountBadge'

const navItems = [
  { to: '/', label: 'Live View', end: true },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/blacklist', label: 'Blacklist' },
  { to: '/admin', label: 'Admin' },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <h1 className="text-lg font-bold text-white tracking-tight">
            CamCount
          </h1>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-300 hover:text-white hover:bg-slate-700'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <CountBadge />
      </header>

      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
