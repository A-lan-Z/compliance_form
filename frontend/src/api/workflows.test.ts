import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiProblemError,
  getWorkflow,
  openWorkflow,
  saveDraft,
  type ApiProblem,
} from "./workflows";
import { workflowFixture } from "../test/workflowFixture";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("workflow API client", () => {
  it("uses the versioned open and retrieve contracts", async () => {
    const workflow = workflowFixture();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(workflow, 201))
      .mockResolvedValueOnce(jsonResponse(workflow));
    vi.stubGlobal("fetch", fetchMock);

    await openWorkflow({
      assetUrn: workflow.asset.urn,
      formKey: workflow.form.key,
    });
    await getWorkflow(workflow.id);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/workflows/open",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify({
          assetUrn: workflow.asset.urn,
          formKey: workflow.form.key,
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/v1/workflows/${workflow.id}`,
      expect.objectContaining({ method: "GET", credentials: "same-origin" }),
    );
  });

  it("sends only the expected version and editable class when saving", async () => {
    const workflow = workflowFixture();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(workflow));
    vi.stubGlobal("fetch", fetchMock);

    await saveDraft(workflow.id, {
      expectedVersion: 1,
      values: { disposalClass: null },
    });

    const init = fetchMock.mock.calls[0]?.[1];
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      `/api/v1/workflows/${workflow.id}/draft`,
    );
    expect(init).toEqual(
      expect.objectContaining({ method: "PUT", credentials: "same-origin" }),
    );
    expect(JSON.parse(String(init?.body))).toEqual({
      expectedVersion: 1,
      values: { disposalClass: null },
    });
    expect(String(init?.body)).not.toContain("disposalAction");
  });

  it("retains the server problem contract for callers", async () => {
    const problem: ApiProblem = {
      status: 409,
      code: "WORKFLOW_VERSION_CONFLICT",
      title: "Draft version conflict",
      detail: "The draft changed.",
      requestId: "request-123",
      currentVersion: 2,
      fieldErrors: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(problem, 409)),
    );

    const promise = saveDraft(workflowFixture().id, {
      expectedVersion: 1,
      values: { disposalClass: "TEST_CLASS_B" },
    });

    await expect(promise).rejects.toEqual(new ApiProblemError(problem));
  });
});
