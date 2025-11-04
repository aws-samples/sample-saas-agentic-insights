import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, Users, DollarSign, TrendingDown, User } from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarInset,
} from '@/components/ui/sidebar';

const parseJWT = (token: string) => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload;
  } catch {
    return null;
  }
};

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();

  const token = localStorage.getItem('adminToken');
  const user = token ? parseJWT(token) : null;
  const userName = user?.email?.split('@')[0] || 'Admin';

  const handleLogout = () => {
    localStorage.removeItem('adminToken');
    navigate('/login');
  };

  const navItems = [
    // { path: '/tenants', label: 'Tenant Management', icon: Users },
    // { path: '/cost-analysis', label: 'Cost Analysis', icon: DollarSign, badge: 'AI' },
    { path: '/churn-analysis', label: 'Churn Analysis', icon: TrendingDown, badge: 'AI' }
  ];

  return (
    <SidebarProvider>
      <div className="dark bg-linear-to-br from-slate-900 via-purple-900 to-slate-900 text-white min-h-screen flex w-full">
        <Sidebar>
          <SidebarHeader>
            <h2 className="text-xl font-bold text-white px-4 py-2">🔧 SaaS Admin</h2>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {navItems.map(({ path, label, icon: Icon, badge }) => (
                    <SidebarMenuItem key={path}>
                      <SidebarMenuButton asChild isActive={location.pathname === path}>
                        <Link to={path} className="flex items-center">
                          <Icon className="w-5 h-5" />
                          <span>{label}</span>
                          {badge && (
                            <span className="ml-auto bg-gradient-to-r from-purple-500 to-blue-500 text-xs px-2 py-1 rounded-full">
                              {badge}
                            </span>
                          )}
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
          <SidebarFooter>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton className="flex items-center gap-2 text-muted-foreground">
                  <User className="w-4 h-4" />
                  <span className="text-sm">{userName}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton onClick={handleLogout} className="text-red-400 hover:text-red-300">
                  <LogOut className="w-5 h-5" />
                  <span>Logout</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        </Sidebar>
        <SidebarInset className="flex-1">
          <main className="p-8">
            <Outlet />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
