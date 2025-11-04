import { useState, useEffect } from "react";
import { Plus, Eye, Trash2 } from "lucide-react";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface Tenant {
  tenant_id: string;
  tenant_name: string;
  admin_email: string;
  tier: string;
  status: string;
  created_at: string;
}

export default function TenantManagement() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [_, setShowAddModal] = useState(false);

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(
        `${import.meta.env.VITE_CONTROL_PLANE_API_URL}/tenants`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setTenants(data.tenants || []);
      }
    } catch (error) {
      console.error("Error loading tenants:", error);
    } finally {
      setLoading(false);
    }
  };

  const deleteTenant = async (tenantId: string) => {
    if (!confirm("Are you sure you want to delete this tenant?")) return;

    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(
        `${import.meta.env.VITE_CONTROL_PLANE_API_URL}/tenants/${tenantId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        await loadTenants();
      }
    } catch (error) {
      console.error("Error deleting tenant:", error);
    }
  };

  const activeTenants = tenants.filter((tenant) => tenant.status !== "deleted");

  if (loading) {
    return (
      <div>
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
            Tenant Management
          </h1>
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Add Tenant
          </Button>
        </div>

        <div className="grid gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="flex justify-between items-start">
                <div className="flex-1">
                  <Skeleton className="h-6 w-48 mb-2" />
                  <div className="space-y-1 mb-3">
                    <div className="flex items-center">
                      <span className="text-muted-foreground">
                        <strong>Email:</strong>
                      </span>
                      <Skeleton className="h-4 w-40 ml-2" />
                    </div>
                    <div className="flex items-center">
                      <span className="text-muted-foreground">
                        <strong>ID:</strong>
                      </span>
                      <Skeleton className="h-4 w-64 ml-2" />
                    </div>
                    <div className="flex items-center">
                      <span className="text-muted-foreground">
                        <strong>Created:</strong>
                      </span>
                      <Skeleton className="h-4 w-24 ml-2" />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Skeleton className="h-6 w-16 rounded-full" />
                    <Skeleton className="h-6 w-16 rounded-full" />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="icon" disabled>
                    <Eye className="w-4 h-4" />
                  </Button>
                  <Button variant="destructive" size="icon" disabled>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
          Tenant Management
        </h1>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Tenant
        </Button>
      </div>

      {activeTenants.length === 0 ? (
        <div className="text-center py-12 bg-gray-800/30 rounded-lg">
          <h3 className="text-xl font-semibold mb-2">No tenants yet</h3>
          <p className="text-gray-400">
            Start by adding your first tenant to the platform
          </p>
        </div>
      ) : (
        <div className="grid gap-6">
          {activeTenants.map((tenant) => (
            <Card key={tenant.tenant_id}>
              <CardContent className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="mb-2">{tenant.tenant_name}</CardTitle>
                  <p className="text-muted-foreground mb-1">
                    <strong>Email:</strong> {tenant.admin_email}
                  </p>
                  <p className="text-muted-foreground mb-1">
                    <strong>ID:</strong> {tenant.tenant_id}
                  </p>
                  <p className="text-muted-foreground mb-3">
                    <strong>Created:</strong>{" "}
                    {new Date(tenant.created_at).toLocaleDateString()}
                  </p>
                  <div className="flex gap-2">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        tenant.tier === "premium"
                          ? "bg-gradient-to-r from-purple-500 to-blue-500 text-white"
                          : "bg-gray-600 text-gray-200"
                      }`}
                    >
                      {tenant.tier}
                    </span>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        tenant.status === "active"
                          ? "bg-green-600 text-white"
                          : "bg-yellow-600 text-white"
                      }`}
                    >
                      {tenant.status}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="icon">
                    <Eye className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="destructive"
                    size="icon"
                    onClick={() => deleteTenant(tenant.tenant_id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
