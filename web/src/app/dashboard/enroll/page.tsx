"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, CheckCircle2, UserPlus, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { toast } from "sonner";

export default function EnrollStudentPage() {
  const [name, setName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      const validFiles = selectedFiles.filter(f => f.type.startsWith('image/'));
      
      if (validFiles.length !== selectedFiles.length) {
        toast.error("Some files were rejected. Please upload only images.");
      }
      
      setFiles(prev => [...prev, ...validFiles]);
    }
  };

  React.useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (e.clipboardData && e.clipboardData.files.length > 0) {
        const pastedFiles = Array.from(e.clipboardData.files);
        const validFiles = pastedFiles.filter(f => f.type.startsWith('image/'));
        if (validFiles.length > 0) {
          setFiles(prev => [...prev, ...validFiles]);
          toast.success(`${validFiles.length} image(s) pasted from clipboard`);
        }
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, []);

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      const validFiles = droppedFiles.filter(f => f.type.startsWith('image/'));
      setFiles(prev => [...prev, ...validFiles]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      toast.error("Please provide a student name.");
      return;
    }
    
    if (files.length === 0) {
      toast.error("Please upload at least one clear face photo.");
      return;
    }

    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append("student_name", name);
      files.forEach(file => {
        formData.append("files", file);
      });

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enroll`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        toast.success(`Successfully enrolled ${name}!`);
        setName("");
        setFiles([]);
      } else {
        toast.error(data.detail || data.message || "Failed to enroll student.");
      }
    } catch (error) {
      console.error(error);
      toast.error("Network error. Make sure the Python backend is running.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-4xl w-full mx-auto">
      <div>
        <h2 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <UserPlus className="text-primary" />
          Enroll New Student
        </h2>
        <p className="text-muted-foreground">Add reference face images to the Smart Attendance Gallery.</p>
      </div>

      <Card className="border-border shadow-md">
        <form onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle>Student Information</CardTitle>
            <CardDescription>Upload multiple clear, front-facing photos for highest accuracy.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            
            {/* Name Input */}
            <div className="space-y-2">
              <Label htmlFor="student-name">Full Name</Label>
              <Input 
                id="student-name" 
                placeholder="e.g., Jane Smith" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="max-w-md bg-background/50"
              />
            </div>

            {/* Drag & Drop Area */}
            <div className="space-y-2">
              <Label>Reference Photos</Label>
              <div 
                tabIndex={0}
                className={`
                  border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50
                  hover:bg-accent/50 hover:border-primary/50
                  ${files.length > 0 ? "border-primary/30 bg-accent/20" : "border-border bg-background/30"}
                `}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onPaste={(e: React.ClipboardEvent) => {
                  if (e.clipboardData && e.clipboardData.files.length > 0) {
                    const pastedFiles = Array.from(e.clipboardData.files);
                    const validFiles = pastedFiles.filter(f => f.type.startsWith('image/'));
                    if (validFiles.length > 0) {
                      setFiles(prev => [...prev, ...validFiles]);
                      toast.success(`${validFiles.length} image(s) pasted!`);
                    }
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4 text-primary">
                  <UploadCloud className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-medium">Click, drag, or Ctrl+V to paste photos</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                  JPG, JPEG, or PNG images. Upload 2-3 angles of the student's face for best results.
                </p>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  multiple 
                  accept="image/jpeg,image/png,image/jpg"
                  onChange={handleFileChange}
                />
              </div>
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="space-y-3 pt-4">
                <p className="text-sm font-medium">{files.length} file(s) selected</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {files.map((file, index) => (
                    <div key={index} className="relative group bg-background rounded-lg border border-border p-2 flex items-center gap-3">
                      <div className="h-10 w-10 shrink-0 bg-muted rounded-md overflow-hidden flex items-center justify-center">
                        <img 
                          src={URL.createObjectURL(file)} 
                          alt="preview" 
                          className="h-full w-full object-cover"
                          onLoad={(e) => URL.revokeObjectURL((e.target as HTMLImageElement).src)}
                        />
                      </div>
                      <p className="text-xs truncate flex-1">{file.name}</p>
                      <button 
                        type="button" 
                        onClick={(e) => { e.stopPropagation(); removeFile(index); }}
                        className="absolute -top-2 -right-2 h-6 w-6 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </CardContent>
          <CardFooter className="bg-muted/20 border-t border-border px-6 py-4">
            <Button type="submit" disabled={isUploading || !name || files.length === 0} className="w-full sm:w-auto ml-auto">
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating Embeddings...
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Enroll Student
                </>
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
