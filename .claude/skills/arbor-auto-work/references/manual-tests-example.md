# Manual test criteria: the house style

Copy this structure for every report's `manualTests`; do not copy its content.
A project profile may name its own example, which then replaces this one.

Rules visible in the example:
- Environment-agnostic: never name an environment, host, port, profile or
  local-run step; the tester uses whatever environment they are testing.
- Opens with "This verifies ..." (list every ticket the change covers), then
  **WHAT CHANGED** in 2-4 plain sentences about behavior, not code.
- One **TEST N: <what is being proven> (<ticket>)** block per scenario, ordered:
  reproduce the original bug first, then related symptoms, then edge/race
  cases, then access/permissions, then admin/removed features, then a
  **Regression** block last.
- Steps are short imperative sentences, numbered, one action each. Test data is
  built fresh ("Create customer A, and note A's ID"), never IDs quoted in the
  ticket; say so when the ticket quotes IDs ("do not reuse them").
- The last numbered step is `Expected:` followed by bullets (or one inline
  sentence when there is one outcome). Expected results are observable (what
  the user sees, the HTTP status, a log line present or absent), never "works
  correctly".
- Optional `Before the fix:` line stating the old behavior, so a tester can tell
  fixed from broken.
- Log checks name the exact message and whether it must be absent or present.
- Ends with **AUTOMATED COVERAGE**: where the specs live, the run command, and
  the setup caveat.

---

This verifies both SHOP-412 and SHOP-418

WHAT CHANGED
Order totals are now computed from the stored line items instead of the cached cart, so a discount applied after checkout starts shows up on the confirmation page and in the invoice. The invoice download no longer fails with a server error when an order has a zero-priced line.

**TEST 1: Reproduce the original bug (SHOP-412)**

1. Create customer A, and note A's ID.
2. As A, add two products to the cart and start checkout.
3. In the admin tool, apply a 10% discount to A's open order.
4. As A, finish checkout.
5. Expected: the confirmation page and the order history both show the discounted total.
6. Before the fix: the confirmation page showed the undiscounted total.

**TEST 2: Invoice with a zero-priced line (SHOP-418)**

1. Create customer B, and add a free sample plus one paid product to B's cart.
2. Complete checkout as B.
3. Download the invoice from B's order history.
4. Expected:

    * The invoice downloads as a PDF with both lines, the sample at 0.00.
    * There is no server error.

5. Check the application log for: Cannot divide by zero line total
   Expected: it is absent.

**TEST 3: Access is limited to the order's owner**

1. As B, open A's order URL directly. Expected: access is denied (403).
2. As an admin, open the same order. Expected: it loads.
3. The ticket quotes orders 88213 and 88240 as examples; they belong to other accounts, so do not reuse them.

**TEST 4: Regression**

1. Place an order with no discounts and only paid lines.
2. Expected: totals, confirmation page and invoice match what they showed before the change.

**AUTOMATED COVERAGE**
test-automation/tests/api/ has OrderTotals and InvoiceDownload specs. Run them with: npm run api
Point the run at the environment you are testing.
