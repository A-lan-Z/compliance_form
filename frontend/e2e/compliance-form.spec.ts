import { expect, test } from "@playwright/test";

const ASSET_URN = "urn:li:container:00000000000000000000000000000001";
const FORM_KEY = "dcl.edw.database.fixture";

test("an authorized fixture BCP saves and reloads the private draft", async ({
  page,
}) => {
  const query = new URLSearchParams({ assetUrn: ASSET_URN, formKey: FORM_KEY });
  await page.goto(`/compliance-form?${query}`);

  await expect(
    page.getByLabel("Fixture environment notice"),
  ).toContainText("Local fixture data — no DataHub changes are made.");
  await expect(
    page.getByRole("heading", {
      name: "DCL EDW Database Compliance — Fixture",
    }),
  ).toBeVisible();
  await expect(page.getByText("Fixture EDW Database")).toBeVisible();
  await expect(page.getByText(ASSET_URN)).toBeVisible();
  await expect(page.getByText("DRAFT", { exact: true })).toBeVisible();

  const disposalClass = page.getByLabel("Disposal Class");
  const disposalAction = page.getByLabel("Disposal Action");
  await expect(disposalClass).toHaveValue("TEST_CLASS_A");
  await expect(disposalAction).toHaveValue("TEST_ACTION_A");
  await expect(disposalAction).not.toBeEditable();

  await disposalClass.selectOption("TEST_CLASS_B");
  await expect(disposalAction).toHaveValue("TEST_ACTION_B");
  await page.getByRole("button", { name: "Save draft" }).press("Enter");
  await expect(page.getByText("Draft saved.")).toBeVisible();
  await expect(page.getByTestId("workflow-version")).toHaveText("2");

  await page.reload();
  await expect(disposalClass).toHaveValue("TEST_CLASS_B");
  await expect(disposalAction).toHaveValue("TEST_ACTION_B");
  await expect(disposalAction).not.toBeEditable();
  await expect(
    page.getByLabel("Fixture environment notice"),
  ).toBeVisible();

  for (const name of [
    "Submit",
    "Approve",
    "Reject",
    "Publish",
    "Verify",
  ]) {
    await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0);
  }
});
