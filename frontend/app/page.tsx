"use client";

import React, { useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { useRouter } from 'next/navigation';

const CheckIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#3b82f6' }}>
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
    <polyline points="22 4 12 14.01 9 11.01"></polyline>
  </svg>
);

const GoogleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
  </svg>
);

const GitHubIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
  </svg>
);

export default function Home() {
  const { user, loading, loginWithGoogle, loginWithGitHub, authError, clearError } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      if (user.role === 'admin') {
        router.push('/admin');
      } else {
        router.push('/dashboard');
      }
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex-center" style={{ minHeight: '100vh', flexDirection: 'column', gap: '16px', backgroundColor: '#ffffff' }}>
        <div className="spin-slow" style={{ color: '#3b82f6' }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path></svg>
        </div>
        <p style={{ fontWeight: 500, color: '#64748b' }}>Loading session...</p>
      </div>
    );
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      backgroundColor: '#f8fafc', 
      fontFamily: 'var(--font-body)',
      padding: '24px'
    }}>
      <div style={{ 
        backgroundColor: '#ffffff', 
        border: '1px solid #e2e8f0', 
        borderRadius: '16px', 
        padding: '40px', 
        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)',
        maxWidth: '400px',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
          <CheckIcon />
          <span style={{ fontSize: '24px', fontWeight: 700, color: '#0f172a', letterSpacing: '-0.5px' }}>
            Task<span style={{ color: '#3b82f6' }}>Hub</span>
          </span>
        </div>

        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>Sign In</h1>
        <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '28px', textAlign: 'center' }}>
          Sign in to your account to manage your workspace.
        </p>

        {authError && (
          <div style={{ 
            backgroundColor: '#fef2f2', 
            border: '1px solid #fca5a5', 
            borderRadius: '8px', 
            padding: '12px', 
            marginBottom: '20px', 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'flex-start', 
            gap: '8px',
            width: '100%'
          }}>
            <p style={{ fontSize: '13px', color: '#dc2626', margin: 0, lineHeight: 1.5 }}>{authError}</p>
            <button onClick={clearError} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontWeight: 700, fontSize: '16px', padding: 0 }}>×</button>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: '100%' }}>
          <button 
            onClick={loginWithGoogle}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
              width: '100%', padding: '12px', backgroundColor: '#ffffff',
              border: '1px solid #cbd5e1', borderRadius: '8px',
              fontSize: '15px', fontWeight: 600, color: '#334155',
              cursor: 'pointer', transition: 'background-color 0.2s'
            }}
            onMouseOver={e => e.currentTarget.style.backgroundColor = '#f8fafc'}
            onMouseOut={e => e.currentTarget.style.backgroundColor = '#ffffff'}
          >
            <GoogleIcon /> Continue with Google
          </button>
          
          <button 
            onClick={loginWithGitHub}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
              width: '100%', padding: '12px', backgroundColor: '#0f172a',
              border: '1px solid #0f172a', borderRadius: '8px',
              fontSize: '15px', fontWeight: 600, color: '#ffffff',
              cursor: 'pointer', transition: 'background-color 0.2s'
            }}
            onMouseOver={e => e.currentTarget.style.backgroundColor = '#1e293b'}
            onMouseOut={e => e.currentTarget.style.backgroundColor = '#0f172a'}
          >
            <GitHubIcon /> Continue with GitHub
          </button>
        </div>
      </div>
    </div>
  );
}
