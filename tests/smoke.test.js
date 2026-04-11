const { request } = require('playwright');

/**
 * PlayNexus API Smoke Test
 *
 * Purpose:
 * Performs a full authentication lifecycle (Signup -> Login -> Fetch -> Delete)
 * to verify that the PostgreSQL/SQLite database and FastAPI endpoints are actively live.
 */

(async () => {
  let url = process.env.SITE_URL;
  if (!url || url === 'null' || url === 'undefined') {
    const env = process.env.APP_ENV || 'staging';
    url = (env === 'production') ? 'https://playnexus-prod.onrender.com' : 'https://playnexus-test.onrender.com';
  }

  // Fallback to local if no https
  if (!url.startsWith('http')) url = 'http://127.0.0.1:8000';

  console.log(`🔍 Starting API Smoke Test against: ${url}`);
  const context = await request.newContext({ baseURL: url });
  const dummyUser = `test_runner_${Date.now()}`;
  const dummyPass = `P@ssword123!`;

  try {
    // 1. SIGNUP
    console.log(`👤 Creating test account: ${dummyUser}...`);
    let res = await context.post('/api/auth/signup', {
      data: { username: dummyUser, password: dummyPass, confirm_password: dummyPass }
    });
    if (!res.ok()) throw new Error(`Signup failed: ${await res.text()}`);
    console.log('✅ Signup successful.');

    // 2. LOGIN
    console.log(`🔑 Logging into test account...`);
    res = await context.post('/api/auth/login', {
      data: { username: dummyUser, password: dummyPass }
    });
    if (!res.ok()) throw new Error(`Login failed: ${await res.text()}`);
    console.log('✅ Login successful.');

    // 3. CHECK ENDPOINT STATUS
    console.log(`📡 Checking user endpoint status...`);
    res = await context.get(`/api/auth/me?username=${dummyUser}`);
    if (!res.ok()) throw new Error(`Status check failed: ${await res.text()}`);
    console.log('✅ Active user profile state verified.');

    // 4. DELETE ACCOUNT
    console.log(`🧨 Deleting dummy account...`);
    res = await context.delete('/api/auth/account', {
      data: { username: dummyUser, password: dummyPass }
    });
    if (!res.ok()) throw new Error(`Delete failed: ${await res.text()}`);
    console.log('✅ Account successfully deleted.');

    console.log("🎉 ALL ENDPOINTS ACTIVE AND HEALTHY.");

  } catch (error) {
    console.error("❌ ERROR during smoke test:", error.message);
    process.exit(1);
  }
})();