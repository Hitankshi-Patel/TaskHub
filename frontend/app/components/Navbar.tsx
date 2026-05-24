"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Link from 'next/link';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  // Load and apply theme
  useEffect(() => {
    const savedTheme = localStorage.getItem('taskhub_theme') as 'light' | 'dark' | null;
    const initialTheme = savedTheme || 'dark';
    setTheme(initialTheme);
    document.documentElement.setAttribute('data-theme', initialTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('taskhub_theme', newTheme);
  };

  if (!user) return null;

  return (
    <nav className="navbar">
      <div className="container navbar-container">
        {/* Logo */}
        <Link href="/" className="logo">
          <div className="logo-icon">T</div>
          <span>TaskHub</span>
        </Link>

        {/* Navigation & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Dashboard Navigation */}
          {user.role === 'admin' ? (
            <Link href="/admin" style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-secondary)' }} className="nav-link">
              Admin Dashboard
            </Link>
          ) : (
            <Link href="/dashboard" style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-secondary)' }} className="nav-link">
              My Task Board
            </Link>
          )}

          {/* User Profile */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {user.full_name || user.email.split('@')[0]}
            </span>
            <span style={{ 
              fontSize: '10px', 
              fontWeight: 800, 
              color: user.role === 'admin' ? 'var(--danger)' : 'var(--accent)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              {user.role}
            </span>
          </div>

          {/* Theme Toggle Button */}
          <button 
            onClick={toggleTheme} 
            className="btn-icon" 
            title="Toggle Light/Dark Theme"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px', cursor: 'pointer' }}
          >
            {theme === 'light' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
            )}
          </button>

          {/* Logout Button */}
          <button 
            onClick={logout} 
            className="btn btn-secondary"
            style={{ padding: '8px 16px' }}
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};
export default Navbar;
