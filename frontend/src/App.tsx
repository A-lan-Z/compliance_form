import { ComplianceFormPage } from "./features/compliance/ComplianceFormPage";
import type { WorkflowApi } from "./api/workflows";

interface RouteLocation {
  pathname: string;
  search: string;
}

interface AppProps {
  location?: RouteLocation;
  api?: WorkflowApi;
}

export function App({ location = window.location, api }: AppProps) {
  const parameters = new URLSearchParams(location.search);
  const assetUrn = parameters.get("assetUrn");
  const formKey = parameters.get("formKey");

  if (
    location.pathname !== "/compliance-form" ||
    !assetUrn ||
    !formKey
  ) {
    return (
      <main className="page-shell">
        <section className="content-card" role="alert">
          <h1>DCL compliance form</h1>
          <p>
            This route requires both an asset URN and a form key. Open the
            configured fixture form URL.
          </p>
        </section>
      </main>
    );
  }

  return (
    <ComplianceFormPage assetUrn={assetUrn} formKey={formKey} api={api} />
  );
}
