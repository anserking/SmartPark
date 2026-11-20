import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from 'sonner';
import { ThemeProvider } from 'next-themes';

import Layout from './components/Layout';

const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ParkingSpotsPage = lazy(() => import('./pages/ParkingSpotsPage'));
const ParkingSessionsPage = lazy(() => import('./pages/ParkingSessionsPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const RewardsPage = lazy(() => import('./pages/RewardsPage'));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <BrowserRouter>
        <Suspense
          fallback={
            <div
              role="status"
              className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground"
            >
              Loading SmartPark…
            </div>
          }
        >
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="parking-spots" element={<ParkingSpotsPage />} />
              <Route path="sessions" element={<ParkingSessionsPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="rewards" element={<RewardsPage />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="admin" element={<AdminPage />} />
            </Route>
          </Routes>
        </Suspense>
        <Toaster position="top-right" />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
