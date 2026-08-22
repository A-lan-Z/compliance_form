export interface WorkflowWarning {
  code: string;
  message: string;
}

export interface FieldError {
  field: string;
  code: string;
  message: string;
}

export interface ApiProblem {
  type?: string;
  status: number;
  code: string;
  title: string;
  detail: string;
  requestId?: string;
  fieldErrors?: FieldError[];
  currentVersion?: number;
}

export interface WorkflowView {
  id: string;
  asset: {
    urn: string;
    displayName: string;
    entityType: string;
    subTypes: string[];
  };
  form: {
    key: string;
    displayName: string;
    revision: number;
    definitionSha256: string;
  };
  status: {
    review: "DRAFT";
    publication: "NOT_STARTED";
  };
  version: number;
  fields: {
    disposalClass: {
      value: string | null;
      editable: boolean;
      allowedValues: string[];
    };
    disposalAction: {
      value: string | null;
      editable: false;
      derivedFrom: "disposalClass";
      previewByDisposalClass: Record<string, string>;
    };
  };
  baseline: {
    capturedAt: string;
    sha256: string;
  };
  warnings: WorkflowWarning[];
  permissions: {
    canEdit: boolean;
  };
}

export interface OpenWorkflowRequest {
  assetUrn: string;
  formKey: string;
}

export interface SaveDraftRequest {
  expectedVersion: number;
  values: {
    disposalClass: string | null;
  };
}

export class ApiProblemError extends Error {
  readonly problem: ApiProblem;

  constructor(problem: ApiProblem) {
    super(problem.detail);
    this.name = "ApiProblemError";
    this.problem = problem;
  }
}

async function requestJson<T>(
  url: string,
  init: RequestInit,
): Promise<T> {
  const response = await fetch(url, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...init.headers,
    },
  });
  const body = (await response.json()) as T | ApiProblem;

  if (!response.ok) {
    throw new ApiProblemError(body as ApiProblem);
  }

  return body as T;
}

export function openWorkflow(
  request: OpenWorkflowRequest,
  signal?: AbortSignal,
): Promise<WorkflowView> {
  return requestJson<WorkflowView>("/api/v1/workflows/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
}

export function getWorkflow(
  workflowId: string,
  signal?: AbortSignal,
): Promise<WorkflowView> {
  return requestJson<WorkflowView>(
    `/api/v1/workflows/${encodeURIComponent(workflowId)}`,
    { method: "GET", signal },
  );
}

export function saveDraft(
  workflowId: string,
  request: SaveDraftRequest,
  signal?: AbortSignal,
): Promise<WorkflowView> {
  return requestJson<WorkflowView>(
    `/api/v1/workflows/${encodeURIComponent(workflowId)}/draft`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    },
  );
}

export interface WorkflowApi {
  openWorkflow: typeof openWorkflow;
  getWorkflow: typeof getWorkflow;
  saveDraft: typeof saveDraft;
}

export const workflowApi: WorkflowApi = {
  openWorkflow,
  getWorkflow,
  saveDraft,
};
