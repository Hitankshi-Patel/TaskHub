"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/navigation';
import Navbar from '../components/Navbar';
import api, { TaskData } from '../services/api';

export default function UserDashboard() {
  const { user, loading, getAuthHeaders } = useAuth();
  const router = useRouter();
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/');
    } else if (user && user.role === 'admin') {
      router.push('/admin');
    }
  }, [user, loading, router]);

  const fetchMyTasks = async () => {
    try {
      setFetching(true);
      setError(null);
      const headers = getAuthHeaders();
      const myTasks = await api.getMyTasks(headers);
      setTasks(myTasks);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tasks.');
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (user && user.role === 'user') {
      fetchMyTasks();
    }
  }, [user]);

  const handleStartTask = async (taskId: string) => {
    try {
      const headers = getAuthHeaders();
      await api.startTask(taskId, headers);
      // Refresh task list
      fetchMyTasks();
    } catch (err: any) {
      alert(`Error starting task: ${err.message}`);
    }
  };

  if (loading || !user) {
    return (
      <div className="flex-center" style={{ minHeight: '100vh', backgroundColor: 'var(--bg-app)' }}>
        <p style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Verifying credentials...</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-app)', paddingTop: 'calc(var(--header-height) + 20px)' }}>
      <Navbar />

      <main className="container" style={{ flex: 1, paddingBottom: '60px' }}>
        {/* Header Block */}
        <div className="flex-between" style={{ marginBottom: '32px', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Your Design Board</h1>
            <p style={{ color: 'var(--text-secondary)' }}>
              Manage your assigned product photography tasks and generate professional variations.
            </p>
          </div>
          <button onClick={fetchMyTasks} className="btn btn-secondary">
            🔄 Refresh Board
          </button>
        </div>

        {error && (
          <div style={{ backgroundColor: 'var(--danger-glow)', border: '1px solid var(--danger)', padding: '16px', borderRadius: 'var(--radius-sm)', color: 'var(--danger)', marginBottom: '24px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {fetching ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="skeleton-shimmer" style={{ height: '140px', borderRadius: 'var(--radius-md)' }}></div>
            <div className="skeleton-shimmer" style={{ height: '140px', borderRadius: 'var(--radius-md)' }}></div>
          </div>
        ) : tasks.length === 0 ? (
          <div className="card" style={{ padding: '60px 20px', textAlign: 'center', backgroundColor: 'var(--bg-card)' }}>
            <span style={{ fontSize: '48px', display: 'block', marginBottom: '16px' }}>☕</span>
            <h3>No tasks assigned yet</h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '8px auto 0' }}>
              Your administrator hasn't assigned any product photography tasks to your account yet. Check back later!
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {tasks.map((task) => (
              <div 
                key={task.id} 
                className="card" 
                style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'auto 1fr auto', 
                  gap: '24px', 
                  alignItems: 'center', 
                  backgroundColor: 'var(--bg-card)'
                }}
              >
                {/* Product Image Thumbnail */}
                <div style={{ width: '120px', height: '120px', borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-input)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img 
                    src={task.product_image_url} 
                    alt={task.title} 
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                </div>

                {/* Task Details */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <h3 style={{ fontSize: '20px', margin: 0 }}>{task.title}</h3>
                    <span className={`badge badge-${task.status.replace('_', '-')}`}>
                      {task.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
                    {task.description || 'No description provided.'}
                  </p>
                  
                  {/* Revision Feedback */}
                  {task.status === 'revision_requested' && task.feedback && (
                    <div style={{ 
                      marginTop: '8px',
                      backgroundColor: 'var(--danger-glow)', 
                      borderLeft: '4px solid var(--danger)', 
                      padding: '10px 14px', 
                      borderRadius: '4px',
                      fontSize: '13px'
                    }}>
                      <strong style={{ color: 'var(--danger)' }}>Revision Request:</strong> "{task.feedback}"
                    </div>
                  )}
                  {task.status === 'accepted' && task.feedback && (
                    <div style={{ 
                      marginTop: '8px',
                      backgroundColor: 'var(--success-glow)', 
                      borderLeft: '4px solid var(--success)', 
                      padding: '10px 14px', 
                      borderRadius: '4px',
                      fontSize: '13px'
                    }}>
                      <strong style={{ color: 'var(--success)' }}>Feedback:</strong> "{task.feedback}"
                    </div>
                  )}
                </div>

                {/* Task Actions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', minWidth: '180px' }}>
                  {task.status === 'assigned' || task.status === 'revision_requested' ? (
                    <button 
                      onClick={() => handleStartTask(task.id)} 
                      className="btn btn-primary"
                      style={{ width: '100%' }}
                    >
                      🚀 Start Studio Task
                    </button>
                  ) : (
                    <button 
                      onClick={() => router.push(`/tasks/${task.id}`)} 
                      className="btn btn-primary"
                      style={{ width: '100%', background: 'linear-gradient(135deg, var(--accent), #0f9f94)' }}
                    >
                      🎨 Open AI Studio
                    </button>
                  )}
                  <button 
                    onClick={() => router.push(`/tasks/${task.id}`)} 
                    className="btn btn-secondary"
                    style={{ width: '100%' }}
                  >
                    View Details
                  </button>
                </div>

              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
