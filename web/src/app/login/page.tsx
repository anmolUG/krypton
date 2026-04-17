"use client";
import React, { useState } from "react";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function AuthPage() {
  const router = useRouter();
  const [showEmail, setShowEmail] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please enter email and password");
      return;
    }

    setIsLoading(true);
    try {
      const res = await signIn("credentials", {
        redirect: false,
        email,
        password,
      });

      if (res?.error) {
        toast.error("Invalid credentials (try admin@university.edu / password)");
      } else {
        toast.success("Successfully logged in");
        router.push("/dashboard");
      }
    } catch (error) {
      toast.error("Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    signIn("google", { callbackUrl: "/dashboard" });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center text-white px-4">
      {/* Container for the content */}
      <div className="w-full max-w-[400px] flex flex-col items-center space-y-8 relative overflow-hidden">
        
        {/* Logo & Branding */}
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-white rounded-md flex items-center justify-center">
            <span className="text-black font-bold text-xl leading-none">A</span>
          </div>
          <span className="text-lg font-medium tracking-tight">Krypton</span>
        </div>

        {/* Heading */}
        <h1 className="text-4xl font-bold tracking-tight text-center">
          {showEmail ? "Sign in with email" : "Sign in to your account"}
        </h1>

        {/* Dynamic Content Area */}
        <div className="w-full relative min-h-[180px]">
          {/* Default Social View */}
          <div className={`w-full absolute inset-0 flex flex-col transition-all duration-300 transform ${showEmail ? '-translate-x-full opacity-0 pointer-events-none' : 'translate-x-0 opacity-100'}`}>
            <div className="w-full space-y-4">
              <Button 
                variant="outline" 
                onClick={handleGoogleLogin}
                className="w-full h-12 border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-300 transition-all duration-200"
              >
                <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
                  <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
                </svg>
                <span className="text-sm">Login with Google</span>
              </Button>
              
              {/* Divider */}
              <div className="w-full border-t border-neutral-900 my-4" />

              {/* Main Action Button */}
              <Button 
                onClick={() => setShowEmail(true)}
                className="w-full h-12 bg-white text-black hover:bg-neutral-200 font-medium transition-all duration-200"
              >
                Continue with Email
              </Button>
            </div>
          </div>

          {/* Email Form View */}
          <div className={`w-full absolute inset-0 flex flex-col transition-all duration-300 transform ${showEmail ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0 pointer-events-none'}`}>
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-neutral-400">Email</Label>
                <Input 
                  id="email" 
                  type="email" 
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@university.edu" 
                  className="bg-neutral-900/50 border-neutral-800 text-white h-12 focus-visible:ring-neutral-700" 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-neutral-400">Password</Label>
                <Input 
                  id="password" 
                  type="password" 
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="bg-neutral-900/50 border-neutral-800 text-white h-12 focus-visible:ring-neutral-700" 
                />
              </div>
              <div className="flex gap-2 pt-2">
                <Button 
                  type="button"
                  variant="outline"
                  onClick={() => setShowEmail(false)}
                  className="h-12 w-12 shrink-0 border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-300 p-0 flex items-center justify-center"
                >
                  <ArrowLeft size={18} />
                </Button>
                <Button 
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 h-12 bg-white text-black hover:bg-neutral-200 font-medium transition-all duration-200"
                >
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Sign In"}
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Footer Link */}
        <p className="text-neutral-500 text-sm mt-8 transition-opacity duration-300" style={{ opacity: showEmail ? 0 : 1 }}>
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-white hover:underline transition-all">
            Sign up
          </Link>
        </p>

      </div>
    </div>
  );
}
