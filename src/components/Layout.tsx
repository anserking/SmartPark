import { Link, Outlet, useLocation } from 'react-router-dom';
import { MapPin, ShieldCheck } from 'lucide-react';

const navigation = [
  { name: 'Find parking', href: '/dashboard', icon: MapPin },
  { name: 'Admin', href: '/admin', icon: ShieldCheck },
];

export default function Layout() {
  const location = useLocation();
  const isDashboard = location.pathname === '/dashboard';

  return (
    <div className="min-h-screen bg-background">
      <header className="relative z-[1100] flex h-14 items-center justify-between border-b border-[#ded8c9] bg-[#fffdf8] px-4 sm:px-6">
        <Link
          to="/dashboard"
          className="flex min-h-11 items-center gap-2 rounded-md text-[#273b2b] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#496348]"
        >
          <span className="grid h-8 w-8 place-items-center rounded-full bg-[#496348] text-white">
            <MapPin aria-hidden="true" className="h-4 w-4" />
          </span>
          <span className="text-lg font-semibold tracking-tight">SmartPark</span>
        </Link>
        <nav aria-label="Main navigation" className="flex items-center gap-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.href}
                to={item.href}
                aria-current={isActive ? 'page' : undefined}
                className={`flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#496348] ${
                  isActive
                    ? 'bg-[#e7e5d7] text-[#273b2b]'
                    : 'text-[#625d51] hover:bg-[#f1eee5] hover:text-[#273b2b]'
                }`}
              >
                <Icon aria-hidden="true" className="h-4 w-4" />
                <span className="hidden sm:inline">{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </header>
      <main
        className={
          isDashboard
            ? 'h-[calc(100dvh-3.5rem)] overflow-hidden'
            : 'mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8'
        }
      >
        <Outlet />
      </main>
    </div>
  );
}
