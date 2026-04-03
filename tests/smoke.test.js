const { chromium } = require('playwright');

/**
 * PlayNexus Visual Smoke Test
 *
 * Purpose:
 * 1. Pass the ProFreeHost anti-bot challenge (real browser).
 * 2. Take a full-page screenshot of the produced site.
 * 3. Verify specifically that the text "PlayNexus" exists (ensures no blank page).
 *
 * Environment fallbacks:
 * - If SITE_URL is not set or is "null", uses hardcoded URLs based on APP_ENV:
 *   - production: https://playnexus-prod.onrender.com
 *   - staging/test: https://playnexus-test.onrender.com
 */

(async () => {
  let url = process.env.SITE_URL;

  // Fallback to environment-specific hardcoded URLs if SITE_URL is missing or null
  if (!url || url === 'null' || url === 'undefined') {
    const env = process.env.APP_ENV || process.env.ENV || process.env.NODE_ENV || 'staging';
    console.log(`⚠️  SITE_URL not provided (value: ${url}), using fallback for environment: ${env}`);

    if (env === 'production' || env === 'prod') {
      url = 'https://playnexus-prod.onrender.com';
    } else {
      url = 'https://playnexus-test.onrender.com'; // staging/test default
    }
    console.log(`🔧 Using fallback URL: ${url}`);
  }

  console.log(`🔍 Starting Smoke Test for: ${url}`);
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // 1. Navigate to the site
    // networkidle: Wait until there are no more than 0 network connections for at least 500 ms.
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

    // 2. Take a Full-Page Screenshot
    await page.screenshot({ path: 'screenshot.png', fullPage: true });
    console.log("📸 Screenshot captured: screenshot.png");

    // 3. Verify Page Content
    const content = await page.textContent('body');
    if (content.includes('PlayNexus')) {
      console.log("✅ SUCCESS: 'PlayNexus' found on the page.");
    } else {
      console.error("❌ FAILURE: 'PlayNexus' NOT found. The page might be blank or redirecting.");
      process.exit(1);
    }

  } catch (error) {
    console.error("❌ ERROR during smoke test:", error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
