import { Box, useMediaQuery, useTheme } from "@mui/material";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import Footer from "../components/navigation/Footer";
import Header from "../components/navigation/Header";
import Sidebar from "../components/navigation/Sidebar";

const DRAWER_WIDTH = 240;

const MainLayout = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => setMobileOpen((prev) => !prev);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Header onMenuClick={handleDrawerToggle} />
      <Box sx={{ display: "flex", flex: 1 }}>
        <Sidebar
          mobileOpen={mobileOpen}
          onClose={handleDrawerToggle}
          isMobile={isMobile}
        />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: { xs: 2, sm: 3 },
            // On desktop, offset by sidebar width; on mobile sidebar is an overlay
            ml: { xs: 0, sm: `${DRAWER_WIDTH}px` },
            width: { xs: "100%", sm: `calc(100% - ${DRAWER_WIDTH}px)` },
            minHeight: "calc(100vh - 64px)",
          }}
        >
          {/* Spacer for fixed AppBar */}
          <Box sx={{ mt: { xs: 7, sm: 8 }, mb: 2 }}>
            <Outlet />
          </Box>
        </Box>
      </Box>
      <Box sx={{ ml: { xs: 0, sm: `${DRAWER_WIDTH}px` } }}>
        <Footer />
      </Box>
    </Box>
  );
};

export default MainLayout;
