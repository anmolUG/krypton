"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileImage, Loader2, Search, Users, Video } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

export default function AnalyzeClassroomPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [attendanceRecords, setAttendanceRecords] = useState<any[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (!selectedFile.type.startsWith('image/')) {
        toast.error("Please upload an image file.");
        return;
      }
      setFile(selectedFile);
      setResultImage(null); // Clear previous results
      setAttendanceRecords([]);
    }
  };

  React.useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (e.clipboardData && e.clipboardData.files.length > 0) {
        const pastedFile = e.clipboardData.files[0];
        if (pastedFile.type.startsWith('image/')) {
          setFile(pastedFile);
          setResultImage(null);
          setAttendanceRecords([]);
          toast.success("Image pasted from clipboard");
        }
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (!droppedFile.type.startsWith('image/')) {
        toast.error("Please drop an image file.");
        return;
      }
      setFile(droppedFile);
      setResultImage(null);
      setAttendanceRecords([]);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;

    setIsAnalyzing(true);
    setResultImage(null);
    setAttendanceRecords([]);
    
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/analyze`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        toast.success("Analysis complete!");
        
        // Base64 string from python comes without the prefix
        if (data.annotated_image_base64) {
          setResultImage(`data:image/jpeg;base64,${data.annotated_image_base64}`);
        }
        
        const newRecords: any[] = [];

        // 1. Process Enrolled Students (Present & Absent)
        if (data.full_attendance?.attendance) {
          data.full_attendance.attendance.forEach((student: any) => {
            if (student.present) {
              newRecords.push({
                name: student.student_name,
                distance: student.confidence,
                status: student.status === "HIGH_CONFIDENCE" ? "PRESENT" : "TENTATIVE",
                badgeStyle: student.status === "HIGH_CONFIDENCE" 
                  ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" 
                  : "bg-blue-500/10 text-blue-500 border-blue-500/20",
                dotStyle: student.status === "HIGH_CONFIDENCE" ? "bg-emerald-500" : "bg-blue-500",
                position: `Row ${student.row || "?"}, Col ${student.column || "?"}`
              });
            } else {
              newRecords.push({
                name: student.student_name,
                distance: null,
                status: "ABSENT",
                badgeStyle: "bg-red-500/10 text-red-500 border-red-500/20",
                dotStyle: "bg-red-500",
                position: "N/A"
              });
            }
          });
        }

        setAttendanceRecords(newRecords);
      } else {
        toast.error(data.detail || "Failed to analyze image.");
      }
    } catch (error) {
      console.error(error);
      toast.error("Network error. Make sure the Python backend is running.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-6xl w-full mx-auto">
      <div>
        <h2 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Video className="text-primary" />
          Classroom Analysis
        </h2>
        <p className="text-muted-foreground">Upload a classroom photo to instantly identify students and mark attendance.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Upload area */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="border-border shadow-md">
            <CardHeader>
              <CardTitle>Session Upload</CardTitle>
              <CardDescription>Select an image to process.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div 
                tabIndex={0}
                className={`
                  border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50
                  hover:bg-accent/50 hover:border-primary/50
                  ${file ? "border-primary/30 bg-accent/20" : "border-border bg-background/30"}
                `}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onPaste={(e: React.ClipboardEvent) => {
                  if (e.clipboardData && e.clipboardData.files.length > 0) {
                    const pastedFile = e.clipboardData.files[0];
                    if (pastedFile.type.startsWith('image/')) {
                      setFile(pastedFile);
                      setResultImage(null);
                      setAttendanceRecords([]);
                      toast.success("Image pasted!");
                    }
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                {file ? (
                  <>
                    <div className="h-12 w-12 rounded-full bg-primary/20 flex items-center justify-center mb-4 text-primary">
                      <FileImage className="h-6 w-6" />
                    </div>
                    <h3 className="text-sm font-medium break-all">{file.name}</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      {(file.size / 1024 / 1024).toFixed(2)} MB • Click to change
                    </p>
                  </>
                ) : (
                  <>
                    <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4 text-primary">
                      <UploadCloud className="h-6 w-6" />
                    </div>
                    <h3 className="text-sm font-medium">Capture, Upload, or Ctrl+V</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Drag or paste photo here
                    </p>
                  </>
                )}
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept="image/jpeg,image/png,image/jpg"
                  onChange={handleFileChange}
                />
              </div>

              <Button 
                onClick={handleAnalyze} 
                className="w-full h-12 text-md" 
                disabled={!file || isAnalyzing}
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Running Neural Network...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-5 w-5" />
                    Analyze Classroom
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Quick Stats side panel */}
          {attendanceRecords.length > 0 && (
            <Card className="border-border shadow-md bg-primary/5 border-primary/20">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary" />
                  Live Roster
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{attendanceRecords.length}</div>
                <p className="text-xs text-muted-foreground">Students identified in this frame</p>
              </CardContent>
            </Card>
          )}

        </div>

        {/* Right Column: Results Display */}
        <div className="lg:col-span-8">
          <Card className="border-border shadow-md h-full flex flex-col">
            <CardHeader>
              <CardTitle>Vision Output</CardTitle>
              <CardDescription>Processed frame with bounding boxes and matched identities.</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col space-y-6">
              
              {/* Image Result */}
              <div className="w-full bg-black/40 rounded-xl border border-border/50 overflow-hidden relative flex-1 min-h-[400px] flex items-center justify-center">
                {isAnalyzing ? (
                  <div className="flex flex-col items-center text-muted-foreground animate-pulse">
                    <Search className="h-10 w-10 mb-4 opacity-50" />
                    <p>Scanning faces and calculating embeddings...</p>
                  </div>
                ) : resultImage ? (
                  <img 
                    src={resultImage} 
                    alt="Analyzed Classroom" 
                    className="max-w-full max-h-[600px] object-contain"
                  />
                ) : (
                  <div className="text-muted-foreground text-sm flex flex-col items-center">
                    <Video className="h-10 w-10 mb-4 opacity-20" />
                    Awaiting image input.
                  </div>
                )}
              </div>

              {/* Records Table */}
              {attendanceRecords.length > 0 && (
                <div className="border border-border rounded-lg overflow-hidden">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-muted text-muted-foreground uppercase text-xs">
                      <tr>
                        <th className="px-6 py-3 font-medium min-w-[120px]">Status</th>
                        <th className="px-6 py-3 font-medium">Student Name</th>
                        <th className="px-6 py-3 font-medium">Predicted Seat</th>
                        <th className="px-6 py-3 font-medium text-right">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {attendanceRecords.map((record, idx) => (
                        <tr key={idx} className="bg-background hover:bg-accent/50 transition-colors">
                          <td className="px-6 py-4 border-r border-border/30">
                            <span className={`inline-flex items-center justify-center min-w-[80px] gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase border ${record.badgeStyle || "bg-muted text-muted-foreground border-border"}`}>
                              <span className={`h-1.5 w-1.5 rounded-full ${record.dotStyle || "bg-muted-foreground"}`}></span>
                              {record.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 font-semibold text-foreground text-sm uppercase tracking-wide">
                            {record.name}
                          </td>
                          <td className="px-6 py-4 text-xs font-medium text-muted-foreground">
                            {record.position}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {record.distance !== null ? (
                              <div className="flex flex-col items-end">
                                <span className="text-[10px] text-muted-foreground uppercase tracking-widest mb-0.5">Similarity Score</span>
                                <span className="font-mono text-sm text-foreground bg-accent/30 px-2 py-0.5 rounded border border-border/50">
                                  {record.distance.toFixed(3)}
                                </span>
                              </div>
                            ) : (
                              <span className="text-muted-foreground text-xs italic">N/A</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
