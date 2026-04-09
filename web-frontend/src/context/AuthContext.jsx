import { createContext, useCallback, useContext, useState } from "react";
import apiService from "../services/apiService";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.auth.login(credentials);
      if (response?.data) {
        const userData = {
          ...response.data.user,
          token: response.data.token,
          isAuthenticated: true,
        };
        setUser(userData);
        localStorage.setItem("user", JSON.stringify(userData));
        return true;
      }
      setError("Login failed. Please check your credentials.");
      return false;
    } catch (err) {
      const message = err.message || "An error occurred during login";
      setError(message);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (userData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.auth.register(userData);
      if (response?.data) {
        const newUser = {
          ...response.data.user,
          token: response.data.token,
          isAuthenticated: true,
        };
        setUser(newUser);
        localStorage.setItem("user", JSON.stringify(newUser));
        return true;
      }
      setError("Registration failed.");
      return false;
    } catch (err) {
      setError(err.message || "An error occurred during registration");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiService.auth.logout();
    } catch {
      // ignore logout API errors - still clear local state
    } finally {
      setUser(null);
      setError(null);
      localStorage.removeItem("user");
    }
  }, []);

  const checkAuthState = useCallback(() => {
    const savedUser = localStorage.getItem("user");
    if (savedUser) {
      try {
        const parsed = JSON.parse(savedUser);
        if (parsed && parsed.isAuthenticated) {
          setUser(parsed);
        } else {
          localStorage.removeItem("user");
        }
      } catch {
        localStorage.removeItem("user");
      }
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    checkAuthState,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;
