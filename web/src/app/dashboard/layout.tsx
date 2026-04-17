"use client";

import React from "react";
import { useSession, signOut } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Users, 
  UserPlus,
  Video, 
  BarChart3, 
  Settings, 
  LogOut, 
  LayoutDashboard,
  Bell,
  Search
} from "lucide-react";
import { Input } from "@/components/ui/input";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return <div className="h-screen flex items-center justify-center bg-background text-foreground animate-pulse">Loading Researcher Profile...</div>;
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden text-foreground">
      {/* Persistent Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Krypton Analytics
          </h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 py-4">
          <NavItem href="/dashboard" icon={<LayoutDashboard size={20} />} label="Smart Dashboard" active={pathname === "/dashboard"} />
          <NavItem href="/dashboard/registry" icon={<Users size={20} />} label="Student Registry" active={pathname === "/dashboard/registry"} />
          <NavItem href="/dashboard/enroll" icon={<UserPlus size={20} />} label="Enroll Student" active={pathname === "/dashboard/enroll"} />
          <NavItem href="/dashboard/analyze" icon={<Video size={20} />} label="Classroom Analysis" active={pathname === "/dashboard/analyze"} />
        </nav>

        <div className="p-4 border-t border-border space-y-2">
          <NavItem href="/dashboard" icon={<Settings size={20} />} label="Settings" />
          <button 
            onClick={() => signOut()}
            className="flex items-center gap-3 px-4 py-2 w-full text-left text-sm font-medium rounded-lg text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut size={20} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col bg-background/50 overflow-hidden">
        {/* Persistent Header */}
        <header className="h-16 border-b border-border bg-card/40 backdrop-blur-md flex items-center justify-between px-8 shrink-0">
          <div className="relative w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
            <Input 
              placeholder="Search researchers, students or sessions..." 
              className="pl-10 bg-background/50 border-none shadow-none focus-visible:ring-1 h-9"
            />
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2 rounded-full hover:bg-accent relative text-muted-foreground">
              <Bell size={20} />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full" />
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-border">
              <div className="text-right">
                <p className="text-xs font-medium">{session?.user?.name || "Dr. Researcher"}</p>
                <p className="text-[10px] text-muted-foreground">{session?.user?.email || "research@university.edu"}</p>
              </div>
              <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                {session?.user?.name?.[0]?.toUpperCase() || "R"}
              </div>
            </div>
          </div>
        </header>

        {/* Dynamic Page Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

function NavItem({ href, icon, label, active = false }: { href: string, icon: React.ReactNode, label: string, active?: boolean }) {
  return (
    <Link href={href} className={`
      flex items-center gap-3 px-4 py-2 w-full text-left text-sm font-medium rounded-lg transition-all duration-200
      ${active 
        ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" 
        : "text-muted-foreground hover:bg-accent hover:text-foreground"}
    `}>
      {icon}
      {label}
    </Link>
  );
}
