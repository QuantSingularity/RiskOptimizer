import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import AssessmentIcon from "@mui/icons-material/Assessment";
import DashboardIcon from "@mui/icons-material/Dashboard";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import HomeIcon from "@mui/icons-material/Home";
import SettingsIcon from "@mui/icons-material/Settings";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  Box,
  Divider,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";

const drawerWidth = 240;

const menuItems = [
  { text: "Dashboard", icon: <DashboardIcon />, path: "/dashboard" },
  { text: "Portfolio", icon: <AccountBalanceWalletIcon />, path: "/portfolio" },
  { text: "Risk Analysis", icon: <AssessmentIcon />, path: "/risk-analysis" },
  { text: "Optimization", icon: <TrendingUpIcon />, path: "/optimization" },
  { text: "Settings", icon: <SettingsIcon />, path: "/settings" },
];

const Sidebar = ({ mobileOpen, onClose, isMobile }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const handleNavigation = (path) => {
    navigate(path);
    if (isMobile) {
      onClose();
    }
  };

  const drawer = (
    <div>
      <Box
        sx={{
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          cursor: "pointer",
        }}
        onClick={() => navigate("/")}
      >
        <Typography
          variant="h6"
          sx={{
            fontFamily: "Poppins, sans-serif",
            fontWeight: 700,
            color: "primary.main",
            fontSize: "1.1rem",
          }}
        >
          RiskOptimizer
        </Typography>
      </Box>
      <List sx={{ pt: 2 }}>
        <ListItemButton
          onClick={() => handleNavigation("/")}
          sx={{
            mb: 0.5,
            mx: 1,
            borderRadius: 1,
            "&:hover": { backgroundColor: "rgba(97, 218, 251, 0.05)" },
          }}
        >
          <ListItemIcon sx={{ color: "text.secondary", minWidth: 40 }}>
            <HomeIcon />
          </ListItemIcon>
          <ListItemText primary="Home" sx={{ color: "text.primary" }} />
        </ListItemButton>
        <Divider sx={{ my: 1, backgroundColor: "rgba(255, 255, 255, 0.06)" }} />
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.text}
              onClick={() => handleNavigation(item.path)}
              selected={isActive}
              sx={{
                mb: 1,
                mx: 1,
                borderRadius: 1,
                "&.Mui-selected": {
                  backgroundColor: "rgba(97, 218, 251, 0.1)",
                  "&:hover": {
                    backgroundColor: "rgba(97, 218, 251, 0.15)",
                  },
                },
                "&:hover": {
                  backgroundColor: "rgba(97, 218, 251, 0.05)",
                },
              }}
            >
              <ListItemIcon
                sx={{
                  color: isActive ? "primary.main" : "text.secondary",
                  minWidth: 40,
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.text}
                sx={{
                  color: isActive ? "primary.main" : "text.primary",
                  "& .MuiTypography-root": {
                    fontWeight: isActive ? 600 : 400,
                  },
                }}
              />
            </ListItemButton>
          );
        })}
      </List>
      <Divider sx={{ my: 2, backgroundColor: "rgba(255, 255, 255, 0.1)" }} />
      <List>
        <ListItemButton sx={{ mx: 1, borderRadius: 1 }}>
          <ListItemIcon sx={{ color: "text.secondary", minWidth: 40 }}>
            <HelpOutlineIcon />
          </ListItemIcon>
          <ListItemText primary="Help & Support" />
        </ListItemButton>
      </List>
    </div>
  );

  return (
    <Box
      component="nav"
      sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
    >
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", sm: "none" },
          "& .MuiDrawer-paper": {
            boxSizing: "border-box",
            width: drawerWidth,
            backgroundColor: "background.paper",
          },
        }}
      >
        {drawer}
      </Drawer>

      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", sm: "block" },
          "& .MuiDrawer-paper": {
            boxSizing: "border-box",
            width: drawerWidth,
            backgroundColor: "background.paper",
            borderRight: "1px solid rgba(255, 255, 255, 0.1)",
          },
        }}
        open
      >
        {drawer}
      </Drawer>
    </Box>
  );
};

export default Sidebar;
