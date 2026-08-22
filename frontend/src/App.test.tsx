import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { WorkflowApi } from "./api/workflows";
import { App } from "./App";
import { workflowFixture } from "./test/workflowFixture";

function createApi(): WorkflowApi {
  const workflow = workflowFixture();
  return {
    openWorkflow: vi.fn().mockResolvedValue(workflow),
    getWorkflow: vi.fn().mockResolvedValue(workflow),
    saveDraft: vi.fn().mockResolvedValue(workflow),
  };
}

describe("App routing", () => {
  it("passes decoded fixture query parameters to the open call", async () => {
    const api = createApi();
    const workflow = workflowFixture();
    const query = new URLSearchParams({
      assetUrn: workflow.asset.urn,
      formKey: workflow.form.key,
    });

    render(
      <App
        location={{ pathname: "/compliance-form", search: `?${query}` }}
        api={api}
      />,
    );

    await screen.findByRole("heading", { name: workflow.form.displayName });
    expect(api.openWorkflow).toHaveBeenCalledWith(
      { assetUrn: workflow.asset.urn, formKey: workflow.form.key },
      expect.any(AbortSignal),
    );
  });

  it("rejects a route with missing required parameters without an API call", () => {
    const api = createApi();
    render(
      <App
        location={{ pathname: "/compliance-form", search: "?formKey=fixture" }}
        api={api}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "This route requires both an asset URN and a form key.",
    );
    expect(api.openWorkflow).not.toHaveBeenCalled();
  });
});
