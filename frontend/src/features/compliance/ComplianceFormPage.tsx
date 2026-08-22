import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiProblemError,
  workflowApi,
  type ApiProblem,
  type WorkflowApi,
  type WorkflowView,
} from "../../api/workflows";

interface ComplianceFormPageProps {
  assetUrn: string;
  formKey: string;
  api?: WorkflowApi;
}

type Activity = "idle" | "saving" | "reloading";

const FIXTURE_NOTICE = "Local fixture data — no DataHub changes are made.";
const CONFLICT_MESSAGE =
  "This draft changed elsewhere. Reload before saving.";

function displayProblem(error: unknown): ApiProblem {
  if (error instanceof ApiProblemError) {
    return error.problem;
  }

  return {
    status: 0,
    code: "DEPENDENCY_UNAVAILABLE",
    title: "Application unavailable",
    detail: "The compliance application could not be reached. Try again.",
  };
}

function ProblemAlert({ problem }: { problem: ApiProblem }) {
  return (
    <div className="alert alert-error" role="alert">
      <p className="alert-title">{problem.title}</p>
      <p>{problem.detail}</p>
      {problem.requestId ? (
        <p className="request-id">Request ID: {problem.requestId}</p>
      ) : null}
    </div>
  );
}

export function ComplianceFormPage({
  assetUrn,
  formKey,
  api = workflowApi,
}: ComplianceFormPageProps) {
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [workflow, setWorkflow] = useState<WorkflowView | null>(null);
  const [selectedClass, setSelectedClass] = useState<string | null>(null);
  const [loadProblem, setLoadProblem] = useState<ApiProblem | null>(null);
  const [saveProblem, setSaveProblem] = useState<ApiProblem | null>(null);
  const [activity, setActivity] = useState<Activity>("idle");
  const [conflicted, setConflicted] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const mutationAlertRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    void api
      .openWorkflow({ assetUrn, formKey }, controller.signal)
      .then((response) => {
        if (!active) return;
        setWorkflow(response);
        setSelectedClass(response.fields.disposalClass.value);
        setLoading(false);
      })
      .catch((error: unknown) => {
        if (!active || controller.signal.aborted) return;
        setLoadProblem(displayProblem(error));
        setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [api, assetUrn, formKey, loadAttempt]);

  useEffect(() => {
    if (saveProblem || conflicted) {
      mutationAlertRef.current?.focus();
    }
  }, [conflicted, saveProblem]);

  const actionPreview =
    workflow && selectedClass
      ? (workflow.fields.disposalAction.previewByDisposalClass[
          selectedClass
        ] ?? null)
      : null;
  const classErrors =
    saveProblem?.fieldErrors?.filter(
      ({ field }) =>
        field === "disposalClass" || field === "values.disposalClass",
    ) ?? [];
  const classDescribedBy = [
    "disposal-class-help",
    classErrors.length ? "disposal-class-error" : null,
  ]
    .filter(Boolean)
    .join(" ");

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workflow || !workflow.permissions.canEdit || conflicted) return;

    setActivity("saving");
    setSaveProblem(null);
    setSaveMessage("");
    const priorVersion = workflow.version;

    try {
      const response = await api.saveDraft(workflow.id, {
        expectedVersion: priorVersion,
        values: { disposalClass: selectedClass },
      });
      setWorkflow(response);
      setSelectedClass(response.fields.disposalClass.value);
      setSaveMessage(
        response.version === priorVersion
          ? "Draft is already up to date."
          : "Draft saved.",
      );
    } catch (error: unknown) {
      const problem = displayProblem(error);
      setSaveProblem(problem);
      if (problem.code === "WORKFLOW_VERSION_CONFLICT") {
        setConflicted(true);
      }
    } finally {
      setActivity("idle");
    }
  }

  async function handleReload() {
    if (!workflow) return;

    setActivity("reloading");
    setSaveProblem(null);
    setSaveMessage("");
    try {
      const response = await api.getWorkflow(workflow.id);
      setWorkflow(response);
      setSelectedClass(response.fields.disposalClass.value);
      setConflicted(false);
      setSaveMessage("Draft reloaded.");
    } catch (error: unknown) {
      setSaveProblem(displayProblem(error));
    } finally {
      setActivity("idle");
    }
  }

  return (
    <main className="page-shell" aria-busy={loading}>
      <aside className="fixture-banner" aria-label="Fixture environment notice">
        {FIXTURE_NOTICE}
      </aside>

      {loading ? (
        <section className="loading-panel" aria-live="polite">
          <h1>DCL compliance form</h1>
          <p>Loading private draft…</p>
        </section>
      ) : null}

      {!loading && loadProblem ? (
        <section className="content-card">
          <h1>DCL compliance form</h1>
          <ProblemAlert problem={loadProblem} />
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              setLoading(true);
              setLoadProblem(null);
              setLoadAttempt((attempt) => attempt + 1);
            }}
          >
            Try again
          </button>
        </section>
      ) : null}

      {!loading && workflow ? (
        <article className="content-card">
          <header className="page-header">
            <p className="eyebrow">Private compliance draft</p>
            <h1>{workflow.form.displayName}</h1>
            <p className="asset-name">{workflow.asset.displayName}</p>
          </header>

          <dl className="workflow-summary">
            <div>
              <dt>Asset URN</dt>
              <dd>
                <code>{workflow.asset.urn}</code>
              </dd>
            </div>
            <div>
              <dt>Form revision</dt>
              <dd>{workflow.form.revision}</dd>
            </div>
            <div>
              <dt>Review status</dt>
              <dd>{workflow.status.review}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd data-testid="workflow-version">{workflow.version}</dd>
            </div>
          </dl>

          {workflow.warnings.length ? (
            <section className="alert alert-warning" aria-label="Draft warnings">
              <h2>Review the imported fixture values</h2>
              <ul>
                {workflow.warnings.map((warning) => (
                  <li key={warning.code}>{warning.message}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <form className="draft-form" onSubmit={handleSave}>
            <div className="field-group">
              <label htmlFor="disposal-class">Disposal Class</label>
              <p className="field-help" id="disposal-class-help">
                Choose a fixture class or leave the draft incomplete.
              </p>
              <select
                id="disposal-class"
                value={selectedClass ?? ""}
                disabled={!workflow.permissions.canEdit || activity !== "idle"}
                aria-describedby={classDescribedBy}
                aria-invalid={classErrors.length > 0}
                onChange={(event) => {
                  setSelectedClass(event.target.value || null);
                  setSaveProblem(null);
                  setSaveMessage("");
                }}
              >
                <option value="">Not selected</option>
                {workflow.fields.disposalClass.allowedValues.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
              {classErrors.length ? (
                <ul className="field-error" id="disposal-class-error">
                  {classErrors.map((error) => (
                    <li key={`${error.code}-${error.message}`}>{error.message}</li>
                  ))}
                </ul>
              ) : null}
            </div>

            <div className="field-group">
              <label htmlFor="disposal-action">Disposal Action</label>
              <p className="field-help" id="disposal-action-help">
                Read-only and derived from Disposal Class. The server confirms it
                after save.
              </p>
              <input
                id="disposal-action"
                value={actionPreview ?? ""}
                placeholder="Not set"
                readOnly
                aria-readonly="true"
                aria-describedby="disposal-action-help"
                aria-live="polite"
              />
            </div>

            {conflicted ? (
              <div
                className="alert alert-error"
                role="alert"
                tabIndex={-1}
                ref={mutationAlertRef}
              >
                <p className="alert-title">Draft version conflict</p>
                <p>{CONFLICT_MESSAGE}</p>
                {saveProblem?.requestId ? (
                  <p className="request-id">
                    Request ID: {saveProblem.requestId}
                  </p>
                ) : null}
                <button
                  className="secondary-button"
                  type="button"
                  disabled={activity !== "idle"}
                  onClick={handleReload}
                >
                  {activity === "reloading" ? "Reloading…" : "Reload draft"}
                </button>
              </div>
            ) : null}

            {!conflicted && saveProblem ? (
              <div tabIndex={-1} ref={mutationAlertRef}>
                <ProblemAlert problem={saveProblem} />
              </div>
            ) : null}

            <p className="save-status" aria-live="polite">
              {saveMessage}
            </p>

            <button
              className="primary-button"
              type="submit"
              disabled={
                !workflow.permissions.canEdit ||
                activity !== "idle" ||
                conflicted
              }
            >
              {activity === "saving" ? "Saving…" : "Save draft"}
            </button>
          </form>
        </article>
      ) : null}
    </main>
  );
}
