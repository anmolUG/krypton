"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function SignupPage() {
  const router = useRouter();
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: ""
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [e.target.id]: e.target.value }));
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Front-end validations
    if (!formData.name || !formData.email || !formData.password || !formData.confirmPassword) {
      toast.error("Please fill in all fields.");
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    if (formData.password.length < 8) {
      toast.error("Password must be at least 8 characters long.");
      return;
    }

    if (!/[A-Z]/.test(formData.password)) {
      toast.error("Password must contain at least one capital letter.");
      return;
    }

    if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
      toast.error("Password must contain at least one special character.");
      return;
    }

    setIsLoading(true);

    try {
      // 1. Register the user
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          password: formData.password
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        toast.error(data.message || "Something went wrong during registration.");
        setIsLoading(false);
        return;
      }

      toast.success("Account created successfully!");

      // 2. Automatically log them in
      const loginRes = await signIn("credentials", {
        redirect: false,
        email: formData.email,
        password: formData.password,
      });

      if (loginRes?.error) {
        toast.error("Registration succeeded, but login failed. Please sign in manually.");
        router.push("/login");
      } else {
        router.push("/dashboard");
      }
    } catch (error) {
      toast.error("Network error. Please try again.");
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    signIn("google", { callbackUrl: "/dashboard" });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center text-white px-4 py-8 overflow-y-auto">
      <div className="w-full max-w-[400px] flex flex-col items-center space-y-8 relative">
        
        {/* Logo & Branding */}
        <div className="flex items-center space-x-2 shrink-0">
          <div className="w-8 h-8 bg-white rounded-md flex items-center justify-center">
            <span className="text-black font-bold text-xl leading-none">A</span>
          </div>
          <span className="text-lg font-medium tracking-tight">Krypton</span>
        </div>

        {/* Heading */}
        <h1 className="text-4xl font-bold tracking-tight text-center shrink-0">
          {showEmailForm ? "Create with email" : "Create your account"}
        </h1>

        <div className="w-full relative min-h-[180px]">
          {/* Default Social View */}
          <div className={`w-full flex flex-col transition-all duration-300 transform ${showEmailForm ? '-translate-x-full opacity-0 pointer-events-none absolute inset-0' : 'translate-x-0 opacity-100 relative'}`}>
            <div className="w-full space-y-4">
              <Button 
                variant="outline" 
                onClick={handleGoogleLogin}
                className="w-full h-12 border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-300 transition-all duration-200"
              >
                <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
                  <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
                </svg>
                <span className="text-sm">Sign up with Google</span>
              </Button>
              
              <div className="w-full border-t border-neutral-900 my-4" />

              <Button 
                onClick={() => setShowEmailForm(true)}
                className="w-full h-12 bg-white text-black hover:bg-neutral-200 font-medium transition-all duration-200"
              >
                Sign up with Email
              </Button>
            </div>
          </div>

          {/* Email Registration Form */}
          <div className={`w-full flex flex-col transition-all duration-300 transform ${showEmailForm ? 'translate-x-0 opacity-100 relative' : 'translate-x-full opacity-0 pointer-events-none absolute inset-0'}`}>
            <form onSubmit={handleSignup} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-neutral-400">Full Name</Label>
                <Input 
                  id="name" 
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Dr. John Doe" 
                  className="bg-neutral-900/50 border-neutral-800 text-white h-12 focus-visible:ring-neutral-700" 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email" className="text-neutral-400">Email Address</Label>
                <Input 
                  id="email" 
                  type="email" 
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="name@university.edu" 
                  className="bg-neutral-900/50 border-neutral-800 text-white h-12 focus-visible:ring-neutral-700" 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-neutral-400">Password</Label>
                <Input 
                  id="password" 
                  type="password" 
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Min 8 chars, 1 capital, 1 special"
                  className="bg-neutral-900/50 border-neutral-800 text-white h-12 focus-visible:ring-neutral-700" 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-neutral-400">Confirm Password</Label>
                <Input 
                  id="confirmPassword" 
                  type="password" 
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="bg-neutral-900/50 border-neutral-800 text-white h-12 focus-visible:ring-neutral-700" 
                />
              </div>
              
              <div className="flex gap-2 pt-2 pb-4">
                <Button 
                  type="button"
                  variant="outline"
                  onClick={() => setShowEmailForm(false)}
                  className="h-12 w-12 shrink-0 border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-300 p-0 flex items-center justify-center"
                >
                  <ArrowLeft size={18} />
                </Button>
                <Button 
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 h-12 bg-white text-black hover:bg-neutral-200 font-medium transition-all duration-200"
                >
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Create Account"}
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Footer Link */}
        <p className={`text-neutral-500 text-sm mt-8 transition-opacity duration-300 ${showEmailForm ? 'pb-8' : ''}`} style={{ opacity: showEmailForm ? 1 : 1 }}>
          Already have an account?{" "}
          <Link href="/login" className="text-white hover:underline transition-all">
            Log in
          </Link>
        </p>

      </div>
    </div>
  );
}
