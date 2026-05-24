"use client";

import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter, useParams } from 'next/navigation';
import Navbar from '../../components/Navbar';
import api, { TaskData, GeneratedImage } from '../../services/api';

interface JobStatus {
  jobId: string;
  progress: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error: string | null;
}

interface ImageSlot {
  type: string;
  name: string;
  category: 'background' | 'theme' | 'creative' | 'model';
  angle?: string;
  description: string;
}

const REQUIRED_SLOTS: ImageSlot[] = [
  { type: 'white_background', name: 'White Background', category: 'background', description: 'Pure white background (#FFFFFF) for e-commerce catalog.' },
  { type: 'theme_1', name: 'Luxury Marble', category: 'theme', description: 'Product positioned elegantly on a polished white marble surface.' },
  { type: 'theme_2', name: 'Black Velvet', category: 'theme', description: 'Product resting on a premium dark velvet cloth drape.' },
  { type: 'creative_1', name: 'Beach Sunset', category: 'creative', description: 'Lifestyle product shot on a flat sea-rock during golden hour.' },
  { type: 'creative_2', name: 'Neon Pedestal', category: 'creative', description: 'Cyberpunk neon cyan/magenta styling on a sleek pedestal.' },
  { type: 'model_front', name: 'Model Front', category: 'model', angle: 'front', description: 'A realistic model wearing the jewelry item, front angle.' },
  { type: 'model_side', name: 'Model Side', category: 'model', angle: 'side', description: 'Model wearing the jewelry item, 45-degree profile view.' },
  { type: 'model_close', name: 'Model Close-up', category: 'model', angle: 'close', description: 'Model wearing the jewelry, close-up macro focal length.' }
];

