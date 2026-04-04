const { chromium } = require('playwright');

/**
 * PlayNexus Authentication Flow Smoke Test
 * 
 * Flow:
 * 1. Register a new user
 * 2. Login with the new user
 * 3. Delete the user
 * 
 * Run with: node tests/auth_flow.test.js
 */

(async () => {
  const url = process.env.SITE_URL || 'http://localhost:8000';
  const timestamp = Date.now();
  const testUser = `smoke_test_${timestamp}`;
  const testPass = 'SecurePass123!';

  console.log(`🔍 Starting Auth Flow Test for: ${url}`);
  console.log(`👤 Using test account: ${testUser}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Navigate to the site
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    console.log("📍 Navigated to the portal.");

    // 2. Register User
    console.log("📝 Registering new user...");
    await page.click('.mode-btn'); // Switch to signup mode
    await page.fill('#auth-username', testUser);
    await page.fill('#auth-password', testPass);
    await page.fill('#auth-confirm-password', testPass);
    
    // Wait for validation to settle
    await page.waitForTimeout(500); 
    await page.click('#auth-btn');

    // Wait for success or transition
    await page.waitForSelector('#master-hub-container', { state: 'visible', timeout: 15000 });
    console.log("✅ Registration successful, hub reached.");

    // 3. Verify Identity
    const displayName = await page.textContent('#display-username');
    if (displayName.trim() === testUser) {
      console.log(`✅ Hub confirms identity: ${displayName}`);
    } else {
      console.warn(`⚠️ Hub shows identity: ${displayName} (expected ${testUser})`);
    }

    // 4. Sign Out
    console.log("🚪 Signing out...");
    await page.click('button:has-text("SIGN OUT")');
    await page.waitForSelector('#crystal-auth-portal', { state: 'visible' });
    console.log("✅ Successfully signed out.");

    // 5. Login
    console.log("🔑 Logging in as the new user...");
    await page.fill('#auth-username', testUser);
    await page.fill('#auth-password', testPass);
    await page.click('#auth-btn');
    await page.waitForSelector('#master-hub-container', { state: 'visible' });
    console.log("✅ Login successful.");

    // 6. Delete Account
    console.log("🗑️ Deleting account...");
    await page.click('button:has-text("DELETE ACCOUNT")');
    await page.waitForSelector('#delete-account-modal.is-open', { state: 'visible' });
    
    await page.fill('#delete-confirm-username', testUser);
    await page.fill('#delete-password', testPass);
    await page.click('#delete-account-submit');

    // Verify redirection to auth portal
    await page.waitForSelector('#crystal-auth-portal', { state: 'visible' });
    console.log("✅ Account deleted successfully.");

    // 7. Verify Cleanup (Attempt Login)
    console.log("🕵️ Verifying account removal (attemtping login)...");
    await page.fill('#auth-username', testUser);
    await page.fill('#auth-password', testPass);
    await page.click('#auth-btn');
    
    // Expect error
    await page.waitForSelector('#auth-error', { state: 'visible' });
    const errorMsg = await page.textContent('#auth-error-text');
    console.log(`✅ Login failed as expected. Server message: "${errorMsg.trim()}"`);

    console.log("\n✨ ALL TESTS PASSED! Authentication functional flows are working correctly.");

  } catch (error) {
    console.error("\n❌ TEST FAILED:", error.message);
    const screenshotPath = `auth_test_failure_${timestamp}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`📸 Failure screenshot captured: ${screenshotPath}`);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
