"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/navigation';
import Navbar from '../components/Navbar';
import api, { TaskData, User, Analytics, GeneratedImage } from '../services/api';

export default function AdminDashboard() {
  const { user, loading, getAuthHeaders } = useAuth();
  const router = useRouter();

  // Data States
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  
  // Loading/UI States
  const [fetching, setFetching] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form States
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [assignedTo, setAssignedTo] = useState('');

  // Review Drawer States
  const [reviewTask, setReviewTask] = useState<TaskData | null>(null);
  const [reviewImages, setReviewImages] = useState<GeneratedImage[]>([]);
  const [feedback, setFeedback] = useState('');
  const [loadingReview, setLoadingReview] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/');
    } else if (user && user.role !== 'admin') {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  const loadAdminData = async () => {
    try {
      setFetching(true);
      setError(null);
      const headers = getAuthHeaders();
      
      const [tasksData, usersData, analyticsData] = await Promise.all([
        api.listAllTasks(headers),
        api.getUsers(headers),
        api.getAnalytics(headers)
      ]);

      setTasks(tasksData);
      setUsers(usersData);
      setAnalytics(analyticsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load administrative data.');
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (user && user.role === 'admin') {
      loadAdminData();
    }
  }, [user]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !imageUrl) return;

    try {
      setSubmitting(true);
      setError(null);
      const headers = getAuthHeaders();
      await api.createTask({
        title,
        description,
        product_image_url: imageUrl,
        assigned_to: assignedTo || undefined
      }, headers);

      // Reset form
      setTitle('');
      setDescription('');
      setImageUrl('');
      setAssignedTo('');
      
      // Reload lists
      await loadAdminData();
    } catch (err: any) {
      setError(err.message || 'Failed to create task.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task? All generated images will be permanently removed.')) return;
    try {
      const headers = getAuthHeaders();
      await api.deleteTask(taskId, headers);
      loadAdminData();
    } catch (err: any) {
      alert(`Error deleting task: ${err.message}`);
    }
  };

  const handleOpenReview = async (task: TaskData) => {
    setReviewTask(task);
    setFeedback('');
    setLoadingReview(true);
    try {
      const headers = getAuthHeaders();
      const gens = await api.getTaskGenerations(task.id, headers);
      setReviewImages(gens);
    } catch (err: any) {
      alert(`Error loading generations: ${err.message}`);
    } finally {
      setLoadingReview(false);
    }
  };

  const handleAcceptSubmission = async () => {
    if (!reviewTask) return;
    try {
      setSubmitting(true);
      const headers = getAuthHeaders();
      await api.acceptTask(reviewTask.id, feedback, headers);
      setReviewTask(null);
      loadAdminData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRejectSubmission = async () => {
    if (!reviewTask) return;
    if (!feedback) {
      alert('You must provide feedback to request revisions.');
      return;
    }
    try {
      setSubmitting(true);
      const headers = getAuthHeaders();
      await api.requestRevision(reviewTask.id, feedback, headers);
      setReviewTask(null);
      loadAdminData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !user) {
    return (
      <div className="flex-center" style={{ minHeight: '100vh', backgroundColor: 'var(--bg-app)' }}>
        <p style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Entering administration deck...</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-app)', paddingTop: 'calc(var(--header-height) + 20px)' }}>
      <Navbar />

      <main className="container" style={{ flex: 1, paddingBottom: '60px' }}>
        
        {/* Title Block */}
        <div className="flex-between" style={{ marginBottom: '32px', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Admin Ops Command</h1>
            <p style={{ color: 'var(--text-secondary)' }}>Manage product photography workflow, assign designers, and review generations.</p>
          </div>
          <button onClick={loadAdminData} className="btn btn-secondary flex-center" style={{ gap: '6px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
            Refresh Analytics
          </button>
        </div>

        {error && (
          <div style={{ backgroundColor: 'var(--danger-glow)', border: '1px solid var(--danger)', padding: '16px', borderRadius: 'var(--radius-sm)', color: 'var(--danger)', marginBottom: '24px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Analytics Section */}
        {analytics && (
          <div className="grid-responsive" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginBottom: '40px', gap: '20px' }}>
            <div className="card" style={{ padding: '20px', textAlign: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Designers</span>
              <p style={{ fontSize: '36px', fontWeight: 800, margin: '8px 0 0', color: 'var(--primary)' }}>{analytics.totals.users}</p>
            </div>
            <div className="card" style={{ padding: '20px', textAlign: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tasks Distributed</span>
              <p style={{ fontSize: '36px', fontWeight: 800, margin: '8px 0 0', color: 'var(--accent)' }}>{analytics.totals.tasks}</p>
            </div>
            <div className="card" style={{ padding: '20px', textAlign: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pending Reviews</span>
              <p style={{ fontSize: '36px', fontWeight: 800, margin: '8px 0 0', color: '#11b2ac' }}>{analytics.statuses.submitted}</p>
            </div>
            <div className="card" style={{ padding: '20px', textAlign: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Asset Generations</span>
              <p style={{ fontSize: '36px', fontWeight: 800, margin: '8px 0 0', color: 'var(--success)' }}>{analytics.totals.generations}</p>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '32px', alignItems: 'start' }}>
          
          {/* Tasks List */}
          <div>
            <h2 style={{ fontSize: '22px', marginBottom: '16px' }}>Task Inventory</h2>
            {fetching ? (
              <div className="skeleton-shimmer" style={{ height: '300px', borderRadius: 'var(--radius-md)' }}></div>
            ) : tasks.length === 0 ? (
              <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)' }}>No tasks in the system. Use the panel on the right to distribute a task.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {tasks.map((task) => (
                  <div key={task.id} className="card" style={{ display: 'flex', gap: '20px', alignItems: 'center', backgroundColor: 'var(--bg-card)', padding: '16px' }}>
                    <img 
                      src={task.product_image_url} 
                      alt={task.title} 
                      style={{ width: '80px', height: '80px', objectFit: 'cover', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}
                    />
                    <div style={{ flex: 1 }}>
                      <h4 style={{ margin: '0 0 4px', fontSize: '16px' }}>{task.title}</h4>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        Assignee: <strong>{task.assignee_name || 'Unassigned'}</strong>
                      </p>
                      <span className={`badge badge-${task.status.replace('_', '-')}`} style={{ fontSize: '10px' }}>
                        {task.status.replace('_', ' ')}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      {task.status === 'submitted' && (
                        <button 
                          onClick={() => handleOpenReview(task)} 
                          className="btn btn-primary flex-center"
                          style={{ padding: '6px 12px', fontSize: '12px', gap: '4px' }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                          Review Assets
                        </button>
                      )}
                      <button 
                        onClick={() => router.push(`/tasks/${task.id}`)}
                        className="btn btn-secondary" 
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                      >
                        Studio Details
                      </button>
                      <button 
                        onClick={() => handleDeleteTask(task.id)} 
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '12px', borderColor: 'var(--danger-glow)', color: 'var(--danger)' }}
                      >
                        Delete
                      </button>
                    </div>

                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Create Task Form */}
          <div className="card" style={{ position: 'sticky', top: '100px' }}>
            <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>Create Photography Task</h2>
            <form onSubmit={handleCreateTask}>
              <div className="form-group">
                <label className="form-label">Task Title / Product Name</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={title} 
                  onChange={(e) => setTitle(e.target.value)} 
                  placeholder="e.g. Diamond Sapphire Ring"
                  required 
                />
              </div>

              <div className="form-group">
                <label className="form-label">Product Description</label>
                <textarea 
                  className="form-input" 
                  value={description} 
                  onChange={(e) => setDescription(e.target.value)} 
                  placeholder="Describe the product details for the AI Studio prompts..." 
                  style={{ minHeight: '80px', resize: 'vertical' }}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Product Image URL</label>
                <input 
                  type="url" 
                  className="form-input" 
                  value={imageUrl} 
                  onChange={(e) => setImageUrl(e.target.value)} 
                  placeholder="https://example.com/product.jpg"
                  required 
                />
              </div>

              <div className="form-group">
                <label className="form-label">Assign To Designer</label>
                <select 
                  className="form-input" 
                  value={assignedTo} 
                  onChange={(e) => setAssignedTo(e.target.value)}
                >
                  <option value="">-- Keep Unassigned --</option>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                  ))}
                </select>
              </div>

              <button 
                type="submit" 
                className="btn btn-primary" 
                style={{ width: '100%', marginTop: '12px' }}
                disabled={submitting}
              >
                {submitting ? 'Creating...' : 'Distribute Task'}
              </button>
            </form>
          </div>

        </div>

      </main>

      {/* Review Drawer Modal */}
      {reviewTask && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(4px)',
          zIndex: 2000,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '24px'
        }}>
          <div className="card" style={{
            width: '100%',
            maxWidth: '900px',
            maxHeight: '90vh',
            overflowY: 'auto',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)'
          }}>
            <div className="flex-between" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '16px', marginBottom: '20px' }}>
              <div>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 800 }}>Reviewing Submission</span>
                <h3 style={{ fontSize: '22px' }}>{reviewTask.title}</h3>
              </div>
              <button onClick={() => setReviewTask(null)} style={{ fontSize: '24px', color: 'var(--text-muted)' }}>&times;</button>
            </div>

            {loadingReview ? (
              <div className="flex-center" style={{ height: '300px' }}>
                <p>Loading generated photos...</p>
              </div>
            ) : (
              <div>
                {/* 8 Images Gallery */}
                <h4 style={{ marginBottom: '12px' }}>Generated Variations (8/8)</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                  {reviewImages.map((img) => (
                    <div key={img.id} style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', overflow: 'hidden', backgroundColor: 'var(--bg-input)' }}>
                      <img 
                        src={img.image_url} 
                        alt={img.image_type} 
                        style={{ width: '100%', height: '180px', objectFit: 'cover' }}
                      />
                      <div style={{ padding: '8px', fontSize: '11px', textAlign: 'center', fontWeight: 700, textTransform: 'uppercase', backgroundColor: 'var(--bg-card)' }}>
                        {img.image_type.replace('_', ' ')}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Review Form */}
                <div className="form-group" style={{ marginBottom: '24px' }}>
                  <label className="form-label">Review Feedback</label>
                  <textarea 
                    className="form-input" 
                    value={feedback} 
                    onChange={(e) => setFeedback(e.target.value)} 
                    placeholder="Enter approval details or describe required revisions..." 
                    style={{ minHeight: '100px' }}
                  />
                </div>

                <div className="flex-between" style={{ gap: '16px' }}>
                  <button 
                    onClick={handleRejectSubmission} 
                    className="btn btn-secondary flex-center"
                    style={{ flex: 1, borderColor: 'var(--danger)', color: 'var(--danger)', padding: '12px', gap: '6px', justifyContent: 'center' }}
                    disabled={submitting}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    Request Revision
                  </button>
                  <button 
                    onClick={handleAcceptSubmission} 
                    className="btn btn-primary flex-center"
                    style={{ flex: 1, background: 'linear-gradient(135deg, var(--success), #059669)', padding: '12px', gap: '6px', justifyContent: 'center' }}
                    disabled={submitting}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    Approve & Complete Task
                  </button>
                </div>

              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
