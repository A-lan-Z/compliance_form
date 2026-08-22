import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  ApiProblemError,
  type ApiProblem,
  type WorkflowApi,
  type WorkflowView,
} from "../../api/workflows";
import { workflowFixture } from "../../test/workflowFixture";
import { ComplianceFormPage } from "./ComplianceFormPage";

const ASSET_URN = "urn:li:container:00000000000000000000000000000001";
const FORM_KEY = "dcl.edw.database.fixture";

function createApi(workflow = workflowFixture()): WorkflowApi {
  return {
    openWorkflow: vi.fn().mockResolvedValue(workflow),
    getWorkflow: vi.fn().mockResolvedValue(workflow),
    saveDraft: vi.fn().mockResolvedValue(workflow),
  };
}

function renderPage(api: WorkflowApi) {
  render(
    <ComplianceFormPage assetUrn={ASSET_URN} formKey={FORM_KEY} api={api} />,
  );
}

async function loadedClassSelect() {
  return screen.findByRole("combobox", { name: "Disposal Class" });
}

describe("ComplianceFormPage", () => {
  it("opens and renders the fixture workflow accessibly", async () => {
    const api = createApi();
    renderPage(api);

    expect(screen.getByText("Loading private draft…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", {
        name: "DCL EDW Database Compliance — Fixture",
      }),
    ).toBeInTheDocument();
    expect(api.openWorkflow).toHaveBeenCalledWith(
      { assetUrn: ASSET_URN, formKey: FORM_KEY },
      expect.any(AbortSignal),
    );
    expect(screen.getByText("Fixture EDW Database")).toBeInTheDocument();
    expect(screen.getByText(ASSET_URN)).toBeInTheDocument();
    expect(screen.getByText("DRAFT")).toBeInTheDocument();
    expect(screen.getByTestId("workflow-version")).toHaveTextContent("1");
    expect(
      screen.getByLabelText("Fixture environment notice"),
    ).toHaveTextContent("Local fixture data — no DataHub changes are made.");

    const classSelect = screen.getByRole("combobox", {
      name: "Disposal Class",
    });
    expect(classSelect).toHaveValue("TEST_CLASS_A");
    expect(screen.getAllByRole("option")).toHaveLength(3);
    const action = screen.getByRole("textbox", { name: "Disposal Action" });
    expect(action).toHaveValue("TEST_ACTION_A");
    expect(action).toHaveAttribute("readonly");
  });

  it("previews the derived action but sends only the editable class", async () => {
    const user = userEvent.setup();
    const api = createApi();
    const saved: WorkflowView = {
      ...workflowFixture(),
      version: 2,
      fields: {
        ...workflowFixture().fields,
        disposalClass: {
          ...workflowFixture().fields.disposalClass,
          value: "TEST_CLASS_B",
        },
        disposalAction: {
          ...workflowFixture().fields.disposalAction,
          value: "TEST_ACTION_B",
        },
      },
    };
    vi.mocked(api.saveDraft).mockResolvedValue(saved);
    renderPage(api);

    const classSelect = await loadedClassSelect();
    await user.selectOptions(classSelect, "TEST_CLASS_B");
    expect(screen.getByRole("textbox", { name: "Disposal Action" })).toHaveValue(
      "TEST_ACTION_B",
    );
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(api.saveDraft).toHaveBeenCalledWith(workflowFixture().id, {
      expectedVersion: 1,
      values: { disposalClass: "TEST_CLASS_B" },
    });
    expect(screen.getByTestId("workflow-version")).toHaveTextContent("2");
    expect(screen.getByText("Draft saved.")).toBeInTheDocument();
  });

  it("supports a null class and null derived action", async () => {
    const user = userEvent.setup();
    const api = createApi();
    const saved: WorkflowView = {
      ...workflowFixture(),
      version: 2,
      fields: {
        ...workflowFixture().fields,
        disposalClass: {
          ...workflowFixture().fields.disposalClass,
          value: null,
        },
        disposalAction: {
          ...workflowFixture().fields.disposalAction,
          value: null,
        },
      },
    };
    vi.mocked(api.saveDraft).mockResolvedValue(saved);
    renderPage(api);

    await user.selectOptions(await loadedClassSelect(), "");
    expect(screen.getByRole("textbox", { name: "Disposal Action" })).toHaveValue(
      "",
    );
    await user.click(screen.getByRole("button", { name: "Save draft" }));
    expect(api.saveDraft).toHaveBeenCalledWith(workflowFixture().id, {
      expectedVersion: 1,
      values: { disposalClass: null },
    });
  });

  it("preserves the local selection and displays validation errors", async () => {
    const user = userEvent.setup();
    const api = createApi();
    const problem: ApiProblem = {
      status: 422,
      code: "INVALID_FIELD_VALUE",
      title: "Invalid field value",
      detail: "The draft contains an invalid value.",
      requestId: "request-422",
      fieldErrors: [
        {
          field: "values.disposalClass",
          code: "INVALID_FIELD_VALUE",
          message: "Choose a supported disposal class.",
        },
      ],
    };
    vi.mocked(api.saveDraft).mockRejectedValue(new ApiProblemError(problem));
    renderPage(api);

    const classSelect = await loadedClassSelect();
    await user.selectOptions(classSelect, "TEST_CLASS_B");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(classSelect).toHaveValue("TEST_CLASS_B");
    expect(classSelect).toHaveAttribute("aria-invalid", "true");
    expect(
      screen.getByText("Choose a supported disposal class."),
    ).toBeInTheDocument();
    expect(screen.getByText("Request ID: request-422")).toBeInTheDocument();
  });

  it("requires an explicit reload after a version conflict", async () => {
    const user = userEvent.setup();
    const api = createApi();
    const problem: ApiProblem = {
      status: 409,
      code: "WORKFLOW_VERSION_CONFLICT",
      title: "Draft version conflict",
      detail: "The draft changed.",
      requestId: "request-409",
      currentVersion: 2,
    };
    const current: WorkflowView = {
      ...workflowFixture(),
      version: 2,
    };
    vi.mocked(api.saveDraft).mockRejectedValue(new ApiProblemError(problem));
    vi.mocked(api.getWorkflow).mockResolvedValue(current);
    renderPage(api);

    const classSelect = await loadedClassSelect();
    await user.selectOptions(classSelect, "TEST_CLASS_B");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(
      screen.getByText("This draft changed elsewhere. Reload before saving."),
    ).toBeInTheDocument();
    expect(classSelect).toHaveValue("TEST_CLASS_B");
    expect(api.getWorkflow).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Reload draft" }));
    expect(api.getWorkflow).toHaveBeenCalledWith(workflowFixture().id);
    await waitFor(() => expect(classSelect).toHaveValue("TEST_CLASS_A"));
    expect(screen.getByTestId("workflow-version")).toHaveTextContent("2");
    expect(screen.queryByText("Draft version conflict")).not.toBeInTheDocument();
  });

  it("renders baseline warnings", async () => {
    const api = createApi({
      ...workflowFixture(),
      warnings: [
        {
          code: "BASELINE_DISPOSAL_ACTION_MISMATCH",
          message: "The existing action did not match the configured class.",
        },
      ],
    });
    renderPage(api);

    expect(
      await screen.findByLabelText("Draft warnings"),
    ).toHaveTextContent(
      "The existing action did not match the configured class.",
    );
  });

  it("does not expose out-of-scope workflow controls", async () => {
    renderPage(createApi());
    await loadedClassSelect();

    for (const name of [
      "Submit",
      "Approve",
      "Reject",
      "Publish",
      "Verify",
      "Delete",
      "Reset",
    ]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });
});