export default function AIStudio() {
  const { user, loading, getAuthHeaders } = useAuth();
  const router = useRouter();
  const params = useParams();
  const taskId = params.id as string;

  // Data States
  const [task, setTask] = useState<TaskData | null>(null);
  const [generations, setGenerations] = useState<GeneratedImage[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Job Polling States
  const [activeJobs, setActiveJobs] = useState<{ [imageType: string]: JobStatus }>({});
  
  // Modal / Toast States
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'info' | 'error' } | null>(null);

  // Polling intervals ref to clean up on unmount
  const pollIntervals = useRef<{ [key: string]: NodeJS.Timeout }>({});

  const showToast = (text: string, type: 'success' | 'info' | 'error' = 'info') => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const fetchTaskAndGens = async () => {
    try {
      setFetching(true);
      setError(null);
      const headers = getAuthHeaders();
      const [taskDetails, gens] = await Promise.all([
        api.getTaskDetails(taskId, headers),
        api.getTaskGenerations(taskId, headers)
      ]);
      setTask(taskDetails);
      setGenerations(gens);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch task information.');
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (!loading && !user) {
      router.push('/');
    } else if (user) {
      fetchTaskAndGens();
    }
    
    return () => {
      // Clean up all running intervals on unmount
      Object.values(pollIntervals.current).forEach(clearInterval);
    };
  }, [user, loading, taskId]);

  const pollJobStatus = (jobId: string, imageType: string) => {
    if (pollIntervals.current[imageType]) {
      clearInterval(pollIntervals.current[imageType]);
    }

    const interval = setInterval(async () => {
      try {
        const headers = getAuthHeaders();
        const status = await api.getJobStatus(jobId, headers);
        
        setActiveJobs(prev => ({
          ...prev,
          [imageType]: {
            jobId,
            progress: status.progress,
            status: status.status,
            error: status.error || null
          }
        }));

        if (status.status === 'completed') {
          clearInterval(interval);
          delete pollIntervals.current[imageType];
          showToast(`Successfully generated ${imageType.replace('_', ' ')}!`, 'success');
          // Reload generations list
          const gens = await api.getTaskGenerations(taskId, headers);
          setGenerations(gens);
          
          // Clear active job after 2 seconds
          setTimeout(() => {
            setActiveJobs(prev => {
              const copy = { ...prev };
              delete copy[imageType];
              return copy;
            });
          }, 2000);
        } else if (status.status === 'failed') {
          clearInterval(interval);
          delete pollIntervals.current[imageType];
          showToast(`Generation failed for ${imageType.replace('_', ' ')}: ${status.error}`, 'error');
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        // Stop polling if job no longer exists (backend restarted and wiped in-memory jobs)
        if (msg.toLowerCase().includes('not found') || msg.includes('404')) {
          clearInterval(interval);
          delete pollIntervals.current[imageType];
          setActiveJobs(prev => {
            const copy = { ...prev };
            delete copy[imageType];
            return copy;
          });
          showToast(`Generation job expired (backend may have restarted). Please regenerate.`, 'error');
        }
        // Other transient errors: log silently and keep polling
      }
    }, 2000);

    pollIntervals.current[imageType] = interval;
  };

  const handleGenerate = async (imageType: string, angle?: string) => {
    if (!task) return;
    try {
      showToast(`Starting generation for ${imageType.replace('_', ' ')}...`, 'info');
      
      const headers = getAuthHeaders();
      const response = await api.generateImage(taskId, {
        image_type: imageType,
        angle
      }, headers);

      setActiveJobs(prev => ({
        ...prev,
        [imageType]: {
          jobId: response.job_id,
          progress: 10,
          status: 'pending',
          error: null
        }
      }));

      pollJobStatus(response.job_id, imageType);
    } catch (err: any) {
      showToast(err.message || 'Generation request failed.', 'error');
    }
  };

  const handleDeleteImg = async (imageType: string, genId: string) => {
    if (!confirm('Are you sure you want to delete this generated image?')) return;
    try {
      const headers = getAuthHeaders();
      await api.deleteGeneration(genId, headers);
      showToast('Image deleted successfully.', 'success');
      const gens = await api.getTaskGenerations(taskId, headers);
      setGenerations(gens);
    } catch (err: any) {
      showToast(`Delete failed: ${err.message}`, 'error');
    }
  };

  const handleSubmitTask = async () => {
    try {
      const headers = getAuthHeaders();
      await api.submitTask(taskId, headers);
      showToast('Task submitted successfully to the administrator!', 'success');
      fetchTaskAndGens();
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    }
  };

  // Helper: Find generation for a slot type
  const getSlotImage = (type: string) => {
    return generations.find(g => g.image_type === type);
  };

  const generatedCount = REQUIRED_SLOTS.reduce((count, slot) => {
    return getSlotImage(slot.type) ? count + 1 : count;
  }, 0);

  if (loading || !user || !task) {
    return (
      <div className="flex-center" style={{ minHeight: '100vh', backgroundColor: 'var(--bg-app)' }}>
        <p style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Loading AI photography studio...</p>
      </div>
    );
  }

  const isWorkingState = task.status === 'in_progress';
  const isSubmissionReady = generatedCount === 8 && (task.status === 'in_progress' || task.status === 'revision_requested');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-app)', paddingTop: 'calc(var(--header-height) + 20px)' }}>
      <Navbar />

      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          backgroundColor: toastMessage.type === 'success' ? 'var(--success)' : toastMessage.type === 'error' ? 'var(--danger)' : 'var(--primary)',
          color: 'white',
          padding: '12px 24px',
          borderRadius: 'var(--radius-sm)',
          boxShadow: 'var(--shadow-xl)',
          zIndex: 3000,
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          animation: 'shimmer 2s infinite'
        }}>
          <span>{toastMessage.type === 'success' ? '✓' : toastMessage.type === 'error' ? '❌' : 'ℹ️'}</span>
          {toastMessage.text}
        </div>
      )}

      <main className="container" style={{ flex: 1, paddingBottom: '80px' }}>
        
        {/* Navigation Breadcrumb */}
        <div style={{ marginBottom: '20px' }}>
          <button 
            onClick={() => router.push(user.role === 'admin' ? '/admin' : '/dashboard')} 
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '13px' }}
          >
            ← Back to Dashboards
          </button>
        </div>

        {/* Task Overview Block */}
        <div className="card" style={{ display: 'grid', gridTemplateColumns: '1fr 240px', gap: '32px', marginBottom: '32px', backgroundColor: 'var(--bg-card)' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <h1 style={{ fontSize: '28px', margin: 0 }}>{task.title}</h1>
              <span className={`badge badge-${task.status.replace('_', '-')}`}>{task.status.replace('_', ' ')}</span>
            </div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '15px' }}>
              {task.description || 'No description provided.'}
            </p>
            
            {/* Task Status Instructions */}
            {task.status === 'assigned' && (
              <div style={{ backgroundColor: 'var(--info-glow)', padding: '12px', borderRadius: '4px', borderLeft: '4px solid var(--info)', fontSize: '14px' }}>
                <strong>Assigned to you:</strong> Click "Start Studio Task" in your Dashboard to unlock the AI Studio controls.
              </div>
            )}
            {task.status === 'revision_requested' && task.feedback && (
              <div style={{ backgroundColor: 'var(--danger-glow)', padding: '12px', borderRadius: '4px', borderLeft: '4px solid var(--danger)', fontSize: '14px' }}>
                <strong style={{ color: 'var(--danger)' }}>Revision Requested:</strong> "{task.feedback}"
              </div>
            )}
            {task.status === 'accepted' && task.feedback && (
              <div style={{ backgroundColor: 'var(--success-glow)', padding: '12px', borderRadius: '4px', borderLeft: '4px solid var(--success)', fontSize: '14px' }}>
                <strong style={{ color: 'var(--success)' }}>Admin Feedback:</strong> "{task.feedback}"
              </div>
            )}

            {/* Tracker Bar */}
            <div style={{ marginTop: '24px' }}>
              <div className="flex-between" style={{ marginBottom: '8px', fontSize: '14px', fontWeight: 700 }}>
                <span>Studio Completion Progress</span>
                <span>{generatedCount} / 8 Images Generated</span>
              </div>
              <div style={{ height: '8px', backgroundColor: 'var(--bg-input)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${(generatedCount / 8) * 100}%`, background: 'linear-gradient(90deg, var(--primary), var(--accent))', transition: 'width 0.4s ease' }}></div>
              </div>
            </div>
          </div>

          {/* Original Product Image Preview */}
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, color: 'var(--text-muted)', display: 'block', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Original Product</span>
            <div style={{ height: '150px', borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-input)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <img 
                src={task.product_image_url} 
                alt="Product to Replicate" 
                style={{ width: '100%', height: '100%', objectFit: 'cover', cursor: 'pointer' }}
                onClick={() => setPreviewImageUrl(task.product_image_url)}
              />
            </div>
          </div>
        </div>

        {/* Submit Bar */}
        {isSubmissionReady && (
          <div className="card glow-animation" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--success-glow)', borderColor: 'var(--success)', padding: '20px', marginBottom: '32px' }}>
            <div>
              <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Generations Complete!</h3>
              <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: '14px' }}>All 8 required assets are present and satisfy exact product appearance consistency.</p>
            </div>
            <button onClick={handleSubmitTask} className="btn btn-primary" style={{ background: 'linear-gradient(135deg, var(--success), #059669)', fontSize: '15px', padding: '12px 28px' }}>
              Submit Final Assets to Admin
            </button>
          </div>
        )}

        {/* 8 Studio Slots Grid */}
        <h2 style={{ fontSize: '22px', marginBottom: '20px' }}>Photography Studio Slots</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '24px' }}>
          
          {REQUIRED_SLOTS.map((slot) => {
            const img = getSlotImage(slot.type);
            const activeJob = activeJobs[slot.type];
            
            return (
              <div 
                key={slot.type} 
                className="card" 
                style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  backgroundColor: 'var(--bg-card)', 
                  padding: '16px',
                  justifyContent: 'space-between',
                  minHeight: '340px'
                }}
              >
                {/* Visual Area */}
                <div style={{ 
                  height: '200px', 
                  borderRadius: 'var(--radius-sm)', 
                  overflow: 'hidden', 
                  border: '1px solid var(--border-color)', 
                  backgroundColor: 'var(--bg-input)',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {activeJob ? (
                    /* Generating state loader */
                    <div style={{ width: '100%', height: '100%', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '12px' }}>
                      <div className="spin-slow" style={{ fontSize: '32px' }}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path></svg>
                      </div>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary)' }}>
                        {activeJob.status === 'pending' ? 'Queuing Replicate Job...' : `Generating: ${activeJob.progress}%`}
                      </span>
                      <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${activeJob.progress}%`, height: '100%', backgroundColor: 'var(--primary)', transition: 'width 0.25s' }}></div>
                      </div>
                    </div>
                  ) : img ? (
                    /* Completed Image preview */
                    <div style={{ width: '100%', height: '100%' }}>
                      <img 
                        src={img.image_url} 
                        alt={slot.name} 
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                      {/* Zoom click */}
                      <button 
                        onClick={() => setPreviewImageUrl(img.image_url)}
                        style={{ position: 'absolute', top: '8px', right: '8px', width: '32px', height: '32px', borderRadius: '16px', backgroundColor: 'rgba(0,0,0,0.6)', color: 'white', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
                      </button>
                    </div>
                  ) : (
                    /* Empty slot placeholder */
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px' }}>
                      <span style={{ display: 'block', marginBottom: '8px' }}>
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: 600 }}>Empty Studio Slot</span>
                    </div>
                  )}
                </div>

                {/* Metadata & Actions */}
                <div style={{ marginTop: '12px' }}>
                  <div className="flex-between" style={{ marginBottom: '4px' }}>
                    <h4 style={{ fontSize: '15px' }}>{slot.name}</h4>
                    {img && <span style={{ fontSize: '10px', color: 'var(--success)', fontWeight: 800 }}>✓ READY</span>}
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', minHeight: '34px', margin: '0 0 12px' }}>
                    {slot.description}
                  </p>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    {img ? (
                      /* Actions for generated image */
                      <>
                        <button 
                          onClick={() => handleGenerate(slot.type, slot.angle)}
                          className="btn btn-secondary"
                          style={{ flex: 1, padding: '6px 0', fontSize: '12px' }}
                          disabled={!isWorkingState || !!activeJob}
                        >
                          Regenerate
                        </button>
                        <a 
                          href={img.image_url} 
                          download={`${task.title.replace(/\s+/g, '_')}_${slot.type}.png`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary flex-center"
                          style={{ width: '40px', padding: 0 }}
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        </a>
                        <button 
                          onClick={() => handleDeleteImg(slot.type, img.id)}
                          className="btn btn-secondary"
                          style={{ width: '40px', padding: 0, borderColor: 'var(--danger-glow)', color: 'var(--danger)' }}
                          disabled={!isWorkingState}
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                        </button>
                      </>
                    ) : (
                      /* Action to trigger generation */
                      <button 
                        onClick={() => handleGenerate(slot.type, slot.angle)}
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '8px' }}
                        disabled={!isWorkingState || !!activeJob}
                      >
                        Generate Photo
                      </button>
                    )}
                  </div>
                </div>

              </div>
            );
          })}
        </div>

      </main>

      {/* Lightbox Preview Modal */}
      {previewImageUrl && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          backdropFilter: 'blur(8px)',
          zIndex: 4000,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '20px'
        }} onClick={() => setPreviewImageUrl(null)}>
          <div style={{ position: 'relative', maxWidth: '90%', maxHeight: '90%' }} onClick={e => e.stopPropagation()}>
            <img 
              src={previewImageUrl} 
              alt="Studio Preview Zoom" 
              style={{ maxWidth: '100vw', maxHeight: '85vh', objectFit: 'contain', borderRadius: 'var(--radius-sm)', border: '2px solid rgba(255,255,255,0.1)' }}
            />
            <button 
              onClick={() => setPreviewImageUrl(null)}
              style={{
                position: 'absolute',
                top: '-40px',
                right: '0px',
                background: 'none',
                border: 'none',
                color: 'white',
                fontSize: '32px',
                cursor: 'pointer'
              }}
            >
              &times;
            </button>
            <div style={{ textAlign: 'center', marginTop: '12px' }}>
              <a 
                href={previewImageUrl} 
                download="taskhub_image.png" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="btn btn-primary"
              >
                ⬇️ Download High-Res Asset
              </a>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
