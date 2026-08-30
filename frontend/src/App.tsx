import {
  BarChart3,
  BriefcaseBusiness,
  CalendarDays,
  ChevronRight,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react";
import { useState } from "react";
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import Home from "./pages/Home";
import MarketBreadth from "./pages/MarketBreadth";
import SectorRotation from "./pages/SectorRotation";
import StockScreener from "./pages/StockScreener";
import SmartMoney from "./pages/SmartMoney";
import PortfolioReview from "./pages/PortfolioReview";
import GoldSilver from "./pages/GoldSilver";
import Earnings from "./pages/Earnings";

const navigation = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/" },
  { label: "Market Breadth", icon: BarChart3, path: "/market-breadth" },
  { label: "Sector Rotation", icon: TrendingUp, path: "/sector-rotation" },
  { label: "Stock Screener", icon: Search, path: "/stock-screener" },
  { label: "Smart Money", icon: Wallet, path: "/smart-money" },
  { label: "Portfolio", icon: BriefcaseBusiness, path: "/portfolio" },
  { label: "Gold / Silver", icon: TrendingUp, path: "/gold-silver" },
  { label: "Earnings", icon: CalendarDays, path: "/earnings" },
];

function App() {
  return (
    <BrowserRouter>
      <Terminal />
    </BrowserRouter>
  );
}

function Terminal() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#080b12] text-slate-100">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
      />

      <div className="lg:pl-64">
        <Header setSidebarOpen={setSidebarOpen} />

        <main className="p-4 sm:p-6">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/market-breadth" element={<MarketBreadth />} />
            <Route path="/sector-rotation" element={<SectorRotation />} />
            <Route path="/stock-screener" element={<StockScreener />} />
            <Route path="/smart-money" element={<SmartMoney />} />
            <Route path="/portfolio" element={<PortfolioReview />} />
            <Route path="/gold-silver" element={<GoldSilver />} />
            <Route path="/earnings" element={<Earnings />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function Sidebar({
  sidebarOpen,
  setSidebarOpen,
}: {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}) {
  const location = useLocation();

  return (
    <aside
      className={`
        fixed left-0 top-0 z-50 h-screen w-64
        border-r border-slate-800 bg-[#0c1018]
        transition-transform duration-200
        lg:translate-x-0
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
      `}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-slate-800 px-5">
        <Link
          to="/"
          onClick={() => setSidebarOpen(false)}
          className="block"
        >
          <div className="text-lg font-bold tracking-wide">
            DSB <span className="text-cyan-400">CAPITAL</span>
          </div>

          <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
            Omni Terminal
          </div>
        </Link>

        <button
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <X size={20} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-3">
        <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          Terminal
        </div>

        {navigation.map((item) => {
          const Icon = item.icon;

          const active =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);

          return (
            <Link
              key={item.label}
              to={item.path}
              onClick={() => setSidebarOpen(false)}
              className={`
                mb-1 flex w-full items-center gap-3 rounded-lg
                px-3 py-2.5 text-sm transition
                ${
                  active
                    ? "bg-cyan-400/10 text-cyan-400"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                }
              `}
            >
              <Icon size={17} />

              <span>{item.label}</span>

              {active && (
                <ChevronRight
                  size={15}
                  className="ml-auto"
                />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Data mode */}
      <div className="absolute bottom-0 w-full border-t border-slate-800 p-4">
        <div className="rounded-lg bg-slate-900 p-3">
          <div className="text-xs text-slate-500">
            Data mode
          </div>

          <div className="mt-1 flex items-center gap-2 text-sm font-medium">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            EOD
          </div>
        </div>
      </div>
    </aside>
  );
}

function Header({
  setSidebarOpen,
}: {
  setSidebarOpen: (open: boolean) => void;
}) {
  const location = useLocation();

  const currentPage =
    navigation.find((item) =>
      item.path === "/"
        ? location.pathname === "/"
        : location.pathname.startsWith(item.path),
    )?.label ?? "Dashboard";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-800 bg-[#080b12]/95 px-4 backdrop-blur lg:px-6">
      <div className="flex items-center gap-3">
        <button
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 lg:hidden"
          onClick={() => setSidebarOpen(true)}
        >
          <Menu size={21} />
        </button>

        <div>
          <h1 className="text-base font-semibold">
            {currentPage}
          </h1>

          <p className="hidden text-xs text-slate-500 sm:block">
            Indian Equity Market Intelligence
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          NSE · EOD
        </div>

        <button
          className="rounded-lg border border-slate-800 bg-slate-900 p-2 text-slate-400 transition hover:border-slate-700 hover:text-slate-100"
          title="Refresh data"
        >
          <RefreshCw size={17} />
        </button>
      </div>
    </header>
  );
}

export default App;