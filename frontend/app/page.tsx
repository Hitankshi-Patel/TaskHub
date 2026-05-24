"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from './context/AuthContext';
import { useRouter } from 'next/navigation';

// --- Simple Icons ---
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

const ShieldIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#9ca3af' }}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
  </svg>
);

const AIFeatureIcon = () => (
  <div style={{ backgroundColor: '#eff6ff', padding: '10px', borderRadius: '50%', color: '#3b82f6' }}>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
  </div>
);

const RoleFeatureIcon = () => (
  <div style={{ backgroundColor: '#f3e8ff', padding: '10px', borderRadius: '50%', color: '#a855f7' }}>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
  </div>
);

const SecureFeatureIcon = () => (
  <div style={{ backgroundColor: '#dcfce7', padding: '10px', borderRadius: '50%', color: '#22c55e' }}>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
  </div>
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
        <p style={{ fontWeight: 500, color: '#64748b' }}>Loading secure session...</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', backgroundColor: '#ffffff', fontFamily: 'var(--font-body)' }}>
      {/* LEFT COLUMN: AUTH */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '40px', maxWidth: '600px', backgroundColor: '#ffffff', zIndex: 10 }}>
        
        {/* Header/Logo */}
        <div style={{ marginBottom: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <CheckIcon />
            <span style={{ fontSize: '24px', fontWeight: 700, color: '#0f172a', letterSpacing: '-0.5px' }}>
              Task<span style={{ color: '#3b82f6' }}>Hub</span>
            </span>
          </div>
          <p style={{ color: '#64748b', fontSize: '15px', fontWeight: 500 }}>AI Product Photography Studio</p>
        </div>

        {/* Login Form Container */}
        <div style={{ 
          backgroundColor: '#ffffff', 
          border: '1px solid #f1f5f9', 
          borderRadius: '24px', 
          padding: '48px', 
          boxShadow: '0 10px 40px -10px rgba(0,0,0,0.05)',
          maxWidth: '460px',
          margin: '0 auto',
          width: '100%'
        }}>
          <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#0f172a', marginBottom: '12px', letterSpacing: '-0.02em' }}>Welcome back</h1>
          <p style={{ color: '#64748b', fontSize: '16px', marginBottom: '32px' }}>
            Sign in to continue to your <strong>TaskHub</strong> workspace.
          </p>

          {authError && (
            <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '8px', padding: '12px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
              <p style={{ fontSize: '14px', color: '#dc2626', margin: 0, lineHeight: 1.5 }}>{authError}</p>
              <button onClick={clearError} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontWeight: 700, fontSize: '16px' }}>×</button>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <button 
              onClick={loginWithGoogle}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
                width: '100%', padding: '14px', backgroundColor: '#ffffff',
                border: '1px solid #cbd5e1', borderRadius: '12px',
                fontSize: '16px', fontWeight: 600, color: '#334155',
                cursor: 'pointer', transition: 'all 0.2s'
              }}
              onMouseOver={e => e.currentTarget.style.backgroundColor = '#f8fafc'}
              onMouseOut={e => e.currentTarget.style.backgroundColor = '#ffffff'}
            >
              <GoogleIcon /> Continue with Google
            </button>
            
            <button 
              onClick={loginWithGitHub}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
                width: '100%', padding: '14px', backgroundColor: '#0f172a',
                border: '1px solid #0f172a', borderRadius: '12px',
                fontSize: '16px', fontWeight: 600, color: '#ffffff',
                cursor: 'pointer', transition: 'all 0.2s'
              }}
              onMouseOver={e => e.currentTarget.style.backgroundColor = '#1e293b'}
              onMouseOut={e => e.currentTarget.style.backgroundColor = '#0f172a'}
            >
              <GitHubIcon /> Continue with GitHub
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', margin: '32px 0', gap: '16px' }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#e2e8f0' }}></div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '14px' }}>
              <ShieldIcon /> Secure OAuth login
            </div>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#e2e8f0' }}></div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', color: '#64748b', fontSize: '13px', fontWeight: 500 }}>
            <span>Protected</span>
            <span>•</span>
            <span>Role Based Access</span>
            <span>•</span>
            <span>Session Secure</span>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '13px', fontWeight: 500 }}>
          <span>© 2024 TaskHub. All rights reserved.</span>
          <div style={{ display: 'flex', gap: '24px' }}>
            <span style={{ cursor: 'pointer' }}>Privacy Policy</span>
            <span style={{ cursor: 'pointer' }}>Terms of Service</span>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: HERO / FEATURES */}
      <div style={{ 
        flex: 1, 
        backgroundColor: '#f8fafc', 
        position: 'relative', 
        display: 'none', 
        '@media (min-width: 1024px)': { display: 'block' } 
      }} className="right-col-desktop">
        
        {/* Subtle Dotted Grid Background */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
          backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)',
          backgroundSize: '24px 24px',
          opacity: 0.5,
          zIndex: 1
        }}></div>

        {/* Theme Toggle Button */}
        <div style={{ position: 'absolute', top: '40px', right: '40px', zIndex: 10, display: 'flex', alignItems: 'center', backgroundColor: '#ffffff', borderRadius: '20px', padding: '4px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', border: '1px solid #f1f5f9' }}>
          <div style={{ padding: '6px', borderRadius: '50%', backgroundColor: '#f1f5f9', color: '#64748b', display: 'flex', cursor: 'pointer' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
          </div>
          <div style={{ padding: '6px', borderRadius: '50%', color: '#94a3b8', display: 'flex', cursor: 'pointer' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
          </div>
        </div>

        {/* Floating Images Collage */}
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '100%', height: '100%', zIndex: 5, pointerEvents: 'none' }}>
          
          <div style={{ position: 'absolute', top: '20%', left: '20%', transform: 'rotate(-5deg)', width: '280px', height: '280px', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.1)', border: '8px solid #ffffff' }}>
            <img src="https://images.unsplash.com/photo-1605100804763-247f52bcf5e9?auto=format&fit=crop&w=600&q=80" alt="Ring Velvet" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          
          <div style={{ position: 'absolute', top: '35%', right: '15%', transform: 'rotate(8deg)', width: '280px', height: '280px', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.1)', border: '8px solid #ffffff' }}>
            <img src="https://images.unsplash.com/photo-1599643478514-4a552ee16d41?auto=format&fit=crop&w=600&q=80" alt="Ring Marble" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          
          <div style={{ position: 'absolute', bottom: '20%', left: '30%', transform: 'rotate(-2deg)', width: '320px', height: '220px', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.1)', border: '8px solid #ffffff' }}>
            <img src="https://images.unsplash.com/photo-1611591437281-460bfbe1220a?auto=format&fit=crop&w=600&q=80" alt="Ring Model" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>

          <div style={{ position: 'absolute', top: '45%', left: '10%', transform: 'rotate(-10deg)', width: '240px', height: '240px', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.1)', border: '8px solid #ffffff', backgroundColor: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <img src="https://images.unsplash.com/photo-1605100804763-247f52bcf5e9?auto=format&fit=crop&w=600&q=80" alt="Ring White" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>

        </div>

        {/* Bottom Features Card */}
        <div style={{ position: 'absolute', bottom: '40px', left: '50%', transform: 'translateX(-50%)', width: '85%', maxWidth: '700px', backgroundColor: '#ffffff', borderRadius: '16px', padding: '24px 32px', display: 'flex', justifyContent: 'space-between', zIndex: 10, boxShadow: '0 10px 30px rgba(0,0,0,0.05)', border: '1px solid #f1f5f9' }}>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <AIFeatureIcon />
            <div>
              <h4 style={{ margin: '0 0 4px 0', fontSize: '15px', color: '#0f172a', fontWeight: 600 }}>AI Powered</h4>
              <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>Generate stunning<br/>product photos</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <RoleFeatureIcon />
            <div>
              <h4 style={{ margin: '0 0 4px 0', fontSize: '15px', color: '#0f172a', fontWeight: 600 }}>Role Based</h4>
              <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>Admin & User<br/>access control</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <SecureFeatureIcon />
            <div>
              <h4 style={{ margin: '0 0 4px 0', fontSize: '15px', color: '#0f172a', fontWeight: 600 }}>Secure</h4>
              <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>OAuth 2.0<br/>Authentication</p>
            </div>
          </div>

        </div>

      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        @media (max-width: 1023px) {
          .right-col-desktop { display: none !important; }
        }
        @media (min-width: 1024px) {
          .right-col-desktop { display: block !important; }
        }
      `}} />
    </div>
  );
}
