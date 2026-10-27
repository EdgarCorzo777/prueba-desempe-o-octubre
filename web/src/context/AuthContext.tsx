import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
  isViewer: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('sismowatch_token'));
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadUser() {
      const storedToken = localStorage.getItem('sismowatch_token');
      if (storedToken) {
        try {
          const profile = await api.getMe();
          setUser(profile);
          setToken(storedToken);
        } catch (err) {
          console.error('Failed to load user profile from token:', err);
          logout();
        }
      }
      setLoading(false);
    }
    loadUser();
  }, []);

  const login = async (email: string, pass: string) => {
    const res = await api.login(email, pass);
    localStorage.setItem('sismowatch_token', res.access_token);
    localStorage.setItem('sismowatch_user', JSON.stringify(res.user));
    setToken(res.access_token);
    setUser(res.user);
  };

  const logout = () => {
    localStorage.removeItem('sismowatch_token');
    localStorage.removeItem('sismowatch_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        isAdmin: user?.role === 'admin',
        isViewer: user?.role === 'viewer' || user?.role === 'admin'
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
