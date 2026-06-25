import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Marketplaces from "./pages/Marketplaces";
import ConnectMarketplace from "./pages/ConnectMarketplace";
import ConnectionDetail from "./pages/ConnectionDetail";
import ListingDashboard from "./pages/ListingDashboard";
import CreateListing from "./pages/CreateListing";
import BulkUpload from "./pages/BulkUpload";
import InventoryUpdate from "./pages/InventoryUpdate";
import Orders from "./pages/Orders";
import Shipping from "./pages/Shipping";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Marketplaces />} />
        <Route path="/connect" element={<ConnectMarketplace />} />
        <Route path="/connections/:id" element={<ConnectionDetail />} />
        <Route path="/listings" element={<ListingDashboard />} />
        <Route path="/listings/new" element={<CreateListing />} />
        <Route path="/listings/:id/edit" element={<CreateListing />} />
        <Route path="/bulk-upload" element={<BulkUpload />} />
        <Route path="/inventory-update" element={<InventoryUpdate />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/shipping" element={<Shipping />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
