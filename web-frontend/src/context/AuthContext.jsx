import { createContext, useCallback, useContext, useState } from "react";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Demo login: accepts any wallet address / credentials — no backend required
  const login = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    try {
      // Simulate a brief loading delay for UX realism
      await new Promise((r) => setTimeout(r, 600));
      const address = credentials.wallet_address || credentials.email || "demo";
      const userData = {
        id: "demo-user",
        username: address.startsWith("0x")
          ? `User_${address.slice(2, 6)}`
          : address,
        email: credentials.email || "",
        wallet_address: address,
        address,
        token: `demo-token-${Date.now()}`,
        isAuthenticated: true,
      };
      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));
      return true;
    } catch (err) {
      setError(err.message || "An error occurred during login");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (userData) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 600));
      const newUser = {
        id: `user-${Date.now()}`,
        username: userData.username,
        email: userData.email,
        wallet_address: userData.wallet_address || userData.address || "",
        address: userData.wallet_address || userData.address || "",
        token: `demo-token-${Date.now()}`,
        isAuthenticated: true,
      };
      setUser(newUser);
      localStorage.setItem("user", JSON.stringify(newUser));
      return true;
    } catch (err) {
      setError(err.message || "An error occurred during registration");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setError(null);
    localStorage.removeItem("user");
  }, []);

  const checkAuthState = useCallback(() => {
    const saved = localStorage.getItem("user");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed?.isAuthenticated) {
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
