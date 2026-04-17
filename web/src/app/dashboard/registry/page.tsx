"use client";

import React, { useEffect, useState } from "react";
import { Users, Search, RefreshCw, GraduationCap, X, ImageIcon, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function RegistryPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modal State
  const [selectedStudent, setSelectedStudent] = useState<any>(null);
  const [studentImages, setStudentImages] = useState<string[]>([]);
  const [loadingImages, setLoadingImages] = useState(false);

  const fetchRegistry = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/registry`);
      if (res.ok) {
        const data = await res.json();
        setStudents(data.students || []);
      } else {
        toast.error("Failed to load student registry.");
      }
    } catch (error) {
      console.error(error);
      toast.error("Cannot connect to backend server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegistry();
  }, []);

  const openStudentDetails = async (student: any) => {
    setSelectedStudent(student);
    setLoadingImages(true);
    setStudentImages([]);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/registry/${student.id}/images`);
      if (res.ok) {
        const data = await res.json();
        setStudentImages(data.images || []);
      } else {
        toast.error("Failed to load images for this student.");
      }
    } catch (error) {
      toast.error("Network error while loading images.");
    } finally {
      setLoadingImages(false);
    }
  };

  const deleteStudent = async (studentId: string, studentName: string) => {
    if (!confirm(`Are you sure you want to permanently delete ${studentName}? This will remove them from the database and recognition models.`)) {
      return;
    }
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/registry/${studentId}`, {
        method: "DELETE",
      });
      
      if (res.ok) {
        toast.success(`Successfully deleted ${studentName}`);
        fetchRegistry(); // Refresh the list
      } else {
        const data = await res.json();
        toast.error(data.detail || "Failed to delete student.");
      }
    } catch (error) {
      toast.error("Network error while deleting student.");
    }
  };

  const closeDetails = () => {
    setSelectedStudent(null);
    setStudentImages([]);
  };

  const filteredStudents = students.filter(s => 
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    s.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 space-y-8 max-w-6xl w-full mx-auto relative">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Users className="text-primary" />
            Student Registry
          </h2>
          <p className="text-muted-foreground">View and manage all students currently enrolled in the face recognition gallery.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchRegistry} disabled={loading} className="gap-2">
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh List
        </Button>
      </div>

      <Card className="border-border shadow-md">
        <CardHeader className="border-b border-border/50 pb-6">
          <div className="flex items-center justify-between gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input 
                placeholder="Search students by name or ID..." 
                className="pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="text-sm text-muted-foreground">
              Total Enrolled: <span className="font-bold text-foreground">{students.length}</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 text-muted-foreground uppercase text-[10px] tracking-wider font-bold">
                <tr>
                  <th className="px-6 py-4">Avatar</th>
                  <th className="px-6 py-4">Student Name</th>
                  <th className="px-6 py-4">Student ID (Internal)</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground italic">
                      <div className="flex flex-col items-center gap-2">
                        <RefreshCw className="animate-spin h-6 w-6 opacity-30" />
                        Loading registry data...
                      </div>
                    </td>
                  </tr>
                ) : filteredStudents.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">
                      {searchTerm ? "No students match your search term." : "No students enrolled yet. Head to the Enroll page to add your first student."}
                    </td>
                  </tr>
                ) : (
                  filteredStudents.map((student) => (
                    <tr key={student.id} className="hover:bg-accent/30 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 overflow-hidden text-primary group-hover:border-primary transition-all">
                          {student.avatar ? (
                            <img 
                              src={`data:image/jpeg;base64,${student.avatar}`} 
                              alt={`${student.name} avatar`}
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <GraduationCap size={20} />
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 font-semibold text-foreground">
                        {student.name}
                        <div className="text-[10px] text-muted-foreground font-normal mt-0.5">
                          {student.image_count ? `${student.image_count} ref images` : "No images stored"}
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-muted-foreground">{student.id}</td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                          Active Gallery
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-xs"
                            onClick={() => openStudentDetails(student)}
                            disabled={!student.image_count}
                          >
                            View Images
                          </Button>
                          <Button 
                            variant="destructive" 
                            size="icon" 
                            className="h-8 w-8"
                            onClick={() => deleteStudent(student.id, student.name)}
                            title="Delete Student"
                          >
                            <Trash2 size={14} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Full Screen Modal Overlay for Student Details */}
      {selectedStudent && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border-primary/20">
            <div className="p-6 border-b border-border flex items-center justify-between bg-muted/30">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-full overflow-hidden border-2 border-primary">
                  {selectedStudent.avatar ? (
                    <img src={`data:image/jpeg;base64,${selectedStudent.avatar}`} className="h-full w-full object-cover" alt="avatar" />
                  ) : <div className="h-full w-full bg-primary/20 flex items-center justify-center"><GraduationCap /></div>}
                </div>
                <div>
                  <h3 className="text-xl font-bold">{selectedStudent.name}</h3>
                  <p className="text-sm text-muted-foreground">ID: {selectedStudent.id}</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={closeDetails}>
                <X size={24} />
              </Button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1">
              {loadingImages ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground">
                  <RefreshCw className="animate-spin h-8 w-8 text-primary" />
                  <p>Fetching original high-res images from database...</p>
                </div>
              ) : studentImages.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground">
                  <ImageIcon className="h-12 w-12 opacity-20" />
                  <p>No images found in GridFS storage for this student.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                  {studentImages.map((b64, idx) => (
                    <div key={idx} className="group relative rounded-xl overflow-hidden border border-border shadow-sm hover:shadow-md transition-all">
                      <div className="aspect-[3/4] bg-muted/30">
                        <img 
                          src={`data:image/jpeg;base64,${b64}`} 
                          alt={`${selectedStudent.name} ref ${idx + 1}`}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                      </div>
                      <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-4 pb-3">
                        <p className="text-white text-xs font-medium">Reference #{idx + 1}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
