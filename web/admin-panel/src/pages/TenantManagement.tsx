import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Users, Plus, Trash2, Eye, DollarSign } from 'lucide-react';

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
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [formData, setFormData] = useState({
    tenant_name: '',
    admin_email: '',
    admin_password: '',
    tier: 'basic'
  });

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const loadTenants = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(
        `${import.meta.env.VITE_CONTROL_PLANE_API_URL}/tenants`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setTenants(data.tenants || []);
      }
    } catch (error) {
      console.error('Failed to load tenants:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  const activeTenants = tenants.filter(t => t.status !== 'deleted');
  const stats = {
    total: activeTenants.length,
    basic: activeTenants.filter(t => t.tier === 'basic').length,
    premium: activeTenants.filter(t => t.tier === 'premium').length,
    active: tenants.filter(t => t.status === 'active').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
            Tenant Management
          </h1>
          <p className="text-slate-400 mt-1">Manage your SaaS tenants and subscriptions</p>
        </div>
        <Button 
          onClick={() => setShowAddModal(true)}
          className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Tenant
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-6 bg-slate-800/50 border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Total Tenants</p>
              <p className="text-3xl font-bold text-white mt-1">{stats.total}</p>
            </div>
            <Users className="w-10 h-10 text-blue-400" />
          </div>
        </Card>
        
        <Card className="p-6 bg-slate-800/50 border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Basic Tier</p>
              <p className="text-3xl font-bold text-cyan-400 mt-1">{stats.basic}</p>
            </div>
            <div className="text-2xl">💼</div>
          </div>
        </Card>
        
        <Card className="p-6 bg-slate-800/50 border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Premium Tier</p>
              <p className="text-3xl font-bold text-purple-400 mt-1">{stats.premium}</p>
            </div>
            <div className="text-2xl">⭐</div>
          </div>
        </Card>
        
        <Card className="p-6 bg-slate-800/50 border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Active</p>
              <p className="text-3xl font-bold text-green-400 mt-1">{stats.active}</p>
            </div>
            <div className="text-2xl">✅</div>
          </div>
        </Card>
      </div>

      {/* Monthly Revenue */}
      <Card className="p-6 bg-slate-800/50 border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
          <DollarSign className="w-5 h-5 mr-2 text-green-400" />
          Monthly Revenue
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-3xl font-bold text-green-400">${(stats.basic * 29) + (stats.premium * 99)}</p>
            <p className="text-sm text-slate-400">Recurring monthly revenue from active tenants</p>
          </div>
          <div className="text-right text-sm text-slate-400">
            <p>Basic: $29/month</p>
            <p>Premium: $99/month</p>
          </div>
        </div>
      </Card>

      {/* Tenants List */}
      <Card className="p-6 bg-slate-800/50 border-slate-700">
        <h2 className="text-xl font-semibold mb-4">Tenants</h2>
        
        {loading ? (
          <div className="text-center py-8 text-slate-400">Loading tenants...</div>
        ) : activeTenants.length === 0 ? (
          <div className="text-center py-8 text-slate-400">No tenants yet</div>
        ) : (
          <div className="space-y-3">
            {activeTenants.map((tenant) => (
              <div
                key={tenant.tenant_id}
                className="p-4 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold text-white">{tenant.tenant_name}</h3>
                      <Badge
                        variant={tenant.tier === 'premium' ? 'default' : 'secondary'}
                        className={tenant.tier === 'premium' ? 'bg-purple-500' : 'bg-cyan-500'}
                      >
                        {tenant.tier}
                      </Badge>
                      <Badge
                        variant={tenant.status === 'active' ? 'default' : 'secondary'}
                        className={tenant.status === 'active' ? 'bg-green-500' : 'bg-yellow-500'}
                      >
                        {tenant.status}
                      </Badge>
                    </div>
                    <div className="mt-2 space-y-1 text-sm text-slate-300">
                      <p><span className="text-slate-400">Email:</span> {tenant.admin_email}</p>
                      <p><span className="text-slate-400">ID:</span> {tenant.tenant_id}</p>
                      <p><span className="text-slate-400">Created:</span> {new Date(tenant.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-slate-600 hover:bg-slate-700"
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-red-600 text-red-400 hover:bg-red-600/20"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Add Tenant Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Add New Tenant</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tenant_name" className="text-slate-300">Company Name</Label>
              <Input
                id="tenant_name"
                value={formData.tenant_name}
                onChange={(e) => setFormData({ ...formData, tenant_name: e.target.value })}
                className="bg-slate-700 border-slate-600 text-white"
                placeholder="Acme Corporation"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="admin_email" className="text-slate-300">Admin Email</Label>
              <Input
                id="admin_email"
                type="email"
                value={formData.admin_email}
                onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                className="bg-slate-700 border-slate-600 text-white"
                placeholder="admin@acme.com"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="admin_password" className="text-slate-300">Admin Password</Label>
              <Input
                id="admin_password"
                type="password"
                value={formData.admin_password}
                onChange={(e) => setFormData({ ...formData, admin_password: e.target.value })}
                className="bg-slate-700 border-slate-600 text-white"
                placeholder="Min 8 characters"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="tier" className="text-slate-300">Tier</Label>
              <Select value={formData.tier} onValueChange={(value) => setFormData({ ...formData, tier: value })}>
                <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-700 border-slate-600">
                  <SelectItem value="basic">Basic ($29/month)</SelectItem>
                  <SelectItem value="premium">Premium ($99/month)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowAddModal(false);
                setFormData({ tenant_name: '', admin_email: '', admin_password: '', tier: 'basic' });
              }}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              Cancel
            </Button>
            <Button
              onClick={async () => {
                if (!formData.tenant_name || !formData.admin_email || !formData.admin_password) {
                  showToast('Please fill in all fields', 'error');
                  return;
                }
                if (formData.admin_password.length < 8) {
                  showToast('Password must be at least 8 characters', 'error');
                  return;
                }
                
                try {
                  const token = localStorage.getItem('adminToken');
                  const response = await fetch(
                    `${import.meta.env.VITE_CONTROL_PLANE_API_URL}/tenants`,
                    {
                      method: 'POST',
                      headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify(formData)
                    }
                  );
                  
                  if (response.ok) {
                    showToast('Tenant created successfully', 'success');
                    setShowAddModal(false);
                    setFormData({ tenant_name: '', admin_email: '', admin_password: '', tier: 'basic' });
                    loadTenants();
                  } else {
                    const error = await response.json();
                    showToast(error.error || 'Failed to create tenant', 'error');
                  }
                } catch (error) {
                  showToast('Network error', 'error');
                }
              }}
              className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
            >
              Create Tenant
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-5">
          <div className={`px-6 py-4 rounded-lg shadow-lg border ${
            toast.type === 'success' 
              ? 'bg-green-500 border-green-600 text-white' 
              : 'bg-red-500 border-red-600 text-white'
          }`}>
            <p className="font-medium">{toast.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}
