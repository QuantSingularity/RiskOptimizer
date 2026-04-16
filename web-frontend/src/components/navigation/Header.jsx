import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import HomeIcon from "@mui/icons-material/Home";
import LogoutIcon from "@mui/icons-material/Logout";
import MenuIcon from "@mui/icons-material/Menu";
import NotificationsIcon from "@mui/icons-material/Notifications";
import SettingsIcon from "@mui/icons-material/Settings";
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  Chip,
  Divider,
  IconButton,
  ListItemIcon,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { formatAddress } from "../../utils/formatters";

const Header = ({ onMenuClick }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState(null);
  const [notifAnchor, setNotifAnchor] = useState(null);

  const handleProfileOpen = (e) => setAnchorEl(e.currentTarget);
  const handleProfileClose = () => setAnchorEl(null);
  const handleNotifOpen = (e) => setNotifAnchor(e.currentTarget);
  const handleNotifClose = () => setNotifAnchor(null);

  const handleLogout = () => {
    handleProfileClose();
    logout();
    navigate("/");
  };

  const handleSettings = () => {
    handleProfileClose();
    navigate("/settings");
  };

  const notifications = [
    {
      id: 1,
      text: "Portfolio up 1.02% today",
      time: "5m ago",
      type: "success",
    },
    {
      id: 2,
      text: "Risk score increased to 65",
      time: "1h ago",
      type: "warning",
    },
    { id: 3, text: "BTC allocation near limit", time: "3h ago", type: "info" },
    {
      id: 4,
      text: "Optimization suggestion ready",
      time: "1d ago",
      type: "info",
    },
  ];

  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        backgroundColor: "background.paper",
        boxShadow: "0px 1px 0px rgba(255,255,255,0.08)",
      }}
    >
      <Toolbar>
        {/* Mobile menu button */}
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onMenuClick}
          sx={{ mr: 2, display: { sm: "none" } }}
        >
          <MenuIcon />
        </IconButton>

        {/* Brand */}
        <Typography
          variant="h6"
          noWrap
          component="div"
          sx={{
            flexGrow: 1,
            fontFamily: "Poppins, sans-serif",
            fontWeight: 700,
            color: "primary.main",
            cursor: "pointer",
            display: { xs: "none", sm: "block" },
          }}
          onClick={() => navigate("/")}
        >
          RiskOptimizer
        </Typography>

        <Box sx={{ flexGrow: 1, display: { xs: "block", sm: "none" } }} />

        {/* Right actions */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {/* Home */}
          <Tooltip title="Home">
            <IconButton
              color="inherit"
              onClick={() => navigate("/")}
              size="small"
            >
              <HomeIcon />
            </IconButton>
          </Tooltip>

          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton color="inherit" onClick={handleNotifOpen} size="small">
              <Badge badgeContent={notifications.length} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* Profile */}
          <Tooltip title="Account">
            <IconButton
              color="inherit"
              onClick={handleProfileOpen}
              size="small"
              sx={{ ml: 0.5 }}
            >
              <Avatar
                sx={{
                  width: 32,
                  height: 32,
                  bgcolor: "primary.main",
                  fontSize: "0.85rem",
                }}
              >
                {user?.username?.[0]?.toUpperCase() ?? (
                  <AccountCircleIcon sx={{ fontSize: 20 }} />
                )}
              </Avatar>
            </IconButton>
          </Tooltip>
        </Box>

        {/* Notifications menu */}
        <Menu
          anchorEl={notifAnchor}
          open={Boolean(notifAnchor)}
          onClose={handleNotifClose}
          PaperProps={{
            sx: { width: 300, backgroundColor: "background.paper" },
          }}
          transformOrigin={{ horizontal: "right", vertical: "top" }}
          anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        >
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="subtitle2" fontWeight={700}>
              Notifications
            </Typography>
          </Box>
          <Divider />
          {notifications.map((n) => (
            <MenuItem
              key={n.id}
              onClick={handleNotifClose}
              sx={{ py: 1.5, alignItems: "flex-start" }}
            >
              <Box sx={{ flex: 1 }}>
                <Typography variant="body2">{n.text}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {n.time}
                </Typography>
              </Box>
            </MenuItem>
          ))}
        </Menu>

        {/* Profile menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleProfileClose}
          PaperProps={{
            sx: { width: 230, backgroundColor: "background.paper" },
          }}
          transformOrigin={{ horizontal: "right", vertical: "top" }}
          anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        >
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="subtitle2" fontWeight={700}>
              {user?.username || "User"}
            </Typography>
            {user?.wallet_address && (
              <Typography variant="caption" color="text.secondary">
                {formatAddress(user.wallet_address)}
              </Typography>
            )}
          </Box>
          <Divider />
          <MenuItem onClick={handleSettings}>
            <ListItemIcon>
              <SettingsIcon fontSize="small" />
            </ListItemIcon>
            Settings
          </MenuItem>
          <Divider />
          <MenuItem onClick={handleLogout} sx={{ color: "error.main" }}>
            <ListItemIcon>
              <LogoutIcon fontSize="small" color="error" />
            </ListItemIcon>
            Sign Out
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
