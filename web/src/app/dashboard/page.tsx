"use client";

import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Users, 
  BarChart3, 
  Calendar, 
  TrendingUp, 
  ChevronRight,
  Clock,
  MapPin,
  Activity
} from "lucide-react";
import { motion } from "framer-motion";

export default function DashboardPage() {
  const [stats, setStats] = React.useState({
    students: "...",
    sessions: "12",
    attendance: "84%",
    lastSync: "Just now"
  });

  // Fetch real stats from Backend
  React.useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/registry`);
        if (res.ok) {
          const data = await res.json();
          setStats(prev => ({ ...prev, students: data.total.toString() }));
        }
      } catch (err) {
        console.error("Failed to fetch backend stats:", err);
      }
    }
    fetchStats();
  }, []);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/60 bg-clip-text text-transparent">
            Researcher Dashboard
          </h2>
          <p className="text-muted-foreground">Real-time classroom monitoring & biometric analytics.</p>
        </div>
        <div className="text-right hidden md:block">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-widest">Last Intelligence Sync</p>
          <p className="text-sm font-bold text-primary">{stats.lastSync}</p>
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard 
          label="Total Students" 
          value={stats.students} 
          icon={<Users className="text-blue-500" size={20} />} 
          change="+2 new this week" 
        />
        <StatsCard 
          label="Sessions Logged" 
          value={stats.sessions} 
          icon={<Activity className="text-emerald-500" size={20} />} 
          change="Last 30 days" 
        />
        <StatsCard 
          label="Avg. Attendance" 
          value={stats.attendance} 
          icon={<TrendingUp className="text-orange-500" size={20} />} 
          change="+3% vs last term" 
        />
        <StatsCard 
          label="System Health" 
          value="Optimal" 
          icon={<BarChart3 className="text-purple-500" size={20} />} 
          change="AI Models Active" 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Main Analytics Card - The requested section */}
        <Card className="lg:col-span-8 border-border shadow-xl overflow-hidden group">
          <CardHeader className="pb-4">
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-xl font-bold tracking-tight">Smart Attendance Analytics</CardTitle>
                <CardDescription>Visual summary of attendance trends over the semester.</CardDescription>
              </div>
              <Button size="sm" variant="ghost" className="text-xs gap-2">
                Export Data <ChevronRight size={14} />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="relative h-[300px] rounded-2xl bg-[#0b0b0d] border border-white/5 flex flex-col items-center justify-center overflow-hidden">
              {/* Chart background elements */}
              <div className="absolute inset-0 opacity-10">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#18181b_1px,transparent_1px),linear-gradient(to_bottom,#18181b_1px,transparent_1px)] bg-[size:40px_40px]" />
              </div>
              
              <AttendanceChart />
              
              {/* Sample labels */}
              <div className="absolute bottom-4 left-0 right-0 flex justify-around px-8">
                {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(d => (
                  <span key={d} className="text-[10px] font-mono text-white/30 uppercase">{d}</span>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Schedule Sidebar */}
        <Card className="lg:col-span-4 border-border shadow-md">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Calendar className="text-primary" size={18} />
              Upcoming Sessions
            </CardTitle>
            <CardDescription>Automated recording schedule.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ScheduleItem 
              time="10:00 AM" 
              subject="Computer Vision III" 
              room="Lab 4A" 
              icon={<Clock size={12} className="text-blue-500" />}
            />
            <ScheduleItem 
              time="01:30 PM" 
              subject="ML Research Seminar" 
              room="Room 202" 
              icon={<Clock size={12} className="text-emerald-500" />}
            />
            <ScheduleItem 
              time="03:00 PM" 
              subject="Physics Lab" 
              room="Science Wing" 
              icon={<Clock size={12} className="text-orange-500" />}
            />
            
            <div className="pt-4">
              <button className="w-full py-2.5 text-xs font-semibold rounded-xl bg-accent hover:bg-accent/80 transition-colors border border-border/50">
                View All Calendars
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatsCard({ label, value, change, icon }: { label: string, value: string, change: string, icon: React.ReactNode }) {
  return (
    <Card className="relative border-border shadow-sm hover:shadow-xl transition-all duration-300 group overflow-hidden">
      <div className="absolute top-0 right-0 p-4 opacity-20 group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      <CardHeader className="py-5">
        <CardDescription className="text-xs font-medium uppercase tracking-wider">{label}</CardDescription>
        <CardTitle className="text-3xl font-extrabold tracking-tight">{value}</CardTitle>
      </CardHeader>
      <CardContent className="pb-5">
        <div className="flex items-center gap-1.5">
          <div className="h-1 w-1 rounded-full bg-primary" />
          <p className="text-[10px] text-muted-foreground font-medium">{change}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ScheduleItem({ time, subject, room, icon }: { time: string, subject: string, room: string, icon: React.ReactNode }) {
  return (
    <div className="group flex items-center justify-between p-3 rounded-xl border border-border/50 bg-accent/20 hover:bg-accent/40 transition-all cursor-default">
      <div className="space-y-1">
        <p className="text-sm font-bold group-hover:text-primary transition-colors">{subject}</p>
        <div className="flex items-center gap-2">
          <MapPin size={10} className="text-muted-foreground" />
          <p className="text-[10px] text-muted-foreground font-medium">{room}</p>
        </div>
      </div>
      <div className="flex flex-col items-end gap-1">
        <div className="px-2 py-0.5 bg-background border border-border rounded text-[9px] font-bold text-foreground shadow-sm">
          {time}
        </div>
        <div className="flex items-center gap-1">
          {icon}
          <span className="text-[8px] uppercase font-bold text-muted-foreground">Auto-Rec</span>
        </div>
      </div>
    </div>
  );
}

function Button({ size, variant, className, children, ...props }: any) {
  const sizeClasses = size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm";
  const variantClasses = variant === "ghost" ? "hover:bg-accent" : "bg-primary text-primary-foreground";
  
  return (
    <button className={`inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 ${sizeClasses} ${variantClasses} ${className}`} {...props}>
      {children}
    </button>
  );
}

function AttendanceChart() {
  // Sample data points for the week
  const data = [45, 78, 52, 91, 74, 85, 95];
  const max = 100;
  const height = 180;
  const width = 600;
  const spacing = width / (data.length - 1);

  // Generate path for the area chart
  const points = data.map((val, i) => `${i * spacing},${height - (val / max) * height}`).join(" ");
  const areaPath = `0,${height} ${points} ${width},${height}`;
  const linePath = points;

  return (
    <div className="relative w-full h-[220px] px-8 py-4">
      <svg 
        viewBox={`0 0 ${width} ${height}`} 
        className="w-full h-full overflow-visible drop-shadow-[0_0_15px_rgba(59,130,246,0.2)]"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Animated Area */}
        <motion.polygon
          initial={{ opacity: 0, scaleY: 0 }}
          animate={{ opacity: 1, scaleY: 1 }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          style={{ originY: "100%" }}
          points={areaPath}
          fill="url(#chartGradient)"
        />

        {/* Animated Line */}
        <motion.polyline
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 2, ease: "easeInOut" }}
          points={linePath}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data Points */}
        {data.map((val, i) => (
          <motion.circle
            key={i}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 1 + i * 0.1, duration: 0.3 }}
            cx={i * spacing}
            cy={height - (val / max) * height}
            r="4"
            fill="#0b0b0d"
            stroke="#3b82f6"
            strokeWidth="2"
          />
        ))}
      </svg>
      
      {/* Floating high-score tag */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 2.2 }}
        className="absolute top-0 right-14 px-2 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-[9px] font-bold text-emerald-400 flex items-center gap-1"
      >
        <TrendingUp size={10} />
        PEAK: 95%
      </motion.div>
    </div>
  );
}
