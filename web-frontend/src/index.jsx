import CssBaseline from "@mui/material/CssBaseline";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/index.css";
import { AuthProvider } from "./context/AuthContext";
import { PortfolioProvider } from "./context/PortfolioContext";
import { RiskAnalysisProvider } from "./context/RiskAnalysisContext";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 5,
    },
    mutations: {
      retry: 0,
    },
  },
});

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#61dafb",
      light: "#8be9fd",
      dark: "#4db8d9",
    },
    secondary: {
      main: "#ff9800",
      light: "#ffb74d",
      dark: "#f57c00",
    },
    error: { main: "#f44336" },
    warning: { main: "#ff9800" },
    success: { main: "#4caf50" },
    background: {
      default: "#0a1929",
      paper: "#132f4c",
    },
    text: {
      primary: "#ffffff",
      secondary: "#b2bac2",
    },
  },
  typography: {
    fontFamily: [
      "-apple-system",
      "BlinkMacSystemFont",
      '"Segoe UI"',
      "Roboto",
      '"Helvetica Neue"',
      "Arial",
      "sans-serif",
    ].join(","),
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 500 },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#132f4c",
          borderBottom: "1px solid rgba(255, 255, 255, 0.12)",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: { backgroundColor: "#132f4c" },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 500,
          borderRadius: 8,
        },
      },
    },
  },
});

const root = createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AuthProvider>
            <PortfolioProvider>
              <RiskAnalysisProvider>
                <App />
              </RiskAnalysisProvider>
            </PortfolioProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
