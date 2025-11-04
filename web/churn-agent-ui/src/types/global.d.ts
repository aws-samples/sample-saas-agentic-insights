declare global {
  interface Window {
    APP_CONFIG?: {
      CONTROL_PLANE_API_URL: string;
      APP_PLANE_API_URL: string;
      SAAS_APP_URL: string;
      ADMIN_PANEL_URL: string;
      LANDING_PAGE_URL: string;
      REGION: string;
    };
    Chart: any;
  }
}

export {};
